# -*- coding: utf-8 -*-
"""
ELDORIA — versão otimizada e redesenhada
Requer: pygame 2.x   |   Execute com:  python eldoria.py

Principais melhorias técnicas
  - Textos com cache (nada de re-renderizar 9x por frame)
  - Tabuleiro, sidebar e fundos pré-renderizados uma única vez
  - Capa carregada uma vez (antes era lida do disco a cada frame)
  - Escala da janela com letterbox (mantém proporção) e mouse corrigido
  - Estado do jogo organizado na classe Jogo (sem dezenas de globals)
  - Áudio resiliente: falta de um arquivo não derruba todos os sons
"""
import math
import random
from collections import deque
from functools import lru_cache

import pygame

# ==========================================================================
# CONSTANTES DE JOGO
# ==========================================================================
VIDA_HEROI = 100
VIDA_FORTALEZA = 150
VIDA_DRAGAO = 300
CURA_POCAO = 10
CURA_CURANDEIRO = 10
BONUS_GUERREIRO = 0.20
BONUS_PERGAMINHO = 0.10
CHANCE_CRITICO_ARQUEIRO = 30
REDUCAO_ESCUDEIRO = 0.50
MAX_PROTECOES_POR_ALVO = 5
MAX_CURAS_POR_ALVO = 25
DANO_DRAGAO_FIXO = 15

CLASSES = ("guerreiro", "arqueiro", "curandeiro", "mago", "escudeiro")
ORDEM_FORTALEZAS = ("fortaleza1", "fortaleza2", "fortaleza3")

NOMES_EXIBICAO = {
    "guerreiro": "Guerreiro", "arqueiro": "Arqueiro", "curandeiro": "Curandeira",
    "mago": "Mago", "escudeiro": "Escudeira",
}
COR_CLASSE = {
    "guerreiro": (230, 90, 80), "arqueiro": (110, 210, 100),
    "curandeiro": (250, 190, 220), "mago": (110, 160, 250),
    "escudeiro": (250, 170, 70),
}

# ==========================================================================
# GEOMETRIA E PALETA
# ==========================================================================
LARGURA, ALTURA = 991, 730
GRADE = 12
LC = 792 // GRADE            # largura da célula (66)
AC = 530 // GRADE            # altura da célula  (44)
TAB_W, TAB_H = LC * GRADE, AC * GRADE
X_SB = TAB_W                 # início da sidebar
L_SB = LARGURA - X_SB
CX_SB = X_SB + L_SB // 2

PONTOS_CRITICOS = [(0, 0), (2, 5), (5, 10), (8, 3), (6, 6), (11, 11)]
AREA_BASE = {(0, 0), (1, 0), (0, 1), (1, 1)}
ESTRUTURAS_INICIAIS = {
    (6, 6): "dragao", (2, 5): "fortaleza1", (5, 10): "fortaleza2",
    (8, 3): "fortaleza3", (11, 11): "santuario",
}

C_FUNDO = (24, 20, 18)
C_PAINEL = (38, 32, 28)
C_CARD = (56, 48, 42)
C_CARD_BORDA = (96, 80, 60)
C_OURO = (236, 194, 92)
C_OURO_ESC = (168, 128, 52)
C_TEXTO = (240, 230, 210)
C_TEXTO_SUAVE = (172, 160, 140)
C_PERIGO = (224, 84, 76)
C_OK = (104, 200, 98)
C_AVISO = (232, 190, 60)
C_CELULA_A = (120, 189, 93)
C_CELULA_B = (108, 172, 84)
C_GRADE = (98, 138, 84)
C_DESTAQUE = (150, 255, 150, 80)

DURACAO_CAPA_MS = 5000
DURACAO_POPUP_MS = 1100
LOG_VIDA_MS = 5000

# ==========================================================================
# INICIALIZAÇÃO DO PYGAME
# ==========================================================================
pygame.init()
janela = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
pygame.display.set_caption("Eldoria")
tela = pygame.Surface((LARGURA, ALTURA)).convert()

# ==========================================================================
# ÁUDIO
# ==========================================================================
AUDIO_OK = False
try:
    pygame.mixer.init()
    pygame.mixer.set_num_channels(16)
    AUDIO_OK = True
except pygame.error as _e:
    print(f"Aviso: áudio indisponível ({_e})")


def _carregar_som(arquivo, volume=None):
    if not AUDIO_OK:
        return None
    try:
        som = pygame.mixer.Sound(arquivo)
        if volume is not None:
            som.set_volume(volume)
        return som
    except (pygame.error, FileNotFoundError):
        return None


ARQUIVOS_SONS = {
    "pocao": "potion.mp3", "pergaminho": "pergaminho.mp3",
    "morte": "morte_jogador.mp3", "vitoria": "vitoria.mp3",
    "derrota": "derrota.mp3", "golpe": "ataque_inimigo_dragao.mp3",
    "ataque_fortaleza": "ataque_fortaleza.mp3", "erra": "personagem_erra.mp3",
    "cura": "cura.mp3", "reviver": "som_reviver.mp3",
    "escudo": "escudeiro_protege.mp3", "critico": "arqueiro_critico.mp3",
    "fortaleza_caiu": "fortaleza_caiu.mp3",
    "fortalezas_caidas": "fortalezas_derrubadas.mp3",
    "dragao_acordou": "dragao_acordado.mp3", "santuario": "chegou_santuario.mp3",
}
SONS = {chave: _carregar_som(arq) for chave, arq in ARQUIVOS_SONS.items()}
SOM_DRAGAO_LOOP = _carregar_som("dragao_movimentando.mp3", 0.40)
SOM_BATALHA = _carregar_som("fundo_batalha_final.mp3", 0.55)
CANAL_BATALHA = pygame.mixer.Channel(7) if AUDIO_OK else None
CANAL_DRAGAO = pygame.mixer.Channel(8) if AUDIO_OK else None

MUSICAS_FUNDO = ("nova_musica.mp3", "musica_fundo.mp3")
MUSICA_FINAL = "musica_final.mp3"
VOL_MUSICA, VOL_MUSICA_DRAGAO, VOL_MUSICA_BATALHA = 0.30, 0.06, 0.08


def tocar_som(chave):
    som = SONS.get(chave)
    if som:
        som.play()


def musica_volume(v):
    if AUDIO_OK:
        try:
            pygame.mixer.music.set_volume(v)
        except pygame.error:
            pass


def _tocar_musica(arquivos, volume):
    if not AUDIO_OK:
        return
    for arq in arquivos:
        try:
            pygame.mixer.music.load(arq)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
            return
        except (pygame.error, FileNotFoundError):
            continue


def iniciar_musica_fundo():
    _tocar_musica(MUSICAS_FUNDO, VOL_MUSICA)


def iniciar_loop_dragao():
    if CANAL_DRAGAO and SOM_DRAGAO_LOOP and not CANAL_DRAGAO.get_busy():
        CANAL_DRAGAO.play(SOM_DRAGAO_LOOP, loops=-1)


def iniciar_musica_batalha_final():
    if CANAL_BATALHA and SOM_BATALHA and not CANAL_BATALHA.get_busy():
        CANAL_BATALHA.play(SOM_BATALHA, loops=-1)
    musica_volume(VOL_MUSICA_BATALHA)


def parar_toda_musica():
    if not AUDIO_OK:
        return
    for canal in (CANAL_DRAGAO, CANAL_BATALHA):
        if canal:
            canal.stop()
    try:
        pygame.mixer.music.stop()
    except pygame.error:
        pass


def tocar_musica_final():
    parar_toda_musica()
    _tocar_musica((MUSICA_FINAL,), 0.70)


# ==========================================================================
# FONTES
# ==========================================================================
ARQUIVO_FONTE = "NewRocker-Regular.ttf"


def _fonte(tamanho, reserva):
    try:
        return pygame.font.Font(ARQUIVO_FONTE, tamanho)
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.Font(None, reserva)


F_MINI = _fonte(14, 16)
F_PEQ = _fonte(18, 18)
F_TUT = _fonte(20, 22)
F_NORMAL = _fonte(24, 24)
F_TIT = _fonte(36, 36)
F_GRANDE = _fonte(72, 72)

# ==========================================================================
# UTILITÁRIOS GRÁFICOS (com cache)
# ==========================================================================


def clarear(cor, n):
    return tuple(min(255, c + n) for c in cor[:3])


@lru_cache(maxsize=2048)
def _surf_texto(txt, fonte, cor, sombra):
    base = fonte.render(txt, True, cor)
    if not sombra:
        return base
    w, h = base.get_size()
    s = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    sh = fonte.render(txt, True, (0, 0, 0))
    sh.set_alpha(150)
    s.blit(sh, (1, 2))
    s.blit(base, (0, 0))
    return s


def texto(sup, txt, fonte, cor, pos, ancora="topleft", sombra=True):
    """Desenha texto (com cache e sombra suave). Retorna o Rect usado."""
    if not txt:
        return pygame.Rect(pos, (0, 0))
    s = _surf_texto(txt, fonte, tuple(cor), sombra)
    r = s.get_rect(**{ancora: pos})
    sup.blit(s, r)
    return r


@lru_cache(maxsize=512)
def quebrar_texto(txt, fonte, largura):
    """Quebra o texto em linhas que cabem em 'largura'. Respeita '\\n'."""
    linhas = []
    for paragrafo in txt.split("\n"):
        atual = ""
        for palavra in paragrafo.split():
            teste = f"{atual} {palavra}".strip()
            if fonte.size(teste)[0] <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return tuple(linhas)


@lru_cache(maxsize=256)
def _rect_alpha(w, h, rgba, raio=0):
    s = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
    pygame.draw.rect(s, rgba, (0, 0, w, h), border_radius=raio)
    return s


@lru_cache(maxsize=64)
def _sombra_elipse(w):
    w = max(8, int(w))
    s = pygame.Surface((w, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 70), (0, 0, w, 10))
    return s


def gradiente(w, h, c1, c2):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(s, tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)),
                         (0, y), (w, y))
    return s


def gradiente_alpha(w, h, rgb, a1, a2):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(s, (*rgb, int(a1 + (a2 - a1) * t)), (0, y), (w, y))
    return s


def cartao(sup, rect, cor=C_CARD, borda=C_CARD_BORDA, raio=10, sombra=True, esp=2):
    r = pygame.Rect(rect)
    if sombra:
        sup.blit(_rect_alpha(r.w, r.h, (0, 0, 0, 70), raio), (r.x + 2, r.y + 3))
    pygame.draw.rect(sup, cor, r, border_radius=raio)
    pygame.draw.rect(sup, borda, r, esp, border_radius=raio)
    return r


def divisor(sup, x, y, largura, cor=C_OURO_ESC):
    pygame.draw.line(sup, cor, (x + 8, y), (x + largura - 8, y), 1)
    for dx in (x + 4, x + largura - 4):
        pygame.draw.polygon(sup, cor, [(dx, y - 3), (dx + 3, y), (dx, y + 3), (dx - 3, y)])


def cor_hp(p):
    return C_OK if p > 0.5 else C_AVISO if p > 0.25 else C_PERIGO


def barra_hp(sup, x, y, w, h, atual, maximo, cor=None):
    p = max(0.0, min(1.0, atual / maximo)) if maximo else 0.0
    raio = h // 2
    pygame.draw.rect(sup, (18, 15, 13), (x, y, w, h), border_radius=raio)
    fw = int(w * p)
    if fw > 0:
        c = cor or cor_hp(p)
        pygame.draw.rect(sup, c, (x, y, fw, h), border_radius=raio)
        if fw > h and h >= 8:
            pygame.draw.line(sup, clarear(c, 60), (x + raio, y + 1), (x + fw - raio, y + 1))
    pygame.draw.rect(sup, C_CARD_BORDA, (x, y, w, h), 1, border_radius=raio)


def botao(sup, txt, rect, cor, pos_mouse, cor_txt=C_FUNDO, fonte=F_TIT):
    rect = pygame.Rect(rect)
    hover = rect.collidepoint(pos_mouse)
    r = rect.move(0, -2) if hover else rect
    pygame.draw.rect(sup, (10, 8, 6), r.move(0, 4), border_radius=12)
    c = clarear(cor, 28) if hover else cor
    pygame.draw.rect(sup, c, r, border_radius=12)
    pygame.draw.rect(sup, clarear(c, 55), r, 2, border_radius=12)
    texto(sup, txt, fonte, cor_txt, r.center, "center", sombra=False)
    return rect


def tecla_visual(sup, rotulo, x, y, largura=34):
    w = max(largura, F_PEQ.size(rotulo)[0] + 16)
    r = pygame.Rect(x, y, w, 28)
    pygame.draw.rect(sup, (16, 13, 11), r.move(0, 3), border_radius=7)
    pygame.draw.rect(sup, (70, 60, 50), r, border_radius=7)
    pygame.draw.rect(sup, C_OURO_ESC, r, 2, border_radius=7)
    texto(sup, rotulo, F_PEQ, C_OURO, r.center, "center", sombra=False)
    return r


def desenhar_bloco(sup, itens, fonte, x, y, largura, cor=C_TEXTO):
    """Bloco de texto com marcação: h=título, p=parágrafo, b=bullet, _=espaço."""
    lh = fonte.get_linesize()
    for tipo, txt in itens:
        if tipo == "h":
            texto(sup, txt, F_NORMAL, C_OURO, (x, y))
            y += F_NORMAL.get_linesize() + 4
        elif tipo in ("p", "b"):
            recuo = 18 if tipo == "b" else 0
            for i, linha in enumerate(quebrar_texto(txt, fonte, largura - recuo)):
                if tipo == "b" and i == 0:
                    cy = y + lh // 2
                    pygame.draw.polygon(sup, C_OURO, [(x + 5, cy - 4), (x + 9, cy),
                                                      (x + 5, cy + 4), (x + 1, cy)])
                texto(sup, linha, fonte, cor, (x + recuo, y))
                y += lh
            y += 5
        else:
            y += lh // 2
    return y


# ==========================================================================
# IMAGENS
# ==========================================================================


def carregar_imagem(nome, tamanho):
    try:
        return pygame.transform.smoothscale(pygame.image.load(nome).convert_alpha(), tamanho)
    except (pygame.error, FileNotFoundError):
        print(f"ERRO: imagem '{nome}' não encontrada!")
        surf = pygame.Surface(tamanho, pygame.SRCALPHA)
        surf.fill((255, 0, 255, 255))
        return surf


def para_cinza(img):
    try:
        return pygame.transform.grayscale(img)          # pygame >= 2.1.4 (rápido)
    except (AttributeError, pygame.error):
        copia = img.copy()
        for px in range(copia.get_width()):
            for py in range(copia.get_height()):
                r, g, b, a = copia.get_at((px, py))
                if a:
                    c = int(r * 0.299 + g * 0.587 + b * 0.114)
                    copia.set_at((px, py), (c, c, c, a))
        return copia


VISUAIS = {
    "arvore_folhas": carregar_imagem("Estruturas_ArvoresComFolhasV2.png", (60, 60)),
    "arvore_seca": carregar_imagem("Estruturas_ArvoresSemFolhasV2.png", (60, 60)),
    "estatua": carregar_imagem("Estruturas_Estatua.png", (70, 56)),
    "pedra": carregar_imagem("Estruturas_Pedra.png", (50, 50)),
    "muro": carregar_imagem("Estruturas_Muro.png", (65, 85)),
    "pocao": carregar_imagem("Item_Pocao.png", (45, 55)),
    "pergaminho": carregar_imagem("Item_PergaminhoV2.png", (45, 55)),
    "dragao": carregar_imagem("Dragao_Adormecido.png", (100, 120)),
    "dragao_acordado": carregar_imagem("Dragao_Acordado.png", (100, 120)),
    "fortaleza1": carregar_imagem("Fortaleza_1.png", (75, 55)),
    "fortaleza2": carregar_imagem("Fortaleza_2.png", (75, 55)),
    "fortaleza3": carregar_imagem("Fortaleza_3.png", (75, 55)),
    "santuario": carregar_imagem("Santuario_Dragao.png", (85, 55)),
    "base": carregar_imagem("base.png", (85, 65)),
}
IMG_INIMIGO = carregar_imagem("Sprite_Inimigo.png", (40, 55))

IMG_HEROI = {c: carregar_imagem(f"Sprite_{c.capitalize()}.png", (55, 60))
             for c in CLASSES}
IMG_HEROI_PB = {c: para_cinza(img) for c, img in IMG_HEROI.items()}

RETRATOS = {
    "guerreiro": carregar_imagem("Selecionado_Guerreiro.png", (230, 230)),
    "arqueiro": carregar_imagem("Selecionado_Arqueiro.png", (280, 280)),
    "curandeiro": carregar_imagem("Selecionado_Curandeiro.png", (210, 255)),
    "mago": carregar_imagem("Selecionado_Mago.png", (260, 290)),
    "escudeiro": carregar_imagem("Selecionado_Escudeiro.png", (240, 240)),
}
POS_PERSONAGEM = {
    "guerreiro": {"retrato": (-5, 525), "texto": (70, 695)},
    "arqueiro": {"retrato": (-25, 520), "texto": (75, 690)},
    "curandeiro": {"retrato": (0, 515), "texto": (65, 700)},
    "mago": {"retrato": (-18, 510), "texto": (70, 695)},
    "escudeiro": {"retrato": (-8, 510), "texto": (72, 692)},
}

# Ícones pequenos da sidebar (escalados uma única vez)
ICO_FORT = {k: pygame.transform.smoothscale(VISUAIS[k], (57, 42)) for k in ORDEM_FORTALEZAS}
ICO_FORT_PB = {k: para_cinza(v) for k, v in ICO_FORT.items()}
ICO_DRAGAO = pygame.transform.smoothscale(VISUAIS["dragao"], (60, 72))
ICO_DRAGAO_AC = pygame.transform.smoothscale(VISUAIS["dragao_acordado"], (60, 72))
ICO_INIMIGO = pygame.transform.smoothscale(IMG_INIMIGO, (22, 29))
ICO_POCAO = pygame.transform.smoothscale(VISUAIS["pocao"], (23, 29))
ICO_PERGAMINHO = pygame.transform.smoothscale(VISUAIS["pergaminho"], (23, 29))


def carregar_capa():
    try:
        img = pygame.image.load("Capa_Eldoria.jpeg").convert()
        return pygame.transform.smoothscale(img, (LARGURA, ALTURA))
    except (pygame.error, FileNotFoundError):
        return None


IMG_CAPA = carregar_capa()


# ==========================================================================
# CAMADAS ESTÁTICAS PRÉ-RENDERIZADAS
# ==========================================================================


def criar_fundo_tabuleiro():
    s = pygame.Surface((TAB_W, TAB_H))
    for lin in range(GRADE):
        for col in range(GRADE):
            cor = C_CELULA_A if (col + lin) % 2 == 0 else C_CELULA_B
            s.fill(cor, (col * LC, lin * AC, LC, AC))
    rng = random.Random(11)                        # tufos de grama decorativos
    for _ in range(240):
        x, y = rng.randint(4, TAB_W - 6), rng.randint(8, TAB_H - 4)
        cor = (92, 152, 70) if rng.random() < 0.7 else (136, 204, 106)
        pygame.draw.line(s, cor, (x, y), (x - 2, y - 4))
        pygame.draw.line(s, cor, (x, y), (x, y - 5))
        pygame.draw.line(s, cor, (x, y), (x + 2, y - 4))
    for lin in range(GRADE):
        for col in range(GRADE):
            pygame.draw.rect(s, C_GRADE, (col * LC, lin * AC, LC, AC), 1)
    base = VISUAIS["base"]
    s.blit(base, ((LC - base.get_width()) // 2, (AC - base.get_height()) // 2))
    return s


def criar_ui_estatica():
    sb = gradiente(L_SB, ALTURA, (46, 39, 34), (26, 22, 20))
    pygame.draw.line(sb, C_OURO_ESC, (0, 0), (0, ALTURA), 3)
    inf = gradiente(TAB_W, ALTURA - TAB_H, (40, 34, 30), (24, 20, 18))
    pygame.draw.line(inf, C_OURO_ESC, (0, 0), (TAB_W, 0), 3)
    return sb, inf


def criar_minimapa_base(c=14):
    s = pygame.Surface((c * GRADE, c * GRADE))
    for lin in range(GRADE):
        for col in range(GRADE):
            cor = (74, 122, 60) if (col + lin) % 2 == 0 else (66, 110, 54)
            s.fill(cor, (col * c, lin * c, c, c))
    pygame.draw.rect(s, C_CARD_BORDA, s.get_rect(), 1)
    return s


def criar_fundo_menu():
    if IMG_CAPA:
        pequeno = pygame.transform.smoothscale(IMG_CAPA, (LARGURA // 10, ALTURA // 10))
        s = pygame.transform.smoothscale(pequeno, (LARGURA, ALTURA))
        s.blit(_rect_alpha(LARGURA, ALTURA, (12, 9, 7, 175)), (0, 0))
        return s
    return gradiente(LARGURA, ALTURA, (34, 24, 40), (14, 10, 18))


FUNDO_TAB = criar_fundo_tabuleiro()
UI_SIDEBAR, UI_INFERIOR = criar_ui_estatica()
MINIMAPA_BASE = criar_minimapa_base()
FUNDO_MENU = criar_fundo_menu()
_FUNDOS = {}


def fundo_cache(nome):
    if nome not in _FUNDOS:
        if nome == "vitoria":
            _FUNDOS[nome] = gradiente(LARGURA, ALTURA, (40, 20, 0), (120, 60, 0))
        else:
            _FUNDOS[nome] = gradiente(LARGURA, ALTURA, (60, 5, 5), (100, 15, 10))
    return _FUNDOS[nome]


# ==========================================================================
# PATHFINDING
# ==========================================================================


def bfs_proximo_passo(origem, destino, bloqueados):
    if origem == destino:
        return None
    fila = deque([origem])
    pai = {origem: None}
    while fila:
        atual = fila.popleft()
        if atual == destino:
            caminho = []
            while atual is not None:
                caminho.append(atual)
                atual = pai[atual]
            caminho.reverse()
            return caminho[1] if len(caminho) > 1 else None
        c, l = atual
        for v in ((c + 1, l), (c - 1, l), (c, l + 1), (c, l - 1)):
            if 0 <= v[0] < GRADE and 0 <= v[1] < GRADE and v not in pai and v not in bloqueados:
                pai[v] = atual
                fila.append(v)
    return None


def centro_celula(col, lin):
    return col * LC + LC / 2, lin * AC + AC / 2


def criar_herois():
    herois = {}
    for c in CLASSES:
        herois[c] = {
            "coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
            "classe": c, "bonus_ataque": 1 + BONUS_GUERREIRO if c == "guerreiro" else 1.0,
            "pergaminhos": 0, "curas_recebidas": 0, "protecoes_recebidas": 0,
            "turnos_morto": 0, "ja_foi_revivido": False,
        }
    herois["escudeiro"]["protegendo"] = None
    return herois


# ==========================================================================
# TEXTOS DO TUTORIAL
# ==========================================================================
TUTORIAL_LENDA = [
    ("p", "Há séculos, o reino de Eldoria vive sob a sombra de um antigo Dragão adormecido."),
    ("p", "Para controlar a criatura, três fortalezas foram erguidas ao redor do seu covil, "
          "protegidas por inimigos sombrios e encantamentos ancestrais."),
    ("_", ""),
    ("p", "Agora, um grupo de cinco heróis parte da antiga base do reino em uma última tentativa "
          "de salvar a terra. Cada membro possui habilidades únicas, e somente trabalhando juntos "
          "será possível destruir as fortalezas, alcançar o Santuário Sagrado e enfrentar o Dragão."),
    ("_", ""),
    ("p", "Porém, a jornada é perigosa. Inimigos vagam pelo mundo, recursos são limitados e a queda "
          "de um companheiro pode significar a derrota."),
]
TUTORIAL_HEROIS = [
    ("guerreiro", "Guerreiro", "Possui maior força física. Causa mais dano contra fortalezas e o Dragão."),
    ("arqueiro", "Arqueiro", "Ataca com precisão. Possui chance de causar dano crítico (dobrado)."),
    ("curandeiro", "Curandeira", "Recupera vida dos aliados (C, máx. 25x/aliado) e revive mortos (V)."),
    ("mago", "Mago", "Pode atacar fortalezas e o Dragão a uma distância maior (alcance 3)."),
    ("escudeiro", "Escudeira", "Protege aliados adjacentes (máx. 5x/aliado). Cancela se afastar (P)."),
]
TUTORIAL_OBJETIVO = [
    ("h", "Objetivo da missão"),
    ("b", "Derrote inimigos, colete poções (vida) e pergaminhos (+10% de ataque)."),
    ("b", "Destrua as 3 fortalezas na ordem indicada (2+ heróis por perto)."),
    ("b", "Visite o Santuário Sagrado, no canto inferior direito. "
          "Sem isso, o Dragão não pode ser atacado!"),
    ("b", "Derrote o Dragão, no centro do mapa, e salve Eldoria."),
    ("_", ""),
    ("h", "Dicas"),
    ("b", "Mantenha os heróis próximos entre si."),
    ("b", "A Escudeira só protege aliados a 1 bloco: se o aliado se afastar, a proteção cai."),
    ("b", "Proteja a Curandeira: ela não pode ser revivida."),
]
TUTORIAL_CONTROLES = [
    ("1-5", "Selecionar herói"),
    ("Setas / WASD", "Mover o herói selecionado"),
    ("Espaço", "Atacar a fortaleza atual ou o Dragão"),
    ("C", "Curar o herói selecionado (Curandeira a 1 bloco, até 25x)"),
    ("V", "Reviver herói caído adjacente (com a Curandeira selecionada)"),
    ("P", "Escudeira protege o herói selecionado (até 5x)"),
    ("R", "Reiniciar a partida"),
]
TITULOS_PAGINA = {1: "A Lenda de Eldoria", 2: "Os Heróis", 3: "Como Jogar"}

TECLAS_HEROI = {pygame.K_1: "guerreiro", pygame.K_2: "arqueiro", pygame.K_3: "curandeiro",
                pygame.K_4: "mago", pygame.K_5: "escudeiro"}
DIRECOES = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}


# ==========================================================================
# ESTADO E REGRAS DO JOGO
# ==========================================================================
class Jogo:
    def __init__(self):
        self.estado = "CAPA"
        self.pagina = 1
        self.t_capa = pygame.time.get_ticks()
        self.t_fim = 0
        self.cache_paginas = {}
        self.shake_ate = 0
        self._gerar_mapa_inicial()
        self.reiniciar(primeira=True)

    # ---------------- geração do mapa ----------------
    def _gerar_mapa_inicial(self):
        ocupadas = set(ESTRUTURAS_INICIAIS)

        def perto(c, l, grupo):
            return any(abs(c - gc) <= 1 and abs(l - gl) <= 1 for gc, gl in grupo)

        obstaculos = {}
        tipos = (["arvore_folhas"] * 3 + ["arvore_seca"] * 3 + ["estatua"] * 3 +
                 ["pedra"] * 3 + ["muro"] * 3)
        for tipo in tipos:
            while True:
                c, l = random.randint(0, 11), random.randint(0, 11)
                seguro = all(abs(c - cx) > 1 or abs(l - cy) > 1 for cx, cy in PONTOS_CRITICOS)
                if (c, l) not in ocupadas and seguro:
                    obstaculos[(c, l)] = tipo
                    ocupadas.add((c, l))
                    break

        def sortear(grupo):
            tentativas = 0
            while True:
                c, l = random.randint(0, 11), random.randint(0, 11)
                if (c, l) in ocupadas or (c, l) in AREA_BASE:
                    continue
                if tentativas < 50 and perto(c, l, grupo):
                    tentativas += 1
                    continue
                ocupadas.add((c, l))
                return c, l

        itens = {}
        for tipo in ["pocao"] * 15 + ["pergaminho"] * 5:
            itens[sortear(itens.keys())] = tipo
        inimigos = set()
        for _ in range(30):
            inimigos.add(sortear(inimigos))
        self._obst0, self._itens0, self._inim0 = obstaculos, itens, inimigos

    # ---------------- (re)início ----------------
    def reiniciar(self, primeira=False):
        self.herois = criar_herois()
        self.estruturas = dict(ESTRUTURAS_INICIAIS)
        self.vida_estruturas = {f: VIDA_FORTALEZA for f in ORDEM_FORTALEZAS}
        self.vida_estruturas["dragao"] = VIDA_DRAGAO
        self.obstaculos = dict(self._obst0)
        self.itens = dict(self._itens0)
        self.inimigos = set(self._inim0)
        self.idx_fort = 0
        self.turnos = 0
        self.sel = "guerreiro"
        self.santuario_visitado = False
        self.dragao_acordou = False
        self._dragao_aleatorio = 0
        self.log_msgs = []
        self.popups = []
        self.vis, self.hp_vis = {}, {}
        self.sincronizar_visual()
        parar_toda_musica()
        iniciar_musica_fundo()
        if not primeira:
            self.estado = "EXPLORACAO"
            self.log("Jogo reiniciado!")

    @property
    def dragao_desperto(self):
        return self.idx_fort >= len(ORDEM_FORTALEZAS)

    def pos_dragao(self):
        return next((p for p, t in self.estruturas.items() if t == "dragao"), None)

    # ---------------- feedback visual ----------------
    def log(self, msg):
        self.log_msgs.append({"texto": msg, "tempo": pygame.time.get_ticks()})
        if len(self.log_msgs) > 4:
            self.log_msgs.pop(0)

    def popup(self, col, lin, txt, cor):
        cx, cy = centro_celula(col, lin)
        self.popups.append({"txt": txt, "x": cx + random.randint(-10, 10), "y": cy - 24,
                            "cor": cor, "t0": pygame.time.get_ticks()})

    def tremer(self, ms=180):
        self.shake_ate = pygame.time.get_ticks() + ms

    def sincronizar_visual(self):
        for nome, h in self.herois.items():
            self.vis[nome] = list(centro_celula(h["coluna"], h["linha"]))
        pd = self.pos_dragao()
        if pd:
            self.vis["dragao"] = list(centro_celula(*pd))
        for nome, h in self.herois.items():
            self.hp_vis[nome] = h["vida"]
        for chave, v in self.vida_estruturas.items():
            self.hp_vis[chave] = max(0, v)

    def atualizar(self, dt):
        """Animações suaves: movimento dos sprites e barras de vida."""
        k_mov = 1 - math.exp(-dt * 16)
        k_hp = 1 - math.exp(-dt * 8)
        alvos = {n: centro_celula(h["coluna"], h["linha"]) for n, h in self.herois.items()}
        pd = self.pos_dragao()
        if pd:
            alvos["dragao"] = centro_celula(*pd)
        for nome, alvo in alvos.items():
            v = self.vis.setdefault(nome, list(alvo))
            v[0] += (alvo[0] - v[0]) * k_mov
            v[1] += (alvo[1] - v[1]) * k_mov
        metas = {n: max(0, h["vida"]) for n, h in self.herois.items()}
        metas.update({f: max(0, v) for f, v in self.vida_estruturas.items()})
        for chave, meta in metas.items():
            v = self.hp_vis.get(chave, meta)
            v += (meta - v) * k_hp
            self.hp_vis[chave] = meta if abs(v - meta) < 0.3 else v
        agora = pygame.time.get_ticks()
        self.popups = [p for p in self.popups if agora - p["t0"] < DURACAO_POPUP_MS]

    # ---------------- regras ----------------
    def verificar_estado(self):
        if not any(h["vida"] > 0 for h in self.herois.values()):
            parar_toda_musica()
            tocar_som("derrota")
            self.estado = "DERROTA"
            self.t_fim = pygame.time.get_ticks()
            self.log("DERROTA! Todos os heróis foram derrotados.")

    def aplicar_dano(self, nome, dano):
        h = self.herois[nome]
        if h["vida"] <= 0:
            return
        esc = self.herois["escudeiro"]
        if esc["vida"] > 0 and esc.get("protegendo") == nome:
            metade = int(dano * REDUCAO_ESCUDEIRO)
            h["vida"] = max(0, h["vida"] - metade)
            esc["vida"] = max(0, esc["vida"] - metade)
            self.log(f"Escudo! {NOMES_EXIBICAO[nome]} e Escudeira: -{metade} HP cada")
            self.popup(h["coluna"], h["linha"], f"-{metade}", C_PERIGO)
            self.popup(esc["coluna"], esc["linha"], f"-{metade}", C_PERIGO)
            if esc["vida"] <= 0:
                esc["turnos_morto"] = 5
                tocar_som("morte")
                self.log("Escudeira caiu protegendo! (5 turnos p/ reviver)")
                esc["protegendo"] = None
        else:
            h["vida"] = max(0, h["vida"] - dano)
            self.log(f"{NOMES_EXIBICAO[nome]} recebe -{dano} HP")
            self.popup(h["coluna"], h["linha"], f"-{dano}", C_PERIGO)
        self.tremer()

        if h["vida"] == 0 and h["turnos_morto"] == 0:
            tocar_som("morte")
            if nome == "curandeiro":
                h["turnos_morto"] = -1
                self.log("Curandeira derrotada permanentemente!")
            elif h.get("ja_foi_revivido", False):
                h["turnos_morto"] = -1
                self.log(f"{NOMES_EXIBICAO[nome]} caiu definitivamente!")
            else:
                h["turnos_morto"] = 5
                self.log(f"{NOMES_EXIBICAO[nome]} caiu! (5 turnos p/ reviver)")

    def verificar_protecao(self):
        esc = self.herois["escudeiro"]
        alvo = esc.get("protegendo")
        if alvo is None or esc["vida"] <= 0:
            return
        h = self.herois[alvo]
        if h["vida"] <= 0:
            esc["protegendo"] = None
        elif abs(esc["coluna"] - h["coluna"]) > 1 or abs(esc["linha"] - h["linha"]) > 1:
            esc["protegendo"] = None
            self.log(f"Proteção cancelada: {NOMES_EXIBICAO[alvo]} se afastou!")

    def encontro_inimigo(self, nome, pos):
        self.inimigos.discard(pos)
        tocar_som("golpe")
        self.log(f"{NOMES_EXIBICAO[nome]} derrotou inimigo! (-5 HP)")
        self.aplicar_dano(nome, 5)

    def herois_aptos(self, pos):
        aptos = []
        for nome, d in self.herois.items():
            if d["vida"] > 0:
                alcance = 3 if d["classe"] == "mago" else 1
                if abs(d["coluna"] - pos[0]) + abs(d["linha"] - pos[1]) <= alcance:
                    aptos.append(nome)
        return aptos

    def _calcular_dano(self, nome, base):
        d = self.herois[nome]
        dano = base
        if d["classe"] == "guerreiro":
            dano = int(dano * (1 + BONUS_GUERREIRO))
        dano = int(dano * (1 + d["pergaminhos"] * BONUS_PERGAMINHO))
        critico = d["classe"] == "arqueiro" and random.randint(1, 100) <= CHANCE_CRITICO_ARQUEIRO
        return (dano * 2 if critico else dano), critico

    def atacar_fortaleza(self):
        """Retorna True se o ataque foi realizado (consome o turno)."""
        if self.idx_fort >= len(ORDEM_FORTALEZAS):
            return False
        nome_f = ORDEM_FORTALEZAS[self.idx_fort]
        pos_f = next((p for p, t in self.estruturas.items() if t == nome_f), None)
        if not pos_f:
            return False
        aptos = self.herois_aptos(pos_f)
        if len(aptos) < 2:
            self.log(f"Precisa de 2+ heróis perto da Fortaleza {self.idx_fort + 1}!")
            return False
        if self.sel not in aptos:
            self.log(f"{NOMES_EXIBICAO[self.sel]} fora do alcance!")
            return False

        quem = NOMES_EXIBICAO[self.sel]
        if random.randint(0, 100) >= 30:
            dano, critico = self._calcular_dano(self.sel, 15)
            self.vida_estruturas[nome_f] -= dano
            tocar_som("critico" if critico else "ataque_fortaleza")
            self.log(f"{'CRÍTICO! ' if critico else ''}{quem} causa {dano} HP à Fortaleza {self.idx_fort + 1}!")
            self.popup(pos_f[0], pos_f[1], f"-{dano}", C_OURO if critico else (255, 160, 70))
        else:
            tocar_som("erra")
            self.log(f"{quem} errou o ataque!")
            self.popup(pos_f[0], pos_f[1], "Errou", C_TEXTO_SUAVE)

        self.log("A fortaleza contra-ataca: -8 HP")
        self.aplicar_dano(self.sel, 8)

        if self.vida_estruturas[nome_f] <= 0:
            self.idx_fort += 1
            del self.estruturas[pos_f]
            if self.idx_fort >= len(ORDEM_FORTALEZAS):
                tocar_som("fortalezas_caidas")
                self.log("Todas as fortalezas caíram!")
                if not self.dragao_acordou:
                    self.dragao_acordou = True
                    tocar_som("dragao_acordou")
                    self.log("O Dragão despertou! Vá ao Santuário!")
            else:
                tocar_som("fortaleza_caiu")
                self.log(f"Fortaleza {self.idx_fort} destruída!")
        self.verificar_estado()
        return True

    def atacar_dragao(self):
        if not self.santuario_visitado:
            self.log("Vá ao Santuário primeiro!")
            return False
        pos = self.pos_dragao()
        if not pos:
            return False
        if self.sel not in self.herois_aptos(pos):
            self.log(f"{NOMES_EXIBICAO[self.sel]} fora do alcance do Dragão!")
            return False

        quem = NOMES_EXIBICAO[self.sel]
        if random.randint(0, 100) >= 30:
            dano, critico = self._calcular_dano(self.sel, 20)
            self.vida_estruturas["dragao"] = max(0, self.vida_estruturas["dragao"] - dano)
            tocar_som("critico" if critico else "golpe")
            self.log(f"{'CRÍTICO! ' if critico else ''}{quem} causa {dano} HP ao Dragão!")
            self.popup(pos[0], pos[1], f"-{dano}", C_OURO if critico else (255, 160, 70))
        else:
            tocar_som("erra")
            self.log(f"{quem} errou o Dragão!")
            self.popup(pos[0], pos[1], "Errou", C_TEXTO_SUAVE)

        if self.vida_estruturas["dragao"] <= 0:
            tocar_musica_final()
            tocar_som("vitoria")
            self.log("DRAGÃO DERROTADO! VITÓRIA!")
            self.estado = "VITORIA"
            self.t_fim = pygame.time.get_ticks()
            return True

        self.log(f"Dragão contra-ataca: -{DANO_DRAGAO_FIXO} HP!")
        self.aplicar_dano(self.sel, DANO_DRAGAO_FIXO)
        self.verificar_estado()
        return True

    def curar(self, alvo):
        cur = self.herois["curandeiro"]
        if cur["vida"] <= 0:
            self.log("Curandeira está derrotada!")
            return False
        if alvo == "curandeiro":
            self.log("A Curandeira não pode curar a si mesma!")
            return False
        h = self.herois[alvo]
        if h["vida"] <= 0:
            self.log(f"{NOMES_EXIBICAO[alvo]} está morto! (Use V para reviver)")
            return False
        if abs(cur["coluna"] - h["coluna"]) > 1 or abs(cur["linha"] - h["linha"]) > 1:
            self.log(f"{NOMES_EXIBICAO[alvo]} fora do alcance da cura!")
            return False
        if h["curas_recebidas"] >= MAX_CURAS_POR_ALVO:
            self.log(f"Limite de curas atingido para {NOMES_EXIBICAO[alvo]}!")
            return False
        h["vida"] = min(h["vida"] + CURA_CURANDEIRO, h["vida_max"])
        h["curas_recebidas"] += 1
        tocar_som("cura")
        self.log(f"Curandeira cura {NOMES_EXIBICAO[alvo]}! +{CURA_CURANDEIRO} HP "
                 f"({MAX_CURAS_POR_ALVO - h['curas_recebidas']} restantes)")
        self.popup(h["coluna"], h["linha"], f"+{CURA_CURANDEIRO}", C_OK)
        return True

    def proteger(self, alvo):
        esc = self.herois["escudeiro"]
        if esc["vida"] <= 0:
            self.log("Escudeira está derrotada!")
            return False
        if alvo == "escudeiro":
            self.log("A Escudeira não pode proteger a si mesma!")
            return False
        h = self.herois[alvo]
        if h["vida"] <= 0:
            self.log(f"{NOMES_EXIBICAO[alvo]} está morto!")
            return False
        if esc["protegendo"] == alvo:
            esc["protegendo"] = None
            self.log(f"Escudeira desfez a proteção de {NOMES_EXIBICAO[alvo]}!")
            return True
        if esc["protegendo"] is not None:
            self.log(f"Desfaça a proteção de {NOMES_EXIBICAO[esc['protegendo']]} primeiro!")
            return False
        if abs(esc["coluna"] - h["coluna"]) > 1 or abs(esc["linha"] - h["linha"]) > 1:
            self.log("Alvo muito longe! Fique a 1 bloco da Escudeira.")
            return False
        if h["protecoes_recebidas"] >= MAX_PROTECOES_POR_ALVO:
            self.log(f"Limite de proteções para {NOMES_EXIBICAO[alvo]}!")
            return False
        esc["protegendo"] = alvo
        h["protecoes_recebidas"] += 1
        tocar_som("escudo")
        self.log(f"Escudeira protege {NOMES_EXIBICAO[alvo]}! "
                 f"({MAX_PROTECOES_POR_ALVO - h['protecoes_recebidas']} proteções restantes)")
        return True

    def reviver(self):
        cur = self.herois["curandeiro"]
        if self.sel != "curandeiro" or cur["vida"] <= 0:
            self.log("Apenas a Curandeira pode reviver aliados!")
            return False
        reviveu = False
        for nome, d in self.herois.items():
            if d["vida"] <= 0 and d["turnos_morto"] > 0:
                if abs(d["coluna"] - cur["coluna"]) + abs(d["linha"] - cur["linha"]) <= 1:
                    d["vida"] = d["vida_max"] // 2
                    d["turnos_morto"] = 0
                    d["ja_foi_revivido"] = True
                    tocar_som("reviver")
                    self.log(f"Curandeira reviveu {NOMES_EXIBICAO[nome]} com {d['vida']} HP!")
                    self.popup(d["coluna"], d["linha"], "Revivido!", C_OK)
                    reviveu = True
        if not reviveu:
            self.log("Nenhum aliado morto próximo para reviver.")
        return reviveu

    def mover(self, dc, dl):
        h = self.herois[self.sel]
        if h["vida"] <= 0:
            self.log(f"{NOMES_EXIBICAO[self.sel]} está incapacitado!")
            return False
        col, lin = h["coluna"] + dc, h["linha"] + dl
        if not (0 <= col < GRADE and 0 <= lin < GRADE):
            return False
        pos = (col, lin)
        bloqueado_por_heroi = (not (col == 0 and lin == 0)) and any(
            n != self.sel and o["coluna"] == col and o["linha"] == lin
            and (o["vida"] > 0 or o["turnos_morto"] > 0)
            for n, o in self.herois.items())
        tipo = self.estruturas.get(pos)

        if tipo == "santuario":
            if bloqueado_por_heroi:
                return False
            if not self.dragao_desperto:
                self.log("Destrua as fortalezas antes!")
                return False
            self.santuario_visitado = True
            h["coluna"], h["linha"] = col, lin
            tocar_som("santuario")
            iniciar_musica_batalha_final()
            self.log("Santuário alcançado! Agora ataque o Dragão!")
            return True

        if tipo or pos in self.obstaculos or bloqueado_por_heroi:
            return False

        if pos in self.inimigos:
            self.encontro_inimigo(self.sel, pos)
            h["coluna"], h["linha"] = col, lin
            self.verificar_estado()
            return True

        h["coluna"], h["linha"] = col, lin
        item = self.itens.get(pos)
        nome = NOMES_EXIBICAO[self.sel]
        if item == "pocao":
            if h["vida"] >= h["vida_max"]:
                self.log(f"{nome} já está com vida cheia!")
            else:
                tocar_som("pocao")
                h["vida"] = min(h["vida"] + CURA_POCAO, h["vida_max"])
                self.log(f"+{CURA_POCAO} HP! {nome} usou poção.")
                self.popup(col, lin, f"+{CURA_POCAO}", C_OK)
                del self.itens[pos]
        elif item == "pergaminho":
            tocar_som("pergaminho")
            h["pergaminhos"] += 1
            self.log(f"+{int(BONUS_PERGAMINHO * 100)}% atq! {nome} pegou pergaminho.")
            self.popup(col, lin, f"+{int(BONUS_PERGAMINHO * 100)}% ATQ", (170, 150, 250))
            del self.itens[pos]
        return True

    # ---------------- IA do dragão ----------------
    def mover_dragao(self, ataque_manual):
        if not self.dragao_desperto or self.estado != "EXPLORACAO":
            return
        pd = self.pos_dragao()
        if not pd:
            return
        alvo, menor = None, 999
        for d in self.herois.values():
            if d["vida"] > 0:
                dist = abs(d["coluna"] - pd[0]) + abs(d["linha"] - pd[1])
                if dist < menor:
                    menor, alvo = dist, d
        if not alvo:
            return
        destino = (alvo["coluna"], alvo["linha"])

        if menor == 1:
            if not ataque_manual:
                nome = alvo["classe"]
                self.log(f"Dragão ataca {NOMES_EXIBICAO[nome]}! -{DANO_DRAGAO_FIXO} HP")
                self.aplicar_dano(nome, DANO_DRAGAO_FIXO)
                self.verificar_estado()
                self._dragao_aleatorio = random.randint(2, 4)
            return

        bloqueados = set(self.obstaculos)
        bloqueados.update(p for p, t in self.estruturas.items() if t != "dragao")
        for d in self.herois.values():
            pos_h = (d["coluna"], d["linha"])
            if (d["vida"] > 0 or d["turnos_morto"] > 0) and pos_h != destino:
                bloqueados.add(pos_h)

        vizinhos = [(c, l) for c, l in ((pd[0] + 1, pd[1]), (pd[0] - 1, pd[1]),
                                        (pd[0], pd[1] + 1), (pd[0], pd[1] - 1))
                    if 0 <= c < GRADE and 0 <= l < GRADE and (c, l) not in bloqueados]
        if not vizinhos:
            return

        if self._dragao_aleatorio > 0:
            proximo = random.choice(vizinhos)
            self._dragao_aleatorio -= 1
        else:
            proximo = bfs_proximo_passo(pd, destino, bloqueados)
            if proximo is None:
                proximo = min(vizinhos, key=lambda p: abs(p[0] - destino[0]) + abs(p[1] - destino[1]))
            if random.random() < 0.30:
                self._dragao_aleatorio = random.randint(1, 3)

        del self.estruturas[pd]
        self.estruturas[proximo] = "dragao"
        iniciar_loop_dragao()
        musica_volume(VOL_MUSICA_DRAGAO)

    # ---------------- turno e entrada ----------------
    def pos_turno(self, ataque):
        self.turnos += 1
        self.verificar_protecao()
        for nome, d in self.herois.items():
            if d["vida"] <= 0 and d["turnos_morto"] > 0:
                d["turnos_morto"] -= 1
                if d["turnos_morto"] == 0:
                    self.log(f"O corpo de {NOMES_EXIBICAO[nome]} desapareceu...")
        self.mover_dragao(ataque)
        if self.herois[self.sel]["vida"] <= 0:
            for nome, d in self.herois.items():
                if d["vida"] > 0:
                    self.sel = nome
                    self.log(f"Seleção trocada para {NOMES_EXIBICAO[nome]}.")
                    break

    def acao_tecla(self, key):
        """Interpreta uma tecla durante a exploração. Retorna (passou_turno, foi_ataque)."""
        if key in TECLAS_HEROI:
            novo = TECLAS_HEROI[key]
            if self.herois[novo]["vida"] <= 0:
                self.log(f"{NOMES_EXIBICAO[novo]} está incapacitado!")
            else:
                self.sel = novo
            return False, False
        if key == pygame.K_SPACE:
            if self.herois[self.sel]["vida"] <= 0:
                return False, False
            ok = self.atacar_fortaleza() if not self.dragao_desperto else self.atacar_dragao()
            return ok, ok
        if key == pygame.K_c:
            return self.curar(self.sel), False
        if key == pygame.K_p:
            return self.proteger(self.sel), False
        if key == pygame.K_v:
            return self.reviver(), False
        if key in DIRECOES:
            return self.mover(*DIRECOES[key]), False
        return False, False

    def tratar_tecla(self, key):
        if self.estado == "CAPA":
            self.estado, self.pagina = "TELA_INICIAL", 1
        elif self.estado == "TELA_INICIAL":
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                self.avancar_pagina()
            elif key == pygame.K_LEFT:
                self.pagina = max(1, self.pagina - 1)
        elif key == pygame.K_r:
            self.reiniciar()
        elif self.estado == "EXPLORACAO":
            passou, ataque = self.acao_tecla(key)
            if passou and self.estado == "EXPLORACAO":
                self.pos_turno(ataque)
            elif passou:                               # a ação encerrou a partida
                self.turnos += 1

    def avancar_pagina(self):
        if self.pagina < 3:
            self.pagina += 1
        else:
            self.estado = "EXPLORACAO"
            self.log("Boa sorte, heróis de Eldoria!")


# ==========================================================================
# RENDERIZAÇÃO — TELAS ESPECIAIS
# ==========================================================================


def desenhar_capa(j, pos, clicou, agora):
    elapsed = agora - j.t_capa
    if IMG_CAPA:
        tela.blit(IMG_CAPA, (0, 0))
    else:
        tela.blit(FUNDO_MENU, (0, 0))
        texto(tela, "ELDORIA", F_GRANDE, C_OURO, (LARGURA // 2, ALTURA // 2 - 40), "center")
    tela.blit(_cache_gradiente_capa(), (0, ALTURA - 220))

    progresso = min(elapsed / DURACAO_CAPA_MS, 1.0)
    bw, bh = 300, 6
    bx, by = LARGURA // 2 - bw // 2, ALTURA - 56
    pygame.draw.rect(tela, (60, 48, 36), (bx, by, bw, bh), border_radius=3)
    pygame.draw.rect(tela, C_OURO, (bx, by, int(bw * progresso), bh), border_radius=3)

    pulso = int(190 + 65 * math.sin(agora / 400))
    texto(tela, "Clique para continuar", F_PEQ, (pulso, pulso, int(pulso * 0.75)),
          (LARGURA // 2, ALTURA - 40), "midtop")
    if elapsed < 700:                                   # fade-in
        s = _rect_alpha(LARGURA, ALTURA, (0, 0, 0, int(255 * (1 - elapsed / 700))))
        tela.blit(s, (0, 0))
    if elapsed >= DURACAO_CAPA_MS or clicou:
        j.estado, j.pagina = "TELA_INICIAL", 1


@lru_cache(maxsize=1)
def _cache_gradiente_capa():
    return gradiente_alpha(LARGURA, 220, (0, 0, 0), 0, 200)


def _montar_pagina(n):
    """Renderiza o conteúdo estático de uma página do tutorial (cacheado)."""
    s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    cartao(s, (40, 34, LARGURA - 80, ALTURA - 68), (30, 25, 22), C_OURO_ESC, 18, esp=3)
    texto(s, TITULOS_PAGINA[n], F_TIT, C_OURO, (80, 52))
    texto(s, f"{n} / 3", F_PEQ, C_TEXTO_SUAVE, (LARGURA - 80, 64), "topright")
    divisor(s, 76, 104, LARGURA - 152)
    largura = LARGURA - 160

    if n == 1:
        desenhar_bloco(s, TUTORIAL_LENDA, F_TUT, 80, 122, largura)
        cena = [("fortaleza1", -250), ("fortaleza2", -125), ("dragao_acordado", 0),
                ("fortaleza3", 125), ("santuario", 255)]
        base_y = 600
        for chave, dx in cena:
            img = VISUAIS[chave]
            cx = LARGURA // 2 + dx
            s.blit(_sombra_elipse(img.get_width() * 0.8), (cx - img.get_width() * 0.4, base_y - 8))
            s.blit(img, (cx - img.get_width() // 2, base_y - img.get_height()))
    elif n == 2:
        y = 120
        for chave, nome, desc in TUTORIAL_HEROIS:
            cartao(s, (70, y, LARGURA - 140, 84), (46, 39, 34), C_CARD_BORDA, 12)
            pygame.draw.rect(s, COR_CLASSE[chave], (70, y + 14, 5, 56), border_radius=3)
            s.blit(IMG_HEROI[chave], (88, y + 12))
            texto(s, nome, F_NORMAL, COR_CLASSE[chave], (166, y + 8))
            for i, linha in enumerate(quebrar_texto(desc, F_PEQ, LARGURA - 140 - 120)):
                texto(s, linha, F_PEQ, C_TEXTO, (166, y + 40 + i * 20))
            y += 92
    else:
        desenhar_bloco(s, TUTORIAL_OBJETIVO, F_PEQ, 80, 122, 400)
        pygame.draw.line(s, C_CARD_BORDA, (496, 122), (496, 590), 1)
        texto(s, "Controles", F_NORMAL, C_OURO, (520, 122))
        y = 160
        lh = F_PEQ.get_linesize()
        for tecla, desc in TUTORIAL_CONTROLES:
            tecla_visual(s, tecla, 520, y + 1, 112)
            linhas = quebrar_texto(desc, F_PEQ, 245)
            for i, linha in enumerate(linhas):
                texto(s, linha, F_PEQ, C_TEXTO, (652, y + 3 + i * lh))
            y += max(36, len(linhas) * lh + 8) + 8
    return s


def desenhar_tutorial(j, pos, clicou, agora):
    tela.blit(FUNDO_MENU, (0, 0))
    if j.pagina not in j.cache_paginas:
        j.cache_paginas[j.pagina] = _montar_pagina(j.pagina)
    tela.blit(j.cache_paginas[j.pagina], (0, 0))

    y_btn = ALTURA - 112
    cx = LARGURA // 2
    if j.pagina < 3:
        principal = botao(tela, "Continuar", (cx - 110, y_btn, 220, 50), C_OURO, pos)
    else:
        principal = botao(tela, "Iniciar Jogo", (cx - 120, y_btn, 240, 50), C_OK, pos)
    voltar = None
    if j.pagina > 1:
        voltar = botao(tela, "Voltar", (80, y_btn, 140, 50), C_CARD, pos, C_TEXTO, F_NORMAL)
    if clicou:
        if principal.collidepoint(pos):
            j.avancar_pagina()
        elif voltar and voltar.collidepoint(pos):
            j.pagina -= 1


def _desenhar_stats(linhas, y, cor, cx=LARGURA // 2):
    for s in linhas:
        texto(tela, s, F_TUT, cor, (cx, y), "midtop")
        y += 36
    return y


def desenhar_vitoria(j, pos, clicou, agora):
    t = (agora - j.t_fim) / 1000.0
    tela.blit(fundo_cache("vitoria"), (0, 0))
    cx, cy = LARGURA // 2, ALTURA // 2
    for i in range(24):                                  # partículas orbitando
        ang = (i / 24) * 2 * math.pi + t * 0.5
        rad = 320 + 20 * math.sin(t * 2 + i)
        px, py = int(cx + math.cos(ang) * rad), int(cy + math.sin(ang) * rad * 0.45)
        tam = max(2, int(4 + 2 * math.sin(t * 3 + i)))
        pygame.draw.circle(tela, (230, int(190 + 40 * math.sin(t + i)),
                                  int(60 + 50 * math.cos(t * 2 + i))), (px, py), tam)
    pw, ph = 720, 520
    px, py = cx - pw // 2, cy - ph // 2
    tela.blit(_rect_alpha(pw, ph, (10, 8, 6, 205), 18), (px, py))
    pygame.draw.rect(tela, C_OURO, (px, py, pw, ph), 3, border_radius=18)

    base = _surf_texto("VITÓRIA!", F_GRANDE, (255, 220, 50), True)
    esc = 1.0 + 0.05 * math.sin(t * 3)
    grande = pygame.transform.smoothscale(base, (int(base.get_width() * esc), int(base.get_height() * esc)))
    tela.blit(grande, grande.get_rect(midtop=(cx, py + 16)))
    texto(tela, "O Dragão foi derrotado! Eldoria está salva!", F_NORMAL, (255, 245, 200),
          (cx, py + 104), "midtop")
    vivos = sum(1 for h in j.herois.values() if h["vida"] > 0)
    y = _desenhar_stats([f"Turnos jogados: {j.turnos}", f"Heróis sobreviventes: {vivos} / 5",
                         "Fortalezas destruídas: 3 / 3"], py + 148, (225, 205, 155))
    y += 10
    for nome, d in j.herois.items():
        vivo = d["vida"] > 0
        cor = COR_CLASSE[nome] if vivo else (130, 130, 130)
        texto(tela, NOMES_EXIBICAO[nome], F_PEQ, cor, (cx - 260, y))
        barra_hp(tela, cx - 120, y + 4, 200, 12, max(0, d["vida"]), d["vida_max"])
        texto(tela, f"{max(0, d['vida'])}/{d['vida_max']}", F_PEQ, cor, (cx + 96, y))
        y += 30
    btn = botao(tela, "Jogar Novamente", (cx - 140, py + ph - 70, 280, 52), C_OURO, pos)
    if clicou and btn.collidepoint(pos):
        j.reiniciar()


_EMBERS = None


def desenhar_derrota(j, pos, clicou, agora):
    global _EMBERS
    t = (agora - j.t_fim) / 1000.0
    tela.blit(fundo_cache("derrota"), (0, 0))
    if _EMBERS is None:
        rng = random.Random(3)
        _EMBERS = [(rng.randint(0, LARGURA), rng.randint(0, ALTURA), rng.uniform(25, 80),
                    rng.randint(1, 4), rng.randint(30, 110)) for _ in range(45)]
    for x, y0, vel, tam, g in _EMBERS:                    # brasas subindo
        pygame.draw.circle(tela, (230, g, 0), (int(x + 12 * math.sin(t + y0)),
                                               int((y0 - t * vel) % ALTURA)), tam)
    cx, cy = LARGURA // 2, ALTURA // 2
    pw, ph = 720, 500
    px, py = cx - pw // 2, cy - ph // 2
    tela.blit(_rect_alpha(pw, ph, (10, 6, 6, 215), 18), (px, py))
    pygame.draw.rect(tela, (160, 40, 40), (px, py, pw, ph), 3, border_radius=18)

    texto(tela, "DERROTA", F_GRANDE, C_PERIGO,
          (cx + random.randint(-2, 2), py + 20 + random.randint(-1, 1)), "midtop")
    texto(tela, "Todos os heróis caíram...", F_NORMAL, (225, 160, 160), (cx, py + 108), "midtop")
    y = _desenhar_stats([f"Turnos sobrevividos: {j.turnos}",
                         f"Fortalezas destruídas: {min(j.idx_fort, 3)} / 3",
                         f"Inimigos restantes: {len(j.inimigos)}"], py + 152, (205, 155, 155))
    y += 10
    for nome in j.herois:
        texto(tela, f"{NOMES_EXIBICAO[nome]} — Caído", F_PEQ, (200, 90, 90), (cx, y), "midtop")
        y += 28
    btn = botao(tela, "Tentar Novamente", (cx - 150, py + ph - 70, 300, 52), C_PERIGO, pos, C_TEXTO)
    if clicou and btn.collidepoint(pos):
        j.reiniciar()


# ==========================================================================
# RENDERIZAÇÃO — JOGO
# ==========================================================================


def desenhar_mundo(j, agora):
    tela.blit(FUNDO_TAB, (0, 0))

    pd = j.pos_dragao()
    if pd:
        tela.blit(_rect_alpha(LC - 1, AC - 1, (50, 50, 50, 120)), (pd[0] * LC + 1, pd[1] * AC + 1))

    d_sel = j.herois[j.sel]
    if d_sel["vida"] > 0:
        c0, l0 = d_sel["coluna"], d_sel["linha"]
        for dc, dl in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            c, l = c0 + dc, l0 + dl
            if (0 <= c < GRADE and 0 <= l < GRADE and (c, l) != (0, 0)
                    and (c, l) not in j.obstaculos
                    and j.estruturas.get((c, l)) in (None, "santuario")):
                tela.blit(_rect_alpha(LC, AC, C_DESTAQUE), (c * LC, l * AC))
        pulso = int(150 + 90 * math.sin(agora / 280))
        tela.blit(_rect_alpha(LC, AC, (255, 230, 90, 45)), (c0 * LC, l0 * AC))
        pygame.draw.rect(tela, (pulso, pulso, 60), (c0 * LC + 1, l0 * AC + 1, LC - 2, AC - 2),
                         2, border_radius=4)

    # ----- fila de sprites ordenada por profundidade -----
    fila = []

    def add(img, cx, cy, prof=None):
        w, h = img.get_size()
        fila.append((cy if prof is None else prof, img, int(cx - w / 2), int(cy - h / 2)))

    for (col, lin), tipo in j.estruturas.items():
        if tipo != "dragao":
            add(VISUAIS[tipo], *centro_celula(col, lin))
    for (col, lin), tipo in j.obstaculos.items():
        add(VISUAIS[tipo], *centro_celula(col, lin))
    for (col, lin), tipo in j.itens.items():
        cx, cy = centro_celula(col, lin)
        add(VISUAIS[tipo], cx, cy + 2.5 * math.sin(agora / 380 + col * 1.7), prof=cy - 40)
    for col, lin in j.inimigos:
        cx, cy = centro_celula(col, lin)
        add(IMG_INIMIGO, cx, cy + 2 * math.sin(agora / 260 + col * 0.9 + lin * 0.5))
    if pd:
        cx, cy = j.vis["dragao"]
        if j.dragao_desperto:
            cy += 2 * math.sin(agora / 250)
        add(VISUAIS["dragao_acordado"] if j.dragao_desperto else VISUAIS["dragao"], cx, cy)

    barras, caidos = [], []
    for nome, d in j.herois.items():
        vivo = d["vida"] > 0
        if (not vivo and d["turnos_morto"] <= 0) or (d["coluna"], d["linha"]) == (0, 0):
            continue
        cx, cy = j.vis[nome]
        img = IMG_HEROI[nome] if vivo else IMG_HEROI_PB[nome]
        add(img, cx, cy)
        if vivo:
            barras.append((cx, cy - img.get_height() / 2, nome))
        else:
            caidos.append((cx, cy - img.get_height() / 2, d["turnos_morto"]))

    fila.sort(key=lambda t: t[0])
    for _, img, x, y in fila:
        w, h = img.get_size()
        tela.blit(_sombra_elipse(w * 0.7), (int(x + w * 0.15), int(y + h - 9)))
        tela.blit(img, (x, y))

    for cx, ytop, nome in barras:
        barra_hp(tela, int(cx - 21), int(ytop - 8), 42, 6, j.hp_vis[nome], VIDA_HEROI)
        if nome == j.sel:
            off = 2 * math.sin(agora / 200)
            yy = int(ytop - 20 + off)
            pygame.draw.polygon(tela, C_OURO, [(int(cx) - 5, yy), (int(cx) + 5, yy), (int(cx), yy + 7)])
    for cx, ytop, turnos in caidos:
        pygame.draw.circle(tela, (20, 16, 14), (int(cx), int(ytop)), 10)
        pygame.draw.circle(tela, C_PERIGO, (int(cx), int(ytop)), 10, 2)
        texto(tela, str(turnos), F_MINI, C_TEXTO, (int(cx), int(ytop)), "center", sombra=False)

    for p in j.popups:                                    # números flutuantes
        t = (agora - p["t0"]) / DURACAO_POPUP_MS
        alfa = 255 if t < 0.6 else int(255 * (1 - (t - 0.6) / 0.4))
        s = _surf_texto(p["txt"], F_NORMAL, p["cor"], True).copy()
        s.set_alpha(max(0, alfa))
        tela.blit(s, s.get_rect(center=(int(p["x"]), int(p["y"] - 34 * (1 - (1 - t) ** 2)))))


def desenhar_minimapa(j, ox, oy, c=14):
    tela.blit(MINIMAPA_BASE, (ox, oy))
    for (col, lin) in j.obstaculos:
        pygame.draw.rect(tela, (52, 78, 44), (ox + col * c + 4, oy + lin * c + 4, c - 8, c - 8))
    for (col, lin) in j.inimigos:
        pygame.draw.circle(tela, (200, 70, 70), (ox + col * c + c // 2, oy + lin * c + c // 2), 2)
    for (col, lin), tipo in j.estruturas.items():
        x, y = ox + col * c, oy + lin * c
        if tipo.startswith("fortaleza"):
            ativa = tipo == ORDEM_FORTALEZAS[min(j.idx_fort, 2)]
            pygame.draw.rect(tela, C_OURO if ativa else (150, 130, 90), (x + 2, y + 2, c - 4, c - 4),
                             border_radius=2)
        elif tipo == "santuario":
            m = (x + c // 2, y + c // 2)
            pygame.draw.polygon(tela, (180, 130, 240), [(m[0], y + 1), (x + c - 1, m[1]),
                                                        (m[0], y + c - 1), (x + 1, m[1])])
        elif tipo == "dragao":
            pygame.draw.circle(tela, C_PERIGO if j.dragao_desperto else (150, 150, 150),
                               (x + c // 2, y + c // 2), c // 2 - 1)
    for nome, d in j.herois.items():
        if d["vida"] > 0:
            m = (ox + d["coluna"] * c + c // 2, oy + d["linha"] * c + c // 2)
            pygame.draw.circle(tela, COR_CLASSE[nome], m, 4)
            if nome == j.sel:
                pygame.draw.circle(tela, C_OURO, m, 6, 1)


def _objetivo_atual(j):
    if j.idx_fort < len(ORDEM_FORTALEZAS):
        return f"Destrua a Fortaleza {j.idx_fort + 1}\n(2+ heróis por perto)"
    if not j.santuario_visitado:
        return "Vá ao Santuário\n(canto inferior direito)"
    return "Derrote o Dragão!\nUse ESPAÇO perto dele"


def desenhar_sidebar(j, agora):
    tela.blit(UI_SIDEBAR, (X_SB, 0))
    pulso = int(205 + 30 * math.sin(agora / 700))
    texto(tela, "Eldoria", F_TIT, (pulso, int(pulso * 0.82), 70), (CX_SB, 6), "midtop")
    texto(tela, f"Turno {j.turnos}", F_PEQ, C_TEXTO_SUAVE, (CX_SB, 46), "midtop")

    x, w = X_SB + 8, L_SB - 16
    y = 74
    for i, chave in enumerate(ORDEM_FORTALEZAS):
        ativa, destruida = i == j.idx_fort, i < j.idx_fort
        cartao(tela, (x, y, w, 58), borda=C_OURO if ativa else C_CARD_BORDA)
        ico = ICO_FORT_PB[chave] if destruida else ICO_FORT[chave]
        tela.blit(ico, ico.get_rect(center=(x + 36, y + 29)))
        texto(tela, f"Fortaleza {i + 1}", F_PEQ, C_OURO if ativa else C_TEXTO, (x + 68, y + 4))
        if destruida:
            texto(tela, "Destruída", F_MINI, C_TEXTO_SUAVE, (x + 68, y + 32))
        else:
            hp = max(0, j.vida_estruturas[chave])
            barra_hp(tela, x + 68, y + 28, w - 78, 10, j.hp_vis[chave], VIDA_FORTALEZA)
            texto(tela, f"{hp}/{VIDA_FORTALEZA}", F_MINI, C_TEXTO_SUAVE, (x + 68, y + 40))
        y += 63

    # Dragão
    borda = C_PERIGO if j.dragao_desperto else C_CARD_BORDA
    cartao(tela, (x, y, w, 88), borda=borda)
    ico = ICO_DRAGAO_AC if j.dragao_desperto else ICO_DRAGAO
    tela.blit(ico, ico.get_rect(center=(x + 38, y + 44)))
    texto(tela, "Dragão", F_PEQ, C_TEXTO, (x + 76, y + 6))
    if not j.dragao_desperto:
        status, cor_s = "Adormecido", C_TEXTO_SUAVE
    elif not j.santuario_visitado:
        status, cor_s = "Desperto (selado)", C_AVISO
    else:
        status, cor_s = "Vulnerável!", C_PERIGO
    texto(tela, status, F_MINI, cor_s, (x + 76, y + 30))
    hp_d = max(0, j.vida_estruturas["dragao"])
    barra_hp(tela, x + 76, y + 50, w - 86, 12, j.hp_vis["dragao"], VIDA_DRAGAO)
    texto(tela, f"{hp_d}/{VIDA_DRAGAO}", F_MINI, C_TEXTO_SUAVE, (x + 76, y + 66))
    y += 96

    # Contadores
    n_pocao = sum(1 for v in j.itens.values() if v == "pocao")
    n_perg = len(j.itens) - n_pocao
    contadores = ((ICO_INIMIGO, len(j.inimigos), (230, 110, 100)),
                  (ICO_POCAO, n_pocao, C_OK), (ICO_PERGAMINHO, n_perg, (170, 150, 250)))
    cw = (w - 8) // 3
    for i, (ico, n, cor) in enumerate(contadores):
        cx0 = x + i * (cw + 4)
        cartao(tela, (cx0, y, cw, 38), sombra=False, raio=8, esp=1)
        tela.blit(ico, (cx0 + 6, y + 4))
        texto(tela, str(n), F_PEQ, cor if n else C_TEXTO_SUAVE, (cx0 + 34, y + 8))
    y += 46

    # Objetivo
    cartao(tela, (x, y, w, 80), (50, 42, 30), C_OURO_ESC)
    texto(tela, "OBJETIVO", F_MINI, C_OURO, (x + 10, y + 6))
    for i, linha in enumerate(quebrar_texto(_objetivo_atual(j), F_PEQ, w - 20)):
        texto(tela, linha, F_PEQ, C_TEXTO, (x + 10, y + 24 + i * 20))
    y += 88

    # Minimapa
    cartao(tela, (x, y, w, 198))
    texto(tela, "MAPA", F_MINI, C_OURO, (x + 10, y + 6))
    desenhar_minimapa(j, x + (w - 168) // 2, y + 24)


def _chip(sup, x, y, rotulo, valor, cor_valor=C_TEXTO):
    wl = F_MINI.size(rotulo)[0]
    wv = F_PEQ.size(valor)[0]
    w = wl + wv + 24
    sup.blit(_rect_alpha(w, 26, (0, 0, 0, 110), 13), (x, y))
    pygame.draw.rect(sup, C_CARD_BORDA, (x, y, w, 26), 1, border_radius=13)
    texto(sup, rotulo, F_MINI, C_OURO, (x + 10, y + 7))
    texto(sup, valor, F_PEQ, cor_valor, (x + 14 + wl, y + 3))
    return x + w + 8


def desenhar_painel_inferior(j, agora):
    tela.blit(UI_INFERIOR, (0, TAB_H))
    sel = j.sel
    d = j.herois[sel]
    pos = POS_PERSONAGEM[sel]
    tela.blit(RETRATOS[sel], pos["retrato"])

    nome = NOMES_EXIBICAO[sel] + (" (CAÍDO)" if d["vida"] <= 0 else "")
    wn, hn = F_NORMAL.size(nome)
    tx, ty = pos["texto"]
    tela.blit(_rect_alpha(wn + 24, hn + 6, (14, 11, 9, 200), 10), (tx - 12, ty - 3))
    pygame.draw.rect(tela, COR_CLASSE[sel], (tx - 12, ty - 3, wn + 24, hn + 6), 2, border_radius=10)
    texto(tela, nome, F_NORMAL, C_TEXTO, (tx, ty))

    X = 340
    texto(tela, "HP", F_NORMAL, C_OURO, (X, 532))
    barra_hp(tela, X + 40, 540, 300, 16, j.hp_vis[sel], d["vida_max"])
    texto(tela, f"{max(0, d['vida'])}/{d['vida_max']}", F_PEQ, C_TEXTO, (X + 352, 536))

    bonus = round((d["bonus_ataque"] + d["pergaminhos"] * BONUS_PERGAMINHO - 1) * 100)
    cx = _chip(tela, X, 568, "Perg.", str(d["pergaminhos"]))
    cx = _chip(tela, cx, 568, "Bônus", f"+{bonus}%", C_OK if bonus else C_TEXTO)
    if sel == "mago":
        cx = _chip(tela, cx, 568, "Alcance", "3")
    elif sel == "arqueiro":
        cx = _chip(tela, cx, 568, "Crítico", f"{CHANCE_CRITICO_ARQUEIRO}%")
    elif sel == "escudeiro":
        alvo = d.get("protegendo")
        if alvo:
            rest = MAX_PROTECOES_POR_ALVO - j.herois[alvo]["protecoes_recebidas"]
            _chip(tela, cx, 568, "Protege", f"{NOMES_EXIBICAO[alvo]} ({max(0, rest)}/{MAX_PROTECOES_POR_ALVO})",
                  (150, 190, 255))
        else:
            _chip(tela, cx, 568, "Proteção", "inativa", C_TEXTO_SUAVE)

    # Registro de eventos (some suavemente)
    tela.blit(_rect_alpha(452, 80, (0, 0, 0, 90), 10), (X - 6, 602))
    j.log_msgs = [m for m in j.log_msgs if agora - m["tempo"] < LOG_VIDA_MS]
    for i, m in enumerate(j.log_msgs):
        idade = agora - m["tempo"]
        s = _surf_texto(m["texto"], F_PEQ, C_TEXTO, True)
        if idade > LOG_VIDA_MS - 1000:
            s = s.copy()
            s.set_alpha(int(255 * (LOG_VIDA_MS - idade) / 1000))
        tela.blit(s, (X, 606 + i * 18))

    texto(tela, "1-5 Herói   |   Setas/WASD Mover   |   Espaço Atacar", F_MINI, C_TEXTO_SUAVE, (X, 690))
    texto(tela, "C Curar   |   P Proteger   |   V Reviver   |   R Reiniciar", F_MINI, C_TEXTO_SUAVE, (X, 706))


def desenhar_jogo(j, pos, clicou, agora):
    desenhar_mundo(j, agora)
    desenhar_sidebar(j, agora)
    desenhar_painel_inferior(j, agora)


# ==========================================================================
# LOOP PRINCIPAL
# ==========================================================================


def viewport(tamanho):
    """Janela redimensionável com letterbox: mantém a proporção original."""
    w, h = tamanho
    esc = min(w / LARGURA, h / ALTURA)
    vw, vh = max(1, int(LARGURA * esc)), max(1, int(ALTURA * esc))
    return (w - vw) // 2, (h - vh) // 2, vw, vh, esc


def apresentar(shake):
    surf = pygame.display.get_surface()
    vx, vy, vw, vh, _ = viewport(surf.get_size())
    origem = tela if (vw, vh) == (LARGURA, ALTURA) else pygame.transform.smoothscale(tela, (vw, vh))
    if vx or vy or shake != (0, 0):
        surf.fill((10, 8, 6))
    surf.blit(origem, (vx + shake[0], vy + shake[1]))
    pygame.display.flip()


def main():
    j = Jogo()
    relogio = pygame.time.Clock()
    rodando = True
    while rodando:
        dt = min(relogio.tick(60) / 1000.0, 0.1)
        agora = pygame.time.get_ticks()
        clicou = False

        vx, vy, _, _, esc = viewport(pygame.display.get_surface().get_size())
        mx, my = pygame.mouse.get_pos()
        pos_mouse = (int((mx - vx) / esc), int((my - vy) / esc))

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                clicou = True
            elif ev.type == pygame.KEYDOWN:
                j.tratar_tecla(ev.key)

        j.atualizar(dt)

        if j.estado == "CAPA":
            desenhar_capa(j, pos_mouse, clicou, agora)
        elif j.estado == "TELA_INICIAL":
            desenhar_tutorial(j, pos_mouse, clicou, agora)
        elif j.estado == "VITORIA":
            desenhar_vitoria(j, pos_mouse, clicou, agora)
        elif j.estado == "DERROTA":
            desenhar_derrota(j, pos_mouse, clicou, agora)
        else:
            desenhar_jogo(j, pos_mouse, clicou, agora)

        tremendo = agora < j.shake_ate and j.estado == "EXPLORACAO"
        apresentar((random.randint(-3, 3), random.randint(-2, 2)) if tremendo else (0, 0))

    pygame.quit()


if __name__ == "__main__":
    main()