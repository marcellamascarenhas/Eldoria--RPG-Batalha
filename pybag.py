import asyncio
import pygame
import random
from collections import deque
import copy
import math

# ==========================================
# CONSTANTES DO JOGO
# ==========================================
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

# ==========================================
# POSICIONAMENTO DA SIDEBAR — DRAGÃO
# Ajuste aqui a posição independente das fortalezas
# ==========================================
DRAGAO_SB_Y_OFFSET = 8  # espaço extra antes do dragão na sidebar
DRAGAO_SB_Y_NOME = 4  # distância da imagem ao nome
DRAGAO_SB_Y_HP = 20  # distância do nome ao HP
DRAGAO_SB_Y_ESPACAMENTO = 36  # espaçamento abaixo do bloco do dragão

pygame.init()
pygame.mixer.init()

# ==========================================
# SISTEMA DE ÁUDIO
# Volumes calibrados: música principal baixa
# para efeitos se destacarem.
# ==========================================

CANAL_BATALHA_FINAL = None
CANAL_DRAGAO_LOOP = None
_dragao_loop_ativo = False


def _carregar_som(nome):
    try:
        return pygame.mixer.Sound(nome)
    except pygame.error:
        return None


try:
    # Música principal — bem baixa para efeitos se destacarem
    pygame.mixer.music.load("nova_musica.mp3")
    pygame.mixer.music.set_volume(0.30)
    pygame.mixer.music.play(-1)

    pygame.mixer.set_num_channels(16)
    CANAL_BATALHA_FINAL = pygame.mixer.Channel(7)
    CANAL_DRAGAO_LOOP = pygame.mixer.Channel(8)

    som_encontro_pocao = _carregar_som("potion.mp3")
    som_encontro_pergaminho = _carregar_som("pergaminho.mp3")
    som_morte_jogador = _carregar_som("morte_jogador.mp3")
    som_vitoria = _carregar_som("vitoria.mp3")
    som_derrota = _carregar_som("derrota.mp3")
    som_ataque_inimigo_dragao = _carregar_som("ataque_inimigo_dragao.mp3")
    som_ataque_fortaleza = _carregar_som("ataque_fortaleza.mp3")
    som_personagem_erra = _carregar_som("personagem_erra.mp3")
    som_cura = _carregar_som("cura.mp3")
    som_reviver = _carregar_som("som_reviver.mp3")
    som_escudeiro_protege = _carregar_som("escudeiro_protege.mp3")
    som_arqueiro_critico = _carregar_som("arqueiro_critico.mp3")
    som_fortaleza_caiu = _carregar_som("fortaleza_caiu.mp3")
    som_fortalezas_derrubadas = _carregar_som("fortalezas_derrubadas.mp3")
    som_dragao_acordado = _carregar_som("dragao_acordado.mp3")
    som_chegou_santuario = _carregar_som("chegou_santuario.mp3")

    som_dragao_loop = _carregar_som("dragao_movimentando.mp3")
    if som_dragao_loop:
        som_dragao_loop.set_volume(0.40)

    som_fundo_batalha_final = _carregar_som("fundo_batalha_final.mp3")
    if som_fundo_batalha_final:
        som_fundo_batalha_final.set_volume(0.55)

    MUSICA_FINAL_PATH = "musica_final.mp3"

except pygame.error as e:
    print(f"Aviso: Erro ao inicializar áudio: {e}")
    som_encontro_pocao = som_encontro_pergaminho = None
    som_morte_jogador = som_vitoria = som_derrota = None
    som_ataque_inimigo_dragao = som_ataque_fortaleza = som_personagem_erra = None
    som_cura = som_reviver = None
    som_escudeiro_protege = som_arqueiro_critico = None
    som_fortaleza_caiu = som_fortalezas_derrubadas = None
    som_dragao_acordado = som_chegou_santuario = None
    som_dragao_loop = som_fundo_batalha_final = None
    MUSICA_FINAL_PATH = None

LARGURA_ORIGINAL = 991
ALTURA_ORIGINAL = 730

janela = pygame.display.set_mode((LARGURA_ORIGINAL, ALTURA_ORIGINAL), pygame.RESIZABLE)
tela_virtual = pygame.Surface((LARGURA_ORIGINAL, ALTURA_ORIGINAL))
pygame.display.set_caption("Eldoria")

C_BG = (180, 156, 131)
C_GRID = (119, 148, 102)
C_CELL_BASE = (120, 189, 93)
C_HIGHLIGHT = (150, 255, 150, 130)
C_TEXTO = (0, 0, 0)
C_BORDA_TEXTO = (146, 114, 77)
C_SIDEBAR_BG = (160, 136, 111)
C_SOMBRA = (80, 60, 40)  # cor de sombra para decorações

LARGURA_CELULA = 792 // 12
ALTURA_CELULA = 530 // 12

try:
    fonte = pygame.font.Font('NewRocker-Regular.ttf', 24)
    fonte_pequena = pygame.font.Font('NewRocker-Regular.ttf', 18)
    fonte_tutorial = pygame.font.Font('NewRocker-Regular.ttf', 20)
    fonte_titulo = pygame.font.Font('NewRocker-Regular.ttf', 36)
    fonte_grande = pygame.font.Font('NewRocker-Regular.ttf', 72)
    fonte_media = pygame.font.Font('NewRocker-Regular.ttf', 48)
except FileNotFoundError:
    fonte = pygame.font.Font(None, 24)
    fonte_pequena = pygame.font.Font(None, 18)
    fonte_tutorial = pygame.font.Font(None, 22)
    fonte_titulo = pygame.font.Font(None, 36)
    fonte_grande = pygame.font.Font(None, 72)
    fonte_media = pygame.font.Font(None, 48)

pontos_criticos = [(0, 0), (2, 5), (5, 10), (8, 3), (6, 6), (11, 11)]
AREA_BASE = {(0, 0), (1, 0), (0, 1), (1, 1)}
POS_SANTUARIO = (11, 11)
posicoes_ocupadas = set(pontos_criticos)

NOMES_EXIBICAO = {
    "guerreiro": "Guerreiro",
    "arqueiro": "Arqueiro",
    "curandeiro": "Curandeira",
    "mago": "Mago",
    "escudeiro": "Escudeira",
}


# ==========================================
# FUNÇÕES UTILITÁRIAS
# ==========================================

def tocar_som(som):
    """Toca um Sound no próximo canal livre disponível."""
    if som:
        try:
            som.play()
        except Exception:
            pass


def iniciar_loop_dragao():
    """Inicia loop de som do dragão no canal dedicado.
    Não reinicia se já estiver tocando."""
    global _dragao_loop_ativo
    if CANAL_DRAGAO_LOOP and som_dragao_loop and not _dragao_loop_ativo:
        try:
            CANAL_DRAGAO_LOOP.play(som_dragao_loop, loops=-1)
            _dragao_loop_ativo = True
        except Exception:
            pass


def parar_loop_dragao():
    """Para o loop de som do dragão."""
    global _dragao_loop_ativo
    if CANAL_DRAGAO_LOOP:
        try:
            CANAL_DRAGAO_LOOP.stop()
        except Exception:
            pass
    _dragao_loop_ativo = False


def iniciar_musica_batalha_final():
    """Liga a camada de batalha final (canal 7, loop).
    Baixa drásticamente a música principal."""
    if CANAL_BATALHA_FINAL and som_fundo_batalha_final:
        try:
            if not CANAL_BATALHA_FINAL.get_busy():
                CANAL_BATALHA_FINAL.play(som_fundo_batalha_final, loops=-1)
            pygame.mixer.music.set_volume(0.08)
        except Exception:
            pass


def parar_toda_musica():
    """Para música principal, loop do dragão e batalha final."""
    parar_loop_dragao()
    if CANAL_BATALHA_FINAL:
        try:
            CANAL_BATALHA_FINAL.stop()
        except Exception:
            pass
    pygame.mixer.music.stop()


def tocar_musica_final():
    """Troca para musica_final.mp3 na vitória."""
    parar_toda_musica()
    if MUSICA_FINAL_PATH:
        try:
            pygame.mixer.music.load(MUSICA_FINAL_PATH)
            pygame.mixer.music.set_volume(0.70)
            pygame.mixer.music.play(-1)
        except Exception:
            pass


def carregar_imagem(nome_arquivo, tamanho):
    try:
        return pygame.transform.scale(
            pygame.image.load(nome_arquivo).convert_alpha(), tamanho)
    except pygame.error:
        print(f"ERRO: Imagem '{nome_arquivo}' não encontrada!")
        surf = pygame.Surface(tamanho, pygame.SRCALPHA)
        surf.fill((255, 0, 255, 255))
        return surf


def area_segura_para_obstaculo(col, lin):
    for cx, cy in pontos_criticos:
        if abs(col - cx) <= 1 and abs(lin - cy) <= 1:
            return False
    return True


def muito_proximo(col, lin, grupo_existente, dist_min=1):
    for item in grupo_existente:
        cx, cy = item if isinstance(item, tuple) else (item["coluna"], item["linha"])
        if abs(col - cx) <= dist_min and abs(lin - cy) <= dist_min:
            return True
    return False


def desenhar_destaque_transparente(tela, x, y, largura, altura, cor_rgba):
    s = pygame.Surface((largura, altura), pygame.SRCALPHA)
    s.fill(cor_rgba)
    tela.blit(s, (x, y))


def desenhar_texto_com_contorno(superficie, texto, fonte_usada, cor_texto, cor_borda, x, y):
    """Renderiza texto com contorno de 8 direções para máxima legibilidade."""
    offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    borda_surf = fonte_usada.render(texto, True, cor_borda)
    for ox, oy in offsets:
        superficie.blit(borda_surf, (x + ox, y + oy))
    superficie.blit(fonte_usada.render(texto, True, cor_texto), (x, y))


def desenhar_texto_multilinha(superficie, texto, fonte_usada, cor_texto, cor_borda,
                              x, y, max_largura, alinhamento="esquerda", centro_x=None):
    """Quebra texto longo respeitando max_largura. Suporta alinhamento central."""
    linhas_originais = texto.split('\n')
    y_offset = y
    altura_linha = fonte_usada.get_linesize()
    for linha_orig in linhas_originais:
        if not linha_orig.strip():
            y_offset += altura_linha // 2
            continue
        palavras = linha_orig.split(' ')
        linha_atual = ""
        for palavra in palavras:
            teste = linha_atual + palavra + " "
            if fonte_usada.size(teste)[0] < max_largura:
                linha_atual = teste
            else:
                _render_linha(superficie, linha_atual.rstrip(), fonte_usada, cor_texto, cor_borda,
                              x, y_offset, alinhamento, centro_x, max_largura)
                y_offset += altura_linha
                linha_atual = palavra + " "
        if linha_atual.strip():
            _render_linha(superficie, linha_atual.rstrip(), fonte_usada, cor_texto, cor_borda,
                          x, y_offset, alinhamento, centro_x, max_largura)
            y_offset += altura_linha
    return y_offset  # retorna y final para encadeamento


def _render_linha(superficie, linha, fonte_usada, cor_texto, cor_borda,
                  x, y, alinhamento, centro_x, max_largura):
    """Renderiza uma única linha já quebrada, com alinhamento."""
    w_linha = fonte_usada.size(linha)[0]
    if alinhamento == "centro" and centro_x is not None:
        rx = centro_x - w_linha // 2
    elif alinhamento == "direita":
        rx = x + max_largura - w_linha
    else:
        rx = x
    desenhar_texto_com_contorno(superficie, linha, fonte_usada, cor_texto, cor_borda, rx, y)


def desenhar_botao(tela, texto, x, y, w, h, cor_fundo, cor_hover, pos_mouse_virtual,
                   fonte_btn=None, sombra=True):
    """Botão com sombra e efeito hover."""
    if fonte_btn is None:
        fonte_btn = fonte_titulo
    rect = pygame.Rect(x, y, w, h)
    # Sombra
    if sombra:
        pygame.draw.rect(tela, (60, 40, 20), (x + 3, y + 4, w, h), border_radius=10)
    cor = cor_hover if rect.collidepoint(pos_mouse_virtual) else cor_fundo
    pygame.draw.rect(tela, cor, rect, border_radius=10)
    pygame.draw.rect(tela, C_BORDA_TEXTO, rect, 4, border_radius=10)
    # Brilho sutil no topo
    brilho = pygame.Surface((w - 8, h // 3), pygame.SRCALPHA)
    brilho.fill((255, 255, 255, 22))
    tela.blit(brilho, (x + 4, y + 3))
    w_t = fonte_btn.render(texto, True, C_TEXTO).get_width()
    h_t = fonte_btn.get_height()
    desenhar_texto_com_contorno(tela, texto, fonte_btn, C_TEXTO, C_BORDA_TEXTO,
                                x + (w - w_t) // 2, y + (h - h_t) // 2)
    return rect


def desenhar_barra_hp(superficie, x, y, largura, altura, hp_atual, hp_max):
    pct = hp_atual / hp_max if hp_max > 0 else 0
    cor_hp = (0, 200, 0) if pct > 0.5 else (220, 200, 0) if pct > 0.25 else (200, 0, 0)
    pygame.draw.rect(superficie, (50, 50, 50), (x, y, largura, altura))
    pygame.draw.rect(superficie, cor_hp, (x, y, int(largura * pct), altura))
    pygame.draw.rect(superficie, C_BORDA_TEXTO, (x, y, largura, altura), 1)


def desenhar_painel(superficie, x, y, w, h, cor_fundo, cor_borda, raio=12, sombra_offset=4):
    """Painel decorativo com sombra projetada."""
    if sombra_offset > 0:
        sombra_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        sombra_surf.fill((0, 0, 0, 60))
        superficie.blit(sombra_surf, (x + sombra_offset, y + sombra_offset))
    pygame.draw.rect(superficie, cor_fundo, (x, y, w, h), border_radius=raio)
    pygame.draw.rect(superficie, cor_borda, (x, y, w, h), 3, border_radius=raio)


def desenhar_divisor_ornamentado(superficie, x, y, largura, cor):
    """Linha divisória com pequenos diamantes nas extremidades."""
    cy = y + 3
    pygame.draw.line(superficie, cor, (x + 8, cy), (x + largura - 8, cy), 1)
    for dx in [x + 4, x + largura - 4]:
        pts = [(dx, cy - 3), (dx + 3, cy), (dx, cy + 3), (dx - 3, cy)]
        pygame.draw.polygon(superficie, cor, pts)


# ==========================================
# PATHFINDING BFS
# ==========================================
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
        for nc, nl in [(c + 1, l), (c - 1, l), (c, l + 1), (c, l - 1)]:
            v = (nc, nl)
            if 0 <= nc <= 11 and 0 <= nl <= 11 and v not in pai and v not in bloqueados:
                pai[v] = atual
                fila.append(v)
    return None


# ==========================================
# ESTRUTURAS DO MAPA
# ==========================================
mapa_estruturas = {
    (6, 6): "dragao",
    (2, 5): "fortaleza1",
    (5, 10): "fortaleza2",
    (8, 3): "fortaleza3",
    (11, 11): "santuario"
}

vida_estruturas = {
    "fortaleza1": VIDA_FORTALEZA,
    "fortaleza2": VIDA_FORTALEZA,
    "fortaleza3": VIDA_FORTALEZA,
    "dragao": VIDA_DRAGAO
}

ordem_fortalezas = ["fortaleza1", "fortaleza2", "fortaleza3"]
fortaleza_atual_index = 0
turnos_jogados = 0

lista_obstaculos_gerar = (["arvore_folhas"] * 3 + ["arvore_seca"] * 3 +
                          ["estatua"] * 3 + ["pedra"] * 3 + ["muro"] * 3)
lista_itens_gerar = ["pocao"] * 15 + ["pergaminho"] * 5

mapa_obstaculos = {}
mapa_itens = {}
lista_inimigos = []

visuais_objetos = {
    "arvore_folhas": carregar_imagem('Estruturas_ArvoresComFolhasV2.png', (60, 60)),
    "arvore_seca": carregar_imagem('Estruturas_ArvoresSemFolhasV2.png', (60, 60)),
    "estatua": carregar_imagem('Estruturas_Estatua.png', (70, 56)),
    "pedra": carregar_imagem('Estruturas_Pedra.png', (50, 50)),
    "muro": carregar_imagem('Estruturas_Muro.png', (65, 85)),
    "pocao": carregar_imagem('Item_Pocao.png', (45, 55)),
    "pergaminho": carregar_imagem('Item_PergaminhoV2.png', (45, 55)),
    "dragao": carregar_imagem('Dragao_Adormecido.png', (100, 120)),
    "dragao_acordado": carregar_imagem('Dragao_Acordado.png', (100, 120)),
    "fortaleza1": carregar_imagem('Fortaleza_1.png', (75, 55)),
    "fortaleza2": carregar_imagem('Fortaleza_2.png', (75, 55)),
    "fortaleza3": carregar_imagem('Fortaleza_3.png', (75, 55)),
    "santuario": carregar_imagem('Santuario_Dragao.png', (85, 55)),
    "base": carregar_imagem('base.png', (85, 65))
}

img_sidebar_inimigo = carregar_imagem('Sprite_Inimigo.png', (40, 52))
img_sidebar_pocao = carregar_imagem('Item_Pocao.png', (46, 58))
img_sidebar_pergaminho = carregar_imagem('Item_PergaminhoV2.png', (46, 58))


def inicializar_elementos_mapa():
    global mapa_obstaculos, mapa_itens, posicoes_ocupadas, lista_inimigos
    mapa_obstaculos.clear()
    mapa_itens.clear()
    posicoes_ocupadas = set(mapa_estruturas.keys())
    for obs in lista_obstaculos_gerar:
        while True:
            c, l = random.randint(0, 11), random.randint(0, 11)
            if (c, l) not in posicoes_ocupadas and area_segura_para_obstaculo(c, l):
                mapa_obstaculos[(c, l)] = obs
                posicoes_ocupadas.add((c, l))
                break
    for item in lista_itens_gerar:
        tentativas = 0
        while True:
            c, l = random.randint(0, 11), random.randint(0, 11)
            if (c, l) not in posicoes_ocupadas and (c, l) not in AREA_BASE:
                if tentativas < 50 and muito_proximo(c, l, mapa_itens.keys(), dist_min=1):
                    tentativas += 1;
                    continue
                mapa_itens[(c, l)] = item
                posicoes_ocupadas.add((c, l))
                break
    lista_inimigos.clear()
    for _ in range(30):
        tentativas = 0
        while True:
            c, l = random.randint(0, 11), random.randint(0, 11)
            if (c, l) not in posicoes_ocupadas and (c, l) not in AREA_BASE:
                if tentativas < 50 and muito_proximo(c, l, lista_inimigos, dist_min=1):
                    tentativas += 1;
                    continue
                lista_inimigos.append({"coluna": c, "linha": l})
                posicoes_ocupadas.add((c, l))
                break


# ==========================================
# SPRITES
# ==========================================
imagens = {
    "guerreiro": carregar_imagem('Sprite_Guerreiro.png', (55, 60)),
    "arqueiro": carregar_imagem('Sprite_Arqueiro.png', (55, 60)),
    "curandeiro": carregar_imagem('Sprite_Curandeiro.png', (55, 60)),
    "mago": carregar_imagem('Sprite_Mago.png', (55, 60)),
    "escudeiro": carregar_imagem('Sprite_Escudeiro.png', (55, 60))
}

imagens_pb = {}
for nome, img in imagens.items():
    img_pb = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    for px in range(img.get_width()):
        for py in range(img.get_height()):
            r, g, b, a = img.get_at((px, py))
            if a > 0:
                cinza = int(r * 0.299 + g * 0.587 + b * 0.114)
                img_pb.set_at((px, py), (cinza, cinza, cinza, a))
    imagens_pb[nome] = img_pb

retratos = {
    "guerreiro": carregar_imagem('Selecionado_Guerreiro.png', (230, 230)),
    "arqueiro": carregar_imagem('Selecionado_Arqueiro.png', (280, 280)),
    "curandeiro": carregar_imagem('Selecionado_Curandeiro.png', (210, 255)),
    "mago": carregar_imagem('Selecionado_Mago.png', (260, 290)),
    "escudeiro": carregar_imagem('Selecionado_Escudeiro.png', (240, 240))
}

posicoes_customizadas = {
    "guerreiro": {"retrato": (-5, 525), "texto": (70, 695)},
    "arqueiro": {"retrato": (-25, 520), "texto": (75, 690)},
    "curandeiro": {"retrato": (0, 515), "texto": (65, 700)},
    "mago": {"retrato": (-18, 510), "texto": (70, 695)},
    "escudeiro": {"retrato": (-8, 510), "texto": (72, 692)}
}


def criar_herois():
    return {
        "guerreiro": {"coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
                      "classe": "guerreiro", "bonus_ataque": 1 + BONUS_GUERREIRO,
                      "pergaminhos": 0, "curas_recebidas": 0, "protecoes_recebidas": 0,
                      "turnos_morto": 0, "ja_foi_revivido": False},
        "arqueiro": {"coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
                     "classe": "arqueiro", "bonus_ataque": 1.0,
                     "pergaminhos": 0, "curas_recebidas": 0, "protecoes_recebidas": 0,
                     "turnos_morto": 0, "ja_foi_revivido": False},
        "curandeiro": {"coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
                       "classe": "curandeiro", "bonus_ataque": 1.0,
                       "pergaminhos": 0, "curas_recebidas": 0, "protecoes_recebidas": 0,
                       "turnos_morto": 0, "ja_foi_revivido": False},
        "mago": {"coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
                 "classe": "mago", "bonus_ataque": 1.0,
                 "pergaminhos": 0, "curas_recebidas": 0, "protecoes_recebidas": 0,
                 "turnos_morto": 0, "ja_foi_revivido": False},
        "escudeiro": {"coluna": 0, "linha": 0, "vida": VIDA_HEROI, "vida_max": VIDA_HEROI,
                      "classe": "escudeiro", "bonus_ataque": 1.0,
                      "pergaminhos": 0, "protegendo": None,
                      "curas_recebidas": 0, "protecoes_recebidas": 0,
                      "turnos_morto": 0, "ja_foi_revivido": False}
    }


herois = criar_herois()
personagem_selecionado = "guerreiro"
estado_jogo = "CAPA"
pagina_tutorial = 1
mensagem_log = []
santuario_visitado = False
tempo_inicio_capa = pygame.time.get_ticks()
DURACAO_CAPA_MS = 5000
tempo_inicio_fim = 0
dragao_ja_acordou = False  # evita tocar som de despertar mais de uma vez


def adicionar_log(msg):
    global mensagem_log
    t = pygame.time.get_ticks()
    mensagem_log.append({"texto": msg, "tempo": t})
    if len(mensagem_log) > 4:
        mensagem_log.pop(0)


imagem_inimigo = carregar_imagem('Sprite_Inimigo.png', (40, 55))
inicializar_elementos_mapa()

mapa_obstaculos_inicial = copy.deepcopy(mapa_obstaculos)
mapa_itens_inicial = copy.deepcopy(mapa_itens)
lista_inimigos_inicial = copy.deepcopy(lista_inimigos)


def santuario_foi_visitado():
    return santuario_visitado


# ==========================================
# TEXTOS DO TUTORIAL
# ==========================================
TEXTO_TUTORIAL_1 = (
    "A Lenda de Eldoria\n\n"
    "Há séculos, o reino de Eldoria vive sob a sombra de um antigo Dragão adormecido.\n"
    "Para controlar a criatura, três fortalezas foram erguidas ao redor do seu covil, "
    "protegidas por inimigos sombrios e encantamentos ancestrais.\n\n"
    "Agora, um grupo de cinco heróis parte da antiga base do reino em uma última tentativa "
    "de salvar a terra. Cada membro possui habilidades únicas, e somente trabalhando juntos "
    "será possível destruir as fortalezas, alcançar o Santuário Sagrado e enfrentar o Dragão.\n\n"
    "Porém, a jornada é perigosa. Inimigos vagam pelo mundo, recursos são limitados e a queda "
    "de um companheiro pode significar a derrota."
)

TEXTO_TUTORIAL_3 = (
    "Objetivo da missão\n"
    "- Explore o mapa e derrote inimigos pelo caminho.\n"
    "- Colete poções (vida) e pergaminhos (+ataque).\n"
    "- Destrua as 3 fortalezas na ordem indicada.\n"
    "- Vá até o Santuário Sagrado (canto inferior direito).\n"
    "  SEM visitar o Santuário, não é possível atacar o Dragão!\n"
    "- Derrote o Dragão (centro do mapa) e salve Eldoria.\n\n"
    "Controles\n"
    "- 1 a 5: Selecionar heróis  |  Setas: Movimentação\n"
    "- Espaço: Atacar fortaleza atual ou Dragão\n"
    "- C: Curar aliado adjacente (Curandeira, máx. 25x por aliado)\n"
    "- V: Reviver herói caído adjacente (Curandeira)\n"
    "- P: Proteção da Escudeira (máx. 5x por aliado, cancela ao afastar)\n"
    "- R: Reiniciar a partida\n\n"
    "Dicas\n"
    "- Mantenha os heróis próximos entre si.\n"
    "- A Escudeira só protege aliados dentro de 1 bloco.\n"
    "  Se o aliado se afastar, a proteção é cancelada automaticamente!\n"
    "- A Curandeira é essencial: proteja-a, pois ela não pode ser revivida."
)


# ==========================================
# COMBATE
# ==========================================

def verificar_estado_jogo():
    global estado_jogo, tempo_inicio_fim
    if sum(1 for h in herois.values() if h["vida"] > 0) == 0:
        parar_toda_musica()
        tocar_som(som_derrota)
        estado_jogo = "DERROTA"
        tempo_inicio_fim = pygame.time.get_ticks()
        adicionar_log("DERROTA! Todos os heróis foram derrotados.")


def aplicar_dano_com_protecao(nome_heroi, dano_total):
    if herois[nome_heroi]["vida"] <= 0:
        return
    escudo = herois["escudeiro"]
    if escudo["vida"] > 0 and escudo.get("protegendo") == nome_heroi:
        metade = int(dano_total * REDUCAO_ESCUDEIRO)
        herois[nome_heroi]["vida"] = max(0, herois[nome_heroi]["vida"] - metade)
        escudo["vida"] = max(0, escudo["vida"] - metade)
        adicionar_log(f"Escudo! {NOMES_EXIBICAO[nome_heroi]} e Escudeira: -{metade} HP cada")
        if escudo["vida"] <= 0:
            escudo["turnos_morto"] = 5
            tocar_som(som_morte_jogador)
            adicionar_log("Escudeira caiu protegendo! (5 turnos p/ reviver)")
            escudo["protegendo"] = None
    else:
        herois[nome_heroi]["vida"] = max(0, herois[nome_heroi]["vida"] - dano_total)
        adicionar_log(f"{NOMES_EXIBICAO[nome_heroi]} recebe -{dano_total} HP")

    if herois[nome_heroi]["vida"] == 0 and herois[nome_heroi]["turnos_morto"] == 0:
        if nome_heroi == "curandeiro":
            herois[nome_heroi]["turnos_morto"] = -1
            tocar_som(som_morte_jogador)
            adicionar_log("Curandeira derrotada permanentemente!")
        elif herois[nome_heroi].get("ja_foi_revivido", False):
            herois[nome_heroi]["turnos_morto"] = -1
            tocar_som(som_morte_jogador)
            adicionar_log(f"{NOMES_EXIBICAO[nome_heroi]} caiu definitivamente!")
        else:
            herois[nome_heroi]["turnos_morto"] = 5
            tocar_som(som_morte_jogador)
            adicionar_log(f"{NOMES_EXIBICAO[nome_heroi]} caiu! (5 turnos p/ reviver)")


def verificar_protecao_escudeiro():
    escudo = herois["escudeiro"]
    alvo = escudo.get("protegendo")
    if alvo is None or escudo["vida"] <= 0:
        return
    if herois[alvo]["vida"] <= 0:
        escudo["protegendo"] = None
        return
    if (abs(escudo["coluna"] - herois[alvo]["coluna"]) > 1 or
            abs(escudo["linha"] - herois[alvo]["linha"]) > 1):
        escudo["protegendo"] = None
        adicionar_log(f"Proteção cancelada: {NOMES_EXIBICAO[alvo]} se afastou!")


def realizar_encontro_inimigo(nome_heroi, inimigo):
    lista_inimigos.remove(inimigo)
    tocar_som(som_ataque_inimigo_dragao)
    adicionar_log(f"{NOMES_EXIBICAO[nome_heroi]} derrotou inimigo! (-5 HP)")
    aplicar_dano_com_protecao(nome_heroi, 5)


def obter_herois_aptos_para_atacar(estrutura_pos):
    herois_aptos = []
    ex, ey = estrutura_pos
    for nome, dados in herois.items():
        if dados["vida"] > 0:
            dist = abs(dados["coluna"] - ex) + abs(dados["linha"] - ey)
            alcance = 3 if dados["classe"] == "mago" else 1
            if dist <= alcance:
                herois_aptos.append(nome)
    return herois_aptos


def calcular_dano_fortaleza(nome_heroi):
    dados = herois[nome_heroi]
    dano = 15
    if dados["classe"] == "guerreiro":
        dano = int(dano * (1 + BONUS_GUERREIRO))
    dano = int(dano * (1 + dados["pergaminhos"] * BONUS_PERGAMINHO))
    critico = False
    if dados["classe"] == "arqueiro" and random.randint(1, 100) <= CHANCE_CRITICO_ARQUEIRO:
        dano *= 2;
        critico = True
    return dano, critico


def calcular_dano_dragao(nome_heroi):
    dados = herois[nome_heroi]
    dano = 20
    if dados["classe"] == "guerreiro":
        dano = int(dano * (1 + BONUS_GUERREIRO))
    dano = int(dano * (1 + dados["pergaminhos"] * BONUS_PERGAMINHO))
    critico = False
    if dados["classe"] == "arqueiro" and random.randint(1, 100) <= CHANCE_CRITICO_ARQUEIRO:
        dano *= 2;
        critico = True
    return dano, critico


def realizar_ataque_fortaleza():
    global fortaleza_atual_index, dragao_ja_acordou
    if fortaleza_atual_index >= len(ordem_fortalezas):
        return
    nome_f = ordem_fortalezas[fortaleza_atual_index]
    pos_f = next((pos for pos, tipo in mapa_estruturas.items() if tipo == nome_f), None)
    if not pos_f:
        return
    aptos = obter_herois_aptos_para_atacar(pos_f)
    if len(aptos) < 2:
        adicionar_log(f"Precisa de 2+ heróis perto da {nome_f}!");
        return
    if personagem_selecionado not in aptos:
        adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} fora do alcance!");
        return

    if random.randint(0, 100) >= 30:
        dano, critico = calcular_dano_fortaleza(personagem_selecionado)
        vida_estruturas[nome_f] -= dano
        if critico:
            tocar_som(som_arqueiro_critico)  # som especial de crítico
            adicionar_log(f"CRÍTICO! {NOMES_EXIBICAO[personagem_selecionado]} causa {dano} HP a {nome_f}!")
        else:
            tocar_som(som_ataque_fortaleza)
            adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} causa {dano} HP a {nome_f}!")
    else:
        tocar_som(som_personagem_erra)
        adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} errou o ataque!")

    adicionar_log(f"{nome_f.capitalize()} contra-ataca: -8 HP")
    aplicar_dano_com_protecao(personagem_selecionado, 8)

    if vida_estruturas[nome_f] <= 0:
        fortaleza_atual_index += 1
        del mapa_estruturas[pos_f]

        if fortaleza_atual_index >= len(ordem_fortalezas):
            # Terceira fortaleza — som especial "todas destruídas"
            tocar_som(som_fortalezas_derrubadas)
            adicionar_log(f"{nome_f.capitalize()} destruída! Todas as fortalezas caíram!")
            if not dragao_ja_acordou:
                dragao_ja_acordou = True
                tocar_som(som_dragao_acordado)
                adicionar_log("O Dragão despertou! Vá ao Santuário!")
        else:
            # Primeira ou segunda fortaleza
            tocar_som(som_fortaleza_caiu)
            adicionar_log(f"{nome_f.capitalize()} destruída!")
    verificar_estado_jogo()


def realizar_ataque_dragao():
    global estado_jogo, tempo_inicio_fim
    if not santuario_foi_visitado():
        adicionar_log("Vá ao Santuário primeiro!");
        return
    pos_dragao = next((pos for pos, tipo in mapa_estruturas.items() if tipo == "dragao"), None)
    if not pos_dragao:
        return
    aptos = obter_herois_aptos_para_atacar(pos_dragao)
    if personagem_selecionado not in aptos:
        adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} fora do alcance do Dragão!");
        return

    if random.randint(0, 100) >= 30:
        dano, critico = calcular_dano_dragao(personagem_selecionado)
        vida_estruturas["dragao"] = max(0, vida_estruturas["dragao"] - dano)
        if critico:
            tocar_som(som_arqueiro_critico)
            adicionar_log(f"CRÍTICO! {NOMES_EXIBICAO[personagem_selecionado]} causa {dano} HP ao Dragão!")
        else:
            tocar_som(som_ataque_inimigo_dragao)
            adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} causa {dano} HP ao Dragão!")
        adicionar_log(f"Dragão: {vida_estruturas['dragao']}/{VIDA_DRAGAO} HP restante")
    else:
        tocar_som(som_personagem_erra)
        adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} errou o Dragão!")

    if vida_estruturas["dragao"] <= 0:
        tocar_musica_final()  # para tudo e toca musica_final.mp3
        tocar_som(som_vitoria)
        adicionar_log("DRAGÃO DERROTADO! VITÓRIA!")
        estado_jogo = "VITORIA"
        tempo_inicio_fim = pygame.time.get_ticks()
        return

    adicionar_log(f"Dragão contra-ataca: -{DANO_DRAGAO_FIXO} HP!")
    aplicar_dano_com_protecao(personagem_selecionado, DANO_DRAGAO_FIXO)
    verificar_estado_jogo()


def usar_habilidade_curandeiro(alvo):
    if herois["curandeiro"]["vida"] <= 0:
        adicionar_log("Curandeira está derrotada!");
        return
    if alvo == "curandeiro":
        adicionar_log("A Curandeira não pode curar a si mesma!");
        return
    if alvo not in herois or herois[alvo]["vida"] <= 0:
        adicionar_log(f"{NOMES_EXIBICAO[alvo]} está morto! (Use V para reviver)");
        return
    cur_c, cur_l = herois["curandeiro"]["coluna"], herois["curandeiro"]["linha"]
    alvo_c, alvo_l = herois[alvo]["coluna"], herois[alvo]["linha"]
    if abs(cur_c - alvo_c) > 1 or abs(cur_l - alvo_l) > 1:
        adicionar_log(f"{NOMES_EXIBICAO[alvo]} fora do alcance da cura!");
        return
    if herois[alvo]["curas_recebidas"] >= MAX_CURAS_POR_ALVO:
        adicionar_log(f"Limite de curas atingido para {NOMES_EXIBICAO[alvo]}!");
        return
    herois[alvo]["vida"] = min(herois[alvo]["vida"] + CURA_CURANDEIRO, herois[alvo]["vida_max"])
    herois[alvo]["curas_recebidas"] += 1
    restantes = MAX_CURAS_POR_ALVO - herois[alvo]["curas_recebidas"]
    tocar_som(som_cura)
    adicionar_log(f"Curandeira cura {NOMES_EXIBICAO[alvo]}! +{CURA_CURANDEIRO} HP ({restantes} restantes)")


def activar_protecao_escudeiro(alvo):
    if herois["escudeiro"]["vida"] <= 0:
        adicionar_log("Escudeira está derrotada!");
        return
    if alvo == "escudeiro":
        adicionar_log("A Escudeira não pode proteger a si mesma!");
        return
    if herois[alvo]["vida"] <= 0:
        adicionar_log(f"{NOMES_EXIBICAO[alvo]} está morto!");
        return
    if herois["escudeiro"]["protegendo"] == alvo:
        herois["escudeiro"]["protegendo"] = None
        adicionar_log(f"Escudeira desfez a proteção de {NOMES_EXIBICAO[alvo]}!");
        return
    if herois["escudeiro"]["protegendo"] is not None:
        outro = herois["escudeiro"]["protegendo"]
        adicionar_log(f"Desfaça a proteção de {NOMES_EXIBICAO[outro]} primeiro!");
        return
    esc_c, esc_l = herois["escudeiro"]["coluna"], herois["escudeiro"]["linha"]
    alvo_c, alvo_l = herois[alvo]["coluna"], herois[alvo]["linha"]
    if abs(esc_c - alvo_c) > 1 or abs(esc_l - alvo_l) > 1:
        adicionar_log("Alvo muito longe! Fique a 1 bloco da Escudeira.");
        return
    if herois[alvo]["protecoes_recebidas"] >= MAX_PROTECOES_POR_ALVO:
        adicionar_log(f"Limite de proteções para {NOMES_EXIBICAO[alvo]}!");
        return
    herois["escudeiro"]["protegendo"] = alvo
    herois[alvo]["protecoes_recebidas"] += 1
    restantes = MAX_PROTECOES_POR_ALVO - herois[alvo]["protecoes_recebidas"]
    tocar_som(som_escudeiro_protege)
    adicionar_log(f"Escudeira protege {NOMES_EXIBICAO[alvo]}! ({restantes} proteções restantes)")


# ==========================================
# IA DO DRAGÃO
# ==========================================
_dragao_turnos_aleatorios = 0


def movimentar_dragao(turno_foi_ataque_manual=False):
    global _dragao_turnos_aleatorios
    if fortaleza_atual_index < len(ordem_fortalezas) or estado_jogo != "EXPLORACAO":
        return
    pos_dragao = next((pos for pos, t in mapa_estruturas.items() if t == "dragao"), None)
    if not pos_dragao:
        return

    heroi_alvo, menor_dist = None, 999
    for dados in herois.values():
        if dados["vida"] > 0:
            dist = abs(dados["coluna"] - pos_dragao[0]) + abs(dados["linha"] - pos_dragao[1])
            if dist < menor_dist:
                menor_dist, heroi_alvo = dist, dados
    if not heroi_alvo:
        return

    destino = (heroi_alvo["coluna"], heroi_alvo["linha"])

    if menor_dist == 1:
        if not turno_foi_ataque_manual:
            nome_alvo = heroi_alvo["classe"]
            adicionar_log(f"Dragão ataca {NOMES_EXIBICAO[nome_alvo]}! -{DANO_DRAGAO_FIXO} HP")
            aplicar_dano_com_protecao(nome_alvo, DANO_DRAGAO_FIXO)
            verificar_estado_jogo()
            _dragao_turnos_aleatorios = random.randint(2, 4)
        return

    bloqueados = set(mapa_obstaculos.keys())
    for pos, tipo in mapa_estruturas.items():
        if tipo != "dragao":
            bloqueados.add(pos)
    for dados in herois.values():
        pos_h = (dados["coluna"], dados["linha"])
        if (dados["vida"] > 0 or dados.get("turnos_morto", 0) > 0) and pos_h != destino:
            bloqueados.add(pos_h)

    vizinhos_livres = [
        (c, l) for c, l in [
            (pos_dragao[0] + 1, pos_dragao[1]),
            (pos_dragao[0] - 1, pos_dragao[1]),
            (pos_dragao[0], pos_dragao[1] + 1),
            (pos_dragao[0], pos_dragao[1] - 1),
        ]
        if 0 <= c <= 11 and 0 <= l <= 11 and (c, l) not in bloqueados
    ]
    if not vizinhos_livres:
        return

    if _dragao_turnos_aleatorios > 0:
        proximo = random.choice(vizinhos_livres)
        _dragao_turnos_aleatorios -= 1
    else:
        proximo = bfs_proximo_passo(pos_dragao, destino, bloqueados)
        if proximo is None:
            proximo = min(vizinhos_livres,
                          key=lambda p: abs(p[0] - destino[0]) + abs(p[1] - destino[1]))
        if random.random() < 0.30:
            _dragao_turnos_aleatorios = random.randint(1, 3)

    del mapa_estruturas[pos_dragao]
    mapa_estruturas[proximo] = "dragao"
    # Inicia loop de som do dragão (não reinicia se já tocando)
    # e baixa a música principal ao mínimo
    iniciar_loop_dragao()
    pygame.mixer.music.set_volume(0.06)


def reiniciar_jogo():
    global herois, personagem_selecionado, estado_jogo
    global fortaleza_atual_index, vida_estruturas, turnos_jogados
    global mapa_estruturas, mapa_obstaculos, mapa_itens, lista_inimigos
    global _dragao_turnos_aleatorios, santuario_visitado, dragao_ja_acordou
    herois = criar_herois()
    mapa_estruturas = {(6, 6): "dragao", (2, 5): "fortaleza1", (5, 10): "fortaleza2",
                       (8, 3): "fortaleza3", (11, 11): "santuario"}
    vida_estruturas = {"fortaleza1": VIDA_FORTALEZA, "fortaleza2": VIDA_FORTALEZA,
                       "fortaleza3": VIDA_FORTALEZA, "dragao": VIDA_DRAGAO}
    fortaleza_atual_index = 0
    turnos_jogados = 0
    _dragao_turnos_aleatorios = 0
    personagem_selecionado = "guerreiro"
    estado_jogo = "EXPLORACAO"
    santuario_visitado = False
    dragao_ja_acordou = False
    mensagem_log.clear()
    mapa_obstaculos = copy.deepcopy(mapa_obstaculos_inicial)
    mapa_itens = copy.deepcopy(mapa_itens_inicial)
    lista_inimigos = copy.deepcopy(lista_inimigos_inicial)
    # Para todos os áudios e reinicia música principal no volume correto
    parar_toda_musica()
    try:
        pygame.mixer.music.load("musica_fundo.mp3")
        pygame.mixer.music.set_volume(0.30)
        pygame.mixer.music.play(-1)
    except Exception:
        pass
    adicionar_log("Jogo reiniciado!")


# ==========================================
# TELAS ESPECIAIS
# ==========================================

def desenhar_tela_capa(tela, pos_mouse_virtual, clicou):
    global estado_jogo, pagina_tutorial
    try:
        img_capa = pygame.transform.scale(
            pygame.image.load("Capa_Eldoria.jpeg").convert(),
            (LARGURA_ORIGINAL, ALTURA_ORIGINAL))
        tela.blit(img_capa, (0, 0))
    except pygame.error:
        tela.fill((20, 10, 30))
        desenhar_texto_com_contorno(tela, "ELDORIA", fonte_grande, (220, 180, 80), C_BORDA_TEXTO,
                                    LARGURA_ORIGINAL // 2 - 100, ALTURA_ORIGINAL // 2 - 50)
    overlay = pygame.Surface((LARGURA_ORIGINAL, ALTURA_ORIGINAL), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 80))
    tela.blit(overlay, (0, 0))
    tempo_atual = pygame.time.get_ticks()
    elapsed = tempo_atual - tempo_inicio_capa
    progresso = min(elapsed / DURACAO_CAPA_MS, 1.0)
    bw, bh = 300, 6
    bx = LARGURA_ORIGINAL // 2 - bw // 2
    by = ALTURA_ORIGINAL - 60
    pygame.draw.rect(tela, (80, 60, 40), (bx, by, bw, bh), border_radius=3)
    pygame.draw.rect(tela, (220, 180, 80), (bx, by, int(bw * progresso), bh), border_radius=3)
    pulso = int(180 + 75 * math.sin(tempo_atual / 400))
    cor_msg = (pulso, pulso, int(pulso * 0.7))
    msg = "Clique para continuar"
    wm = fonte_pequena.render(msg, True, cor_msg).get_width()
    desenhar_texto_com_contorno(tela, msg, fonte_pequena, cor_msg, (0, 0, 0),
                                LARGURA_ORIGINAL // 2 - wm // 2, ALTURA_ORIGINAL - 40)
    if elapsed >= DURACAO_CAPA_MS or clicou:
        estado_jogo = "TELA_INICIAL";
        pagina_tutorial = 1


def desenhar_tela_vitoria(tela, pos_mouse_virtual, clicou):
    tempo_atual = pygame.time.get_ticks()
    elapsed = (tempo_atual - tempo_inicio_fim) / 1000.0
    cx, cy = LARGURA_ORIGINAL // 2, ALTURA_ORIGINAL // 2
    for y in range(ALTURA_ORIGINAL):
        r = y / ALTURA_ORIGINAL
        pygame.draw.line(tela, (int(40 + r * 80), int(20 + r * 40), 0), (0, y), (LARGURA_ORIGINAL, y))
    for i in range(24):
        ang = (i / 24) * 2 * math.pi + elapsed * 0.5
        rad = 320 + 20 * math.sin(elapsed * 2 + i)
        px = int(cx + math.cos(ang) * rad)
        py = int(cy + math.sin(ang) * rad * 0.45)
        tam = max(2, int(4 + 2 * math.sin(elapsed * 3 + i)))
        pygame.draw.circle(tela, (220, int(180 + 40 * math.sin(elapsed + i)),
                                  int(50 + 50 * math.cos(elapsed * 2 + i))), (px, py), tam)
    pw, ph = 720, 520
    px2 = cx - pw // 2;
    py2 = cy - ph // 2
    painel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    painel.fill((0, 0, 0, 160))
    tela.blit(painel, (px2, py2))
    pygame.draw.rect(tela, (200, 160, 40), (px2, py2, pw, ph), 3, border_radius=12)
    escala = 1.0 + 0.05 * math.sin(elapsed * 3)
    txt_v = fonte_grande.render("VITÓRIA!", True, (255, 220, 50))
    txt_e = pygame.transform.scale(txt_v, (int(txt_v.get_width() * escala), int(txt_v.get_height() * escala)))
    tela.blit(txt_e, (cx - txt_e.get_width() // 2, py2 + 20))
    sub = "O Dragão foi derrotado! Eldoria está salva!"
    ws = fonte.render(sub, True, (255, 255, 200)).get_width()
    desenhar_texto_com_contorno(tela, sub, fonte, (255, 255, 200), (80, 40, 0), cx - ws // 2, py2 + 100)
    herois_vivos = sum(1 for h in herois.values() if h["vida"] > 0)
    stats = [f"Turnos jogados: {turnos_jogados}",
             f"Heróis sobreviventes: {herois_vivos} / 5",
             "Fortalezas destruídas: 3 / 3"]
    ys = py2 + 148
    for s in stats:
        wss = fonte_tutorial.render(s, True, (220, 200, 150)).get_width()
        desenhar_texto_com_contorno(tela, s, fonte_tutorial, (220, 200, 150), (60, 30, 0), cx - wss // 2, ys)
        ys += 38
    yh = ys + 10
    for nome, dados in herois.items():
        cor_n = (100, 255, 100) if dados["vida"] > 0 else (150, 150, 150)
        tela.blit(fonte_pequena.render(NOMES_EXIBICAO[nome], True, cor_n), (cx - 260, yh))
        desenhar_barra_hp(tela, cx - 120, yh + 2, 200, 12, max(0, dados["vida"]), dados["vida_max"])
        tela.blit(fonte_pequena.render(f"{max(0, dados['vida'])}/{dados['vida_max']}", True, cor_n), (cx + 90, yh))
        yh += 30
    btn = desenhar_botao(tela, "Jogar Novamente", cx - 140, py2 + ph - 70, 280, 52,
                         (120, 90, 20), (200, 160, 40), pos_mouse_virtual)
    if clicou and btn.collidepoint(pos_mouse_virtual):
        reiniciar_jogo()


def desenhar_tela_derrota(tela, pos_mouse_virtual, clicou):
    tempo_atual = pygame.time.get_ticks()
    elapsed = (tempo_atual - tempo_inicio_fim) / 1000.0
    cx, cy = LARGURA_ORIGINAL // 2, ALTURA_ORIGINAL // 2
    for y in range(ALTURA_ORIGINAL):
        r = y / ALTURA_ORIGINAL
        pygame.draw.line(tela, (int(60 + r * 40), int(5 + r * 10), int(5 + r * 5)), (0, y), (LARGURA_ORIGINAL, y))
    rng = random.Random(int(elapsed * 3))
    for _ in range(40):
        px = rng.randint(0, LARGURA_ORIGINAL)
        py = (rng.randint(0, ALTURA_ORIGINAL) + int(elapsed * 60)) % ALTURA_ORIGINAL
        tam = rng.randint(1, 4)
        pygame.draw.circle(tela, (200 + rng.randint(0, 55), rng.randint(30, 100), 0), (px, py), tam)
    pw, ph = 720, 500
    px2 = cx - pw // 2;
    py2 = cy - ph // 2
    painel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    painel.fill((0, 0, 0, 170))
    tela.blit(painel, (px2, py2))
    pygame.draw.rect(tela, (150, 30, 30), (px2, py2, pw, ph), 3, border_radius=12)
    tx = random.randint(-2, 2);
    ty = random.randint(-1, 1)
    txt_d = fonte_grande.render("DERROTA", True, (220, 50, 50))
    tela.blit(txt_d, (cx - txt_d.get_width() // 2 + tx, py2 + 20 + ty))
    sub = "Todos os heróis caíram..."
    ws = fonte.render(sub, True, (220, 150, 150)).get_width()
    desenhar_texto_com_contorno(tela, sub, fonte, (220, 150, 150), (80, 10, 10), cx - ws // 2, py2 + 105)
    stats = [f"Turnos sobrevividos: {turnos_jogados}",
             f"Fortalezas destruídas: {min(fortaleza_atual_index, 3)} / 3",
             f"Inimigos restantes: {len(lista_inimigos)}"]
    ys = py2 + 150
    for s in stats:
        wss = fonte_tutorial.render(s, True, (200, 150, 150)).get_width()
        desenhar_texto_com_contorno(tela, s, fonte_tutorial, (200, 150, 150), (60, 10, 10), cx - wss // 2, ys)
        ys += 38
    yh = ys + 10
    for nome in herois:
        tn = fonte_pequena.render(f"{NOMES_EXIBICAO[nome]} — Caído", True, (200, 80, 80))
        tela.blit(tn, (cx - tn.get_width() // 2, yh))
        yh += 28
    btn = desenhar_botao(tela, "Tentar Novamente", cx - 150, py2 + ph - 70, 300, 52,
                         (100, 20, 20), (180, 40, 40), pos_mouse_virtual)
    if clicou and btn.collidepoint(pos_mouse_virtual):
        reiniciar_jogo()


# ==========================================
# LOOP PRINCIPAL
# ==========================================
async def main():
    global janela, estado_jogo, pagina_tutorial, personagem_selecionado
    global santuario_visitado, turnos_jogados, mensagem_log

    loop = True
    clock = pygame.time.Clock()

    while loop:
        passou_turno = False
        turno_foi_ataque = False
        clicou = False
        tamanho_atual = janela.get_size()
        scale_x = LARGURA_ORIGINAL / tamanho_atual[0]
        scale_y = ALTURA_ORIGINAL / tamanho_atual[1]
        mx, my = pygame.mouse.get_pos()
        pos_mouse_virtual = (int(mx * scale_x), int(my * scale_y))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False
            elif event.type == pygame.VIDEORESIZE:
                janela = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicou = True
            elif event.type == pygame.KEYDOWN:
                if estado_jogo == "CAPA":
                    estado_jogo = "TELA_INICIAL";
                    pagina_tutorial = 1;
                    continue
                if estado_jogo == "TELA_INICIAL":
                    continue
                if event.key == pygame.K_r:
                    reiniciar_jogo();
                    continue
                if estado_jogo in ["VITORIA", "DERROTA"]:
                    continue

                teclas_pc = {pygame.K_1: "guerreiro", pygame.K_2: "arqueiro",
                             pygame.K_3: "curandeiro", pygame.K_4: "mago", pygame.K_5: "escudeiro"}
                if event.key in teclas_pc:
                    novo = teclas_pc[event.key]
                    if herois[novo]["vida"] <= 0:
                        adicionar_log(f"{NOMES_EXIBICAO[novo]} está incapacitado!")
                    else:
                        personagem_selecionado = novo

                elif event.key == pygame.K_SPACE:
                    if herois[personagem_selecionado]["vida"] > 0:
                        if fortaleza_atual_index < len(ordem_fortalezas):
                            realizar_ataque_fortaleza()
                        else:
                            realizar_ataque_dragao()
                        passou_turno = True
                        turno_foi_ataque = True

                elif event.key == pygame.K_c:
                    usar_habilidade_curandeiro(personagem_selecionado)
                    passou_turno = True

                elif event.key == pygame.K_p:
                    activar_protecao_escudeiro(personagem_selecionado)
                    passou_turno = True

                elif event.key == pygame.K_v:
                    if personagem_selecionado == "curandeiro" and herois["curandeiro"]["vida"] > 0:
                        c_cur, l_cur = herois["curandeiro"]["coluna"], herois["curandeiro"]["linha"]
                        reviveu = False
                        for nome, dados in herois.items():
                            if (dados["vida"] <= 0
                                    and dados.get("turnos_morto", 0) > 0
                                    and dados.get("turnos_morto", 0) != -1):
                                dist = abs(dados["coluna"] - c_cur) + abs(dados["linha"] - l_cur)
                                if dist <= 1:
                                    dados["vida"] = dados["vida_max"] // 2
                                    dados["turnos_morto"] = 0
                                    dados["ja_foi_revivido"] = True
                                    tocar_som(som_reviver)
                                    adicionar_log(f"Curandeira reviveu {NOMES_EXIBICAO[nome]} com {dados['vida']} HP!")
                                    reviveu = True
                        if reviveu:
                            passou_turno = True
                        else:
                            adicionar_log("Nenhum aliado morto próximo para reviver.")
                    else:
                        adicionar_log("Apenas a Curandeira pode reviver aliados!")

                elif event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    if herois[personagem_selecionado]["vida"] <= 0:
                        adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} está incapacitado!");
                        continue
                    col_f = herois[personagem_selecionado]["coluna"]
                    lin_f = herois[personagem_selecionado]["linha"]
                    if event.key == pygame.K_UP and lin_f > 0:
                        lin_f -= 1
                    elif event.key == pygame.K_DOWN and lin_f < 11:
                        lin_f += 1
                    elif event.key == pygame.K_LEFT and col_f > 0:
                        col_f -= 1
                    elif event.key == pygame.K_RIGHT and col_f < 11:
                        col_f += 1

                    if mapa_estruturas.get((col_f, lin_f)) == "santuario":
                        if fortaleza_atual_index >= len(ordem_fortalezas):
                            santuario_visitado = True
                            herois[personagem_selecionado]["coluna"] = col_f
                            herois[personagem_selecionado]["linha"] = lin_f
                            tocar_som(som_chegou_santuario)
                            iniciar_musica_batalha_final()  # batalha final assume a cena
                            adicionar_log("Santuário alcançado! Agora ataque o Dragão!")
                            passou_turno = True
                        else:
                            adicionar_log("Destrua as fortalezas antes!")
                        continue

                    bateu = ((col_f, lin_f) in mapa_obstaculos or (col_f, lin_f) in mapa_estruturas)
                    if not bateu:
                        for nome_h, dados_h in herois.items():
                            if (nome_h != personagem_selecionado
                                    and dados_h["coluna"] == col_f and dados_h["linha"] == lin_f
                                    and not (col_f == 0 and lin_f == 0)):
                                if dados_h["vida"] > 0 or dados_h.get("turnos_morto", 0) > 0:
                                    bateu = True;
                                    break

                    inimigo = next((i for i in lista_inimigos
                                    if i["coluna"] == col_f and i["linha"] == lin_f), None)
                    if inimigo:
                        realizar_encontro_inimigo(personagem_selecionado, inimigo)
                        herois[personagem_selecionado]["coluna"] = col_f
                        herois[personagem_selecionado]["linha"] = lin_f
                        verificar_estado_jogo()
                        passou_turno = True
                    elif not bateu:
                        herois[personagem_selecionado]["coluna"] = col_f
                        herois[personagem_selecionado]["linha"] = lin_f
                        pos_atual = (col_f, lin_f)
                        if pos_atual in mapa_itens:
                            item = mapa_itens[pos_atual]
                            heroi = herois[personagem_selecionado]
                            if item == "pocao":
                                if heroi["vida"] >= heroi["vida_max"]:
                                    adicionar_log(f"{NOMES_EXIBICAO[personagem_selecionado]} já está com vida cheia!")
                                else:
                                    tocar_som(som_encontro_pocao)
                                    heroi["vida"] = min(heroi["vida"] + CURA_POCAO, heroi["vida_max"])
                                    adicionar_log(
                                        f"+{CURA_POCAO} HP! {NOMES_EXIBICAO[personagem_selecionado]} usou poção.")
                                    del mapa_itens[pos_atual]
                            elif item == "pergaminho":
                                tocar_som(som_encontro_pergaminho)
                                tocar_som(som_encontro_pergaminho)
                                heroi["pergaminhos"] += 1
                                adicionar_log(
                                    f"+{int(BONUS_PERGAMINHO * 100)}% atq! {NOMES_EXIBICAO[personagem_selecionado]} pegou pergaminho.")
                                del mapa_itens[pos_atual]
                        passou_turno = True

        # --- PÓS-TURNO ---
        if passou_turno:
            turnos_jogados += 1
            verificar_protecao_escudeiro()
            for nome, dados in herois.items():
                if dados["vida"] <= 0 and dados.get("turnos_morto", 0) > 0:
                    dados["turnos_morto"] -= 1
                    if dados["turnos_morto"] == 0:
                        adicionar_log(f"O corpo de {NOMES_EXIBICAO[nome]} desapareceu...")
            movimentar_dragao(turno_foi_ataque)
            if herois[personagem_selecionado]["vida"] <= 0:
                for nome, dados in herois.items():
                    if dados["vida"] > 0:
                        personagem_selecionado = nome
                        adicionar_log(f"Seleção trocada para {NOMES_EXIBICAO[nome]}.")
                        break

        # ==========================================
        # RENDERIZAÇÃO
        # ==========================================
        tela_virtual.fill(C_BG)

        if estado_jogo == "CAPA":
            desenhar_tela_capa(tela_virtual, pos_mouse_virtual, clicou)

        elif estado_jogo == "TELA_INICIAL":
            # --- Painel com sombra ---
            desenhar_painel(tela_virtual, 50, 50,
                            LARGURA_ORIGINAL - 100, ALTURA_ORIGINAL - 100,
                            C_SIDEBAR_BG, C_BORDA_TEXTO, raio=16, sombra_offset=5)

            # Decoração: bordas internas sombreadas (vinheta)
            vinheta = pygame.Surface((LARGURA_ORIGINAL - 100, ALTURA_ORIGINAL - 100), pygame.SRCALPHA)
            for espessura, alpha in [(18, 30), (10, 20), (5, 10)]:
                pygame.draw.rect(vinheta, (0, 0, 0, alpha), (0, 0, LARGURA_ORIGINAL - 100, ALTURA_ORIGINAL - 100),
                                 espessura, border_radius=14)
            tela_virtual.blit(vinheta, (50, 50))

            # Linha ornamentada abaixo do número de página
            desenhar_texto_com_contorno(tela_virtual, f"Página {pagina_tutorial} / 3",
                                        fonte_pequena, (180, 140, 80), C_BORDA_TEXTO, 80, 68)
            desenhar_divisor_ornamentado(tela_virtual, 80, 92, LARGURA_ORIGINAL - 160, C_BORDA_TEXTO)

            if pagina_tutorial == 1:
                desenhar_texto_multilinha(tela_virtual, TEXTO_TUTORIAL_1, fonte_tutorial,
                                          C_TEXTO, C_BORDA_TEXTO, 80, 108, LARGURA_ORIGINAL - 160)
                # Sprites decorativos centralizados
                tela_virtual.blit(visuais_objetos["fortaleza1"], (270, 408))
                tela_virtual.blit(visuais_objetos["dragao_acordado"], (430, 438))
                tela_virtual.blit(visuais_objetos["fortaleza2"], (340, 525))
                tela_virtual.blit(visuais_objetos["fortaleza3"], (590, 462))
                btn = desenhar_botao(tela_virtual, "Continuar",
                                     LARGURA_ORIGINAL // 2 - 110, ALTURA_ORIGINAL - 118,
                                     220, 52, C_CELL_BASE, (180, 230, 120), pos_mouse_virtual)
                if clicou and btn.collidepoint(pos_mouse_virtual):
                    pagina_tutorial = 2

            elif pagina_tutorial == 2:
                herois_info = [
                    ("guerreiro",
                     "Guerreiro:\nPossui maior força física. Causa mais dano contra fortalezas e o Dragão."),
                    ("arqueiro", "Arqueiro:\nAtaca com precisão. Possui chance de causar dano crítico (dobrado)."),
                    ("curandeiro", "Curandeira:\nRecupera vida dos aliados (C, máx. 25x/aliado) e revive mortos (V)."),
                    ("mago", "Mago:\nPode atacar fortalezas e o Dragão a uma distância maior (alcance 3)."),
                    ("escudeiro", "Escudeira:\nProtege aliados adjacentes (máx. 5x/aliado). Cancela se afastar (P).")
                ]
                y_off = 108
                for img_key, txt in herois_info:
                    tela_virtual.blit(imagens[img_key], (80, y_off))
                    desenhar_texto_multilinha(tela_virtual, txt, fonte_tutorial,
                                              C_TEXTO, C_BORDA_TEXTO, 150, y_off + 5, LARGURA_ORIGINAL - 230)
                    y_off += 105
                btn = desenhar_botao(tela_virtual, "Continuar",
                                     LARGURA_ORIGINAL // 2 - 110, ALTURA_ORIGINAL - 118,
                                     220, 52, C_CELL_BASE, (180, 230, 120), pos_mouse_virtual)
                if clicou and btn.collidepoint(pos_mouse_virtual):
                    pagina_tutorial = 3

            elif pagina_tutorial == 3:
                # Bloco de texto à esquerda
                desenhar_texto_multilinha(tela_virtual, TEXTO_TUTORIAL_3, fonte_tutorial,
                                          C_TEXTO, C_BORDA_TEXTO, 80, 108, LARGURA_ORIGINAL - 160)
                btn = desenhar_botao(tela_virtual, "Iniciar Jogo",
                                     LARGURA_ORIGINAL // 2 - 120, ALTURA_ORIGINAL - 118,
                                     240, 52, (180, 80, 80), (230, 130, 130), pos_mouse_virtual)
                if clicou and btn.collidepoint(pos_mouse_virtual):
                    estado_jogo = "EXPLORACAO"

        elif estado_jogo == "VITORIA":
            desenhar_tela_vitoria(tela_virtual, pos_mouse_virtual, clicou)

        elif estado_jogo == "DERROTA":
            desenhar_tela_derrota(tela_virtual, pos_mouse_virtual, clicou)

        else:
            # ==========================================
            # JOGO EM ANDAMENTO
            # ==========================================
            for lin in range(12):
                for col in range(12):
                    x, y = col * LARGURA_CELULA, lin * ALTURA_CELULA
                    tipo = mapa_estruturas.get((col, lin))
                    if tipo == "dragao":
                        cor = (140, 140, 140)
                    elif (col + lin) % 2 == 0:
                        cor = C_CELL_BASE  # tom normal
                    else:
                        cor = (108, 172, 84)  # tom levemente mais escuro (tabuleiro)
                    pygame.draw.rect(tela_virtual, cor, (x, y, LARGURA_CELULA, ALTURA_CELULA))
                    pygame.draw.rect(tela_virtual, C_GRID, (x, y, LARGURA_CELULA, ALTURA_CELULA), 1)

            img_base = visuais_objetos["base"]
            wb, hb = img_base.get_size()
            tela_virtual.blit(img_base, ((LARGURA_CELULA - wb) // 2, (ALTURA_CELULA - hb) // 2))

            dados_sel = herois[personagem_selecionado]
            if dados_sel["vida"] > 0:
                c_h, l_h = dados_sel["coluna"], dados_sel["linha"]
                # Destaque suave nas células adjacentes (movimentos possíveis)
                for dc, dl in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    ca, la = c_h + dc, l_h + dl
                    if 0 <= ca <= 11 and 0 <= la <= 11 and (ca, la) != (0, 0):
                        desenhar_destaque_transparente(tela_virtual,
                                                       ca * LARGURA_CELULA, la * ALTURA_CELULA, LARGURA_CELULA,
                                                       ALTURA_CELULA, C_HIGHLIGHT)
                # Borda dourada pulsante na célula do herói selecionado
                pulso_sel = int(180 + 75 * math.sin(pygame.time.get_ticks() / 300))
                cor_sel = (pulso_sel, pulso_sel, 0, 160)
                desenhar_destaque_transparente(tela_virtual,
                                               c_h * LARGURA_CELULA, l_h * ALTURA_CELULA,
                                               LARGURA_CELULA, ALTURA_CELULA, (pulso_sel, pulso_sel, 0, 55))
                pygame.draw.rect(tela_virtual, (pulso_sel, pulso_sel, 40),
                                 (c_h * LARGURA_CELULA, l_h * ALTURA_CELULA,
                                  LARGURA_CELULA, ALTURA_CELULA), 2)

            for (col, lin), tipo in mapa_estruturas.items():
                img = (visuais_objetos["dragao_acordado"]
                       if tipo == "dragao" and fortaleza_atual_index >= len(ordem_fortalezas)
                       else visuais_objetos[tipo])
                w, h = img.get_size()
                tela_virtual.blit(img, (col * LARGURA_CELULA + (LARGURA_CELULA - w) // 2,
                                        lin * ALTURA_CELULA + (ALTURA_CELULA - h) // 2))

            for (col, lin), tipo in mapa_obstaculos.items():
                img = visuais_objetos[tipo];
                w, h = img.get_size()
                tela_virtual.blit(img, (col * LARGURA_CELULA + (LARGURA_CELULA - w) // 2,
                                        lin * ALTURA_CELULA + (ALTURA_CELULA - h) // 2))

            for (col, lin), tipo in mapa_itens.items():
                img = visuais_objetos[tipo];
                w, h = img.get_size()
                tela_virtual.blit(img, (col * LARGURA_CELULA + (LARGURA_CELULA - w) // 2,
                                        lin * ALTURA_CELULA + (ALTURA_CELULA - h) // 2))

            for inimigo in lista_inimigos:
                w, h = imagem_inimigo.get_size()
                tela_virtual.blit(imagem_inimigo, (
                    inimigo["coluna"] * LARGURA_CELULA + (LARGURA_CELULA - w) // 2,
                    inimigo["linha"] * ALTURA_CELULA + (ALTURA_CELULA - h) // 2))

            for nome_h, dados in herois.items():
                if dados["vida"] > 0 or dados.get("turnos_morto", 0) > 0:
                    if dados["coluna"] == 0 and dados["linha"] == 0:
                        continue
                    img = imagens[nome_h] if dados["vida"] > 0 else imagens_pb[nome_h]
                    w, h = img.get_size()
                    x = dados["coluna"] * LARGURA_CELULA + (LARGURA_CELULA - w) // 2
                    y = dados["linha"] * ALTURA_CELULA + (ALTURA_CELULA - h) // 2
                    tela_virtual.blit(img, (x, y))
                    if dados["vida"] > 0:
                        hp_pct = dados["vida"] / dados["vida_max"]
                        cor_hp = (0, 255, 0) if hp_pct > 0.5 else (255, 255, 0) if hp_pct > 0.25 else (255, 0, 0)
                        pygame.draw.rect(tela_virtual, (30, 30, 30), (x + 4, y - 9, 42, 6))
                        pygame.draw.rect(tela_virtual, cor_hp, (x + 4, y - 9, int(42 * hp_pct), 6))
                        pygame.draw.rect(tela_virtual, (200, 200, 200), (x + 4, y - 9, 42, 6), 1)
                    else:
                        fn = pygame.font.Font(None, 18)
                        tn = fn.render(str(dados["turnos_morto"]), True, (255, 255, 255))
                        tela_virtual.blit(tn, (x + 20, y - 10))

            # ==========================================
            # BARRA LATERAL DIREITA
            # ==========================================
            x_sb = 12 * LARGURA_CELULA
            larg_sb = LARGURA_ORIGINAL - x_sb
            pygame.draw.rect(tela_virtual, C_SIDEBAR_BG, (x_sb, 0, larg_sb, ALTURA_ORIGINAL))
            pygame.draw.rect(tela_virtual, C_BORDA_TEXTO, (x_sb, 0, larg_sb, ALTURA_ORIGINAL), 3)

            # Vinheta lateral (sombra interna)
            vin_sb = pygame.Surface((larg_sb, ALTURA_ORIGINAL), pygame.SRCALPHA)
            for e, a in [(12, 20), (6, 12), (3, 6)]:
                pygame.draw.rect(vin_sb, (0, 0, 0, a), (0, 0, larg_sb, ALTURA_ORIGINAL), e)
            tela_virtual.blit(vin_sb, (x_sb, 0))

            SB_X = x_sb + 8
            SB_X2 = LARGURA_ORIGINAL - 6
            cx_sb = x_sb + larg_sb // 2

            # Título com leve pulso dourado na cor
            tempo_sb = pygame.time.get_ticks()
            pulso_cor = int(180 + 40 * math.sin(tempo_sb / 900))
            cor_titulo = (pulso_cor, int(pulso_cor * 0.7), 20)  # dourado pulsante
            desenhar_texto_com_contorno(tela_virtual, "Eldoria", fonte_titulo,
                                        cor_titulo, C_BORDA_TEXTO,
                                        cx_sb - fonte_titulo.render("Eldoria", True, cor_titulo).get_width() // 2, 12)

            wtr = fonte_pequena.render(f"Turno: {turnos_jogados}", True, C_TEXTO).get_width()
            desenhar_texto_com_contorno(tela_virtual, f"Turno: {turnos_jogados}", fonte_pequena,
                                        C_TEXTO, C_BORDA_TEXTO, cx_sb - wtr // 2, 55)

            desenhar_divisor_ornamentado(tela_virtual, SB_X, 72, larg_sb - 16, C_BORDA_TEXTO)

            # ── Fortalezas ───────────────────────────────────────────────────
            # "HP:" sempre preto; só o valor (ex. 150/150) muda de cor
            def _render_hp_bicolor(surf, prefixo, valor, fonte_u, cor_val, x, y):
                """Desenha "HP: " em preto e o valor na cor da vida."""
                wp = fonte_u.render(prefixo, True, C_TEXTO).get_width()
                wv = fonte_u.render(valor, True, cor_val).get_width()
                x0 = cx_sb - (wp + wv) // 2
                desenhar_texto_com_contorno(surf, prefixo, fonte_u, C_TEXTO, C_BORDA_TEXTO, x0, y)
                desenhar_texto_com_contorno(surf, valor, fonte_u, cor_val, C_BORDA_TEXTO, x0 + wp, y)

            dragao_acord = fortaleza_atual_index >= len(ordem_fortalezas)
            fortalezas_sb = [("fortaleza1", "Fort. 1"), ("fortaleza2", "Fort. 2"), ("fortaleza3", "Fort. 3")]

            # Alturas de texto para calcular espaçamentos
            ALT_LINHA = fonte_pequena.get_linesize()  # ~18px
            # Cada bloco fortaleza: imagem(55) + espaço(4) + nome(18) + espaço(3) + hp(18) = 98px
            # Espaçamento entre blocos: 8px → total por fortaleza = 106px

            y_off = 78
            for chave, nome_disp in fortalezas_sb:
                img_str = visuais_objetos[chave]
                wi, hi = img_str.get_size()  # 75 × 55
                tela_virtual.blit(img_str, (cx_sb - wi // 2, y_off))

                hp = vida_estruturas.get(chave, 0)
                hp_max = VIDA_FORTALEZA
                pct = hp / hp_max if hp_max > 0 else 0

                y_nome = y_off + hi + 4  # 4px abaixo da imagem
                y_hp = y_nome + ALT_LINHA + 2  # logo abaixo do nome

                wn = fonte_pequena.render(nome_disp, True, C_TEXTO).get_width()
                desenhar_texto_com_contorno(tela_virtual, nome_disp, fonte_pequena,
                                            C_TEXTO, C_BORDA_TEXTO, cx_sb - wn // 2, y_nome)
                if hp > 0:
                    cor_v = (0, 160, 0) if pct > 0.5 else (180, 140, 0) if pct > 0.25 else (180, 30, 30)
                    _render_hp_bicolor(tela_virtual, "HP: ", f"{hp}/{hp_max}",
                                       fonte_pequena, cor_v, cx_sb, y_hp)
                else:
                    wst = fonte_pequena.render("Destruida", True, (120, 120, 120)).get_width()
                    desenhar_texto_com_contorno(tela_virtual, "Destruida", fonte_pequena,
                                                (120, 120, 120), C_BORDA_TEXTO, cx_sb - wst // 2, y_hp)

                y_off = y_hp + ALT_LINHA + 8  # 8px de respiro entre blocos

            # ── Divisor + Dragão ─────────────────────────────────────────────
            # O dragão tem imagem maior (100×120), mas o padrão nome/HP é igual às fortalezas
            desenhar_divisor_ornamentado(tela_virtual, SB_X, y_off, larg_sb - 16, C_BORDA_TEXTO)
            y_off += 5

            img_drag = (visuais_objetos["dragao_acordado"] if dragao_acord
                        else visuais_objetos["dragao"])
            wd, hd = img_drag.get_size()  # 100 × 120
            tela_virtual.blit(img_drag, (cx_sb - wd // 2, y_off))

            hp_drag = vida_estruturas.get("dragao", 0)
            hp_max_d = VIDA_DRAGAO
            pct_d = hp_drag / hp_max_d if hp_max_d > 0 else 0

            # Mesmo padrão de espaçamento das fortalezas
            y_nome_d = y_off + hd + 4
            y_hp_d = y_nome_d + ALT_LINHA + 2

            wnd = fonte_pequena.render("Dragao", True, C_TEXTO).get_width()
            desenhar_texto_com_contorno(tela_virtual, "Dragao", fonte_pequena,
                                        C_TEXTO, C_BORDA_TEXTO,
                                        cx_sb - wnd // 2, y_nome_d)
            if hp_drag > 0:
                cor_vd = (0, 160, 0) if pct_d > 0.5 else (180, 140, 0) if pct_d > 0.25 else (180, 30, 30)
                _render_hp_bicolor(tela_virtual, "HP: ", f"{hp_drag}/{hp_max_d}",
                                   fonte_pequena, cor_vd, cx_sb, y_hp_d)
            else:
                wstd = fonte_pequena.render("Derrotado", True, (120, 120, 120)).get_width()
                desenhar_texto_com_contorno(tela_virtual, "Derrotado", fonte_pequena,
                                            (120, 120, 120), C_BORDA_TEXTO,
                                            cx_sb - wstd // 2, y_hp_d)

            y_off = y_hp_d + ALT_LINHA + 8  # mesmo respiro de 8px após o dragão

            # ── Divisor + Contadores (ícone + texto compactos) ───────────────
            desenhar_divisor_ornamentado(tela_virtual, SB_X, y_off, larg_sb - 16, C_BORDA_TEXTO)
            y_off += 6

            n_inim = len(lista_inimigos)
            n_poc = sum(1 for v in mapa_itens.values() if v == "pocao")
            n_perg = sum(1 for v in mapa_itens.values() if v == "pergaminho")

            contadores = [
                (img_sidebar_inimigo, f"Inimigos: {n_inim}", (200, 80, 80) if n_inim > 0 else (120, 120, 120)),
                (img_sidebar_pocao, f"Pocoes: {n_poc}", (80, 200, 80) if n_poc > 0 else (120, 120, 120)),
                (img_sidebar_pergaminho, f"Perg.: {n_perg}", (140, 120, 220) if n_perg > 0 else (120, 120, 120)),
            ]
            for icone, txt_c, cor_c in contadores:
                wi2, hi2 = icone.get_size()
                tela_virtual.blit(icone, (SB_X, y_off))
                desenhar_texto_com_contorno(tela_virtual, txt_c, fonte_pequena,
                                            cor_c, C_BORDA_TEXTO, SB_X + wi2 + 5,
                                            y_off + (hi2 - fonte_pequena.get_linesize()) // 2 + 2)
                y_off += hi2 + 2  # muito compacto entre contadores

            # ==========================================
            # PAINEL INFERIOR — info do herói selecionado
            # ==========================================
            pygame.draw.line(tela_virtual, C_BORDA_TEXTO,
                             (0, 12 * ALTURA_CELULA), (x_sb, 12 * ALTURA_CELULA), 2)

            # Retrato
            padrao = {"retrato": (-8, 525), "texto": (70, 695)}
            posicao = posicoes_customizadas.get(personagem_selecionado, padrao)
            tela_virtual.blit(retratos[personagem_selecionado], posicao["retrato"])

            # Nome + status
            nome_exib = NOMES_EXIBICAO[personagem_selecionado]
            status_h = " (MORTO)" if dados_sel["vida"] <= 0 else ""
            desenhar_texto_com_contorno(tela_virtual, nome_exib + status_h,
                                        fonte, C_TEXTO, C_BORDA_TEXTO,
                                        posicao["texto"][0], posicao["texto"][1])

            # HP + Pergaminhos + Bônus (com acento)
            bonus_total = round((dados_sel["bonus_ataque"] + dados_sel["pergaminhos"] * BONUS_PERGAMINHO - 1) * 100)
            X_INFO = 340  # posição x do bloco de informações — puxado para a direita
            info = (f"HP: {dados_sel['vida']}/{dados_sel['vida_max']}  |  "
                    f"Perg.: {dados_sel['pergaminhos']}  |  Bônus: +{bonus_total}%")
            desenhar_texto_com_contorno(tela_virtual, info, fonte, C_TEXTO, C_BORDA_TEXTO, X_INFO, 540)

            # Info contextual — apenas Escudeira (curandeira não exibe contador)
            y_extra = 558
            if personagem_selecionado == "escudeiro":
                alvo_atual = herois["escudeiro"].get("protegendo")
                if alvo_atual:
                    rest_prot = MAX_PROTECOES_POR_ALVO - herois[alvo_atual]["protecoes_recebidas"]
                    info_esc = f"Protegendo {NOMES_EXIBICAO[alvo_atual]}  |  {max(0, rest_prot)}/{MAX_PROTECOES_POR_ALVO} prot. restantes"
                else:
                    info_esc = f"Sem proteção ativa  |  Máx. {MAX_PROTECOES_POR_ALVO}x por aliado"
                desenhar_texto_com_contorno(tela_virtual, info_esc, fonte_pequena,
                                            (180, 200, 255), C_BORDA_TEXTO, X_INFO, y_extra)

            # Aviso de santuário ativo — sem símbolos especiais para compatibilidade de fonte
            if fortaleza_atual_index >= len(ordem_fortalezas) and santuario_visitado:
                aviso = "* Santuario ativo! ESPACO para atacar o Dragao! *"
                wav = fonte_pequena.render(aviso, True, (255, 220, 0)).get_width()
                cx_inf = (X_INFO + x_sb) // 2
                desenhar_texto_com_contorno(tela_virtual, aviso, fonte_pequena,
                                            (255, 220, 0), C_BORDA_TEXTO, cx_inf - wav // 2, 574)

            # Log de mensagens (4 linhas, 5s)
            tempo_atual = pygame.time.get_ticks()
            mensagem_log = [m for m in mensagem_log if tempo_atual - m["tempo"] < 5000]
            for i, m in enumerate(mensagem_log):
                desenhar_texto_com_contorno(tela_virtual, m["texto"], fonte_pequena,
                                            C_TEXTO, C_BORDA_TEXTO, X_INFO, 594 + i * 20)

            # Instruções de controle — alinhadas com X_INFO (mesma coluna do HP)
            linha1 = "1-5: Personagem  |  Setas: Mover  |  Espaço: Atacar"
            linha2 = "C: Curar  |  P: Proteger  |  V: Reviver  |  R: Reiniciar"
            desenhar_texto_com_contorno(tela_virtual, linha1, fonte_pequena,
                                        C_TEXTO, C_BORDA_TEXTO, X_INFO, 678)
            desenhar_texto_com_contorno(tela_virtual, linha2, fonte_pequena,
                                        C_TEXTO, C_BORDA_TEXTO, X_INFO, 698)

        tela_final = pygame.transform.smoothscale(tela_virtual, tamanho_atual)
        janela.blit(tela_final, (0, 0))
        pygame.display.update()
        clock.tick(60)

        # OBRIGATÓRIO PARA O NAVEGADOR RESPIRAR
        await asyncio.sleep(0)

    pygame.quit()


# Roda o jogo no formato assíncrono (pygbag)
asyncio.run(main())