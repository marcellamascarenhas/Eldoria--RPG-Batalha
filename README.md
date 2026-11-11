# ⚔️ Eldoria

> *"Há séculos, o reino de Eldoria vive sob a sombra de um antigo Dragão adormecido..."*

Eldoria é um jogo de estratégia por turnos em Python + Pygame, desenvolvido como projeto acadêmico. Controle um grupo de cinco heróis, destrua as fortalezas que selam o Dragão, alcance o Santuário Sagrado e enfrente a fera em batalha final.

---

## 🎮 Como Jogar

### Objetivo
1. Explore o mapa 12×12 e derrote inimigos pelo caminho
2. Colete **poções** (recuperam vida) e **pergaminhos** (aumentam ataque)
3. Destrua as **3 fortalezas** na ordem indicada na sidebar
4. Vá até o **Santuário Sagrado** (canto inferior direito)
5. Derrote o **Dragão** e salve Eldoria!

### Controles

| Tecla | Ação |
|-------|------|
| `1` – `5` | Selecionar herói |
| `↑ ↓ ← →` | Mover herói selecionado |
| `Espaço` | Atacar fortaleza atual ou Dragão |
| `C` | Curandeira cura aliado adjacente (máx. 25x por aliado) |
| `V` | Curandeira revive herói caído adjacente |
| `P` | Escudeira ativa/desativa proteção de aliado adjacente (máx. 5x por aliado) |
| `R` | Reiniciar a partida |

### Os Heróis

| # | Herói | Habilidade especial |
|---|-------|-------------------|
| 1 | **Guerreiro** | +20% de dano contra fortalezas e Dragão |
| 2 | **Arqueiro** | 30% de chance de dano crítico (dobrado) |
| 3 | **Curandeira** | Cura e revive aliados — **não pode ser revivida** |
| 4 | **Mago** | Alcance de ataque 3 células (outros: 1) |
| 5 | **Escudeira** | Divide o dano recebido por aliados 50/50 |

### Regras importantes
- São necessários **2+ heróis no alcance** para atacar uma fortaleza
- O Dragão só pode ser atacado **após visitar o Santuário**
- Heróis derrotados ficam em estado P&B por **5 turnos** antes de sumir (exceto a Curandeira, que some imediatamente)
- Um herói revivido morre **permanentemente** na segunda derrota

---

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.8 ou superior
- Pygame 2.x

```bash
pip install pygame
```

### Executar

```bash
python eldoria.py
```

---

## 📁 Estrutura de Arquivos

```
eldoria/
├── eldoria.py              # Código principal do jogo
├── NewRocker-Regular.ttf   # Fonte medieval (opcional — usa fonte padrão se ausente)
│
├── assets/
│   ├── sprites/            # Sprites dos heróis e inimigos
│   ├── estruturas/         # Imagens de fortalezas, base, santuário, etc.
│   └── items/              # Imagens de poções e pergaminhos
│
└── audio/                  # Músicas e efeitos sonoros (opcionais)
```

### Arquivos de imagem necessários

**Heróis e inimigos**
- `Sprite_Guerreiro.png`, `Sprite_Arqueiro.png`, `Sprite_Curandeiro.png`
- `Sprite_Mago.png`, `Sprite_Escudeiro.png`, `Sprite_Inimigo.png`
- `Selecionado_Guerreiro.png`, `Selecionado_Arqueiro.png`, `Selecionado_Curandeiro.png`
- `Selecionado_Mago.png`, `Selecionado_Escudeiro.png`

**Estruturas e mapa**
- `Fortaleza_1.png`, `Fortaleza_2.png`, `Fortaleza_3.png`
- `Dragao_Adormecido.png`, `Dragao_Acordado.png`
- `Santuario_Dragao.png`, `base.png`
- `Estruturas_ArvoresComFolhasV2.png`, `Estruturas_ArvoresSemFolhasV2.png`
- `Estruturas_Estatua.png`, `Estruturas_Pedra.png`, `Estruturas_Muro.png`

**Itens**
- `Item_Pocao.png`, `Item_PergaminhoV2.png`

**Tela de capa**
- `Capa_Eldoria.jpeg`

### Arquivos de áudio (todos opcionais — o jogo roda sem som)

| Arquivo | Evento |
|---------|--------|
| `nova_musica.mp3` | Música principal (loop) |
| `musica_final.mp3` | Música de vitória |
| `fundo_batalha_final.mp3` | Camada extra durante batalha final |
| `pocao.mp3` | Coleta de poção |
| `pergaminho.mp3` | Coleta de pergaminho |
| `morte_jogador.mp3` | Herói derrotado |
| `vitoria.mp3` | Stinger de vitória |
| `derrota.mp3` | Stinger de derrota |
| `ataque_inimigo_dragao.mp3` | Acerto em inimigo ou Dragão |
| `ataque_fortaleza.mp3` | Acerto em fortaleza |
| `personagem_erra.mp3` | Ataque errado |
| `cura.mp3` | Habilidade de cura |
| `som_reviver.mp3` | Habilidade de reviver |
| `fortaleza_caiu.mp3` | Fortaleza 1 ou 2 destruída |
| `fortalezas_derrubadas.mp3` | Fortaleza 3 destruída (todas caíram) |
| `dragao_acordado.mp3` | Dragão acorda |
| `dragao_movimentando.mp3` | Loop enquanto Dragão persegue |
| `chegou_santuario.mp3` | Chegada ao Santuário |
| `escudeiro_protege.mp3` | Escudeira ativa proteção |
| `arqueiro_critico.mp3` | Crítico do Arqueiro |

---

## 🧠 Arquitetura do Código

O jogo é estruturado em um único arquivo Python com seções bem definidas:

```
eldoria.py
├── Constantes e balanceamento
├── Sistema de áudio (graceful degradation)
├── Configurações da janela e tela virtual
├── Funções utilitárias (renderização, UI)
├── Pathfinding BFS (movimento do Dragão)
├── Geração do mapa (obstáculos, itens, inimigos)
├── Sprites e retratos dos heróis
├── Estado global do jogo
├── Lógica de combate
│   ├── Dano com proteção da Escudeira
│   ├── Ataque a fortalezas
│   └── Ataque ao Dragão
├── IA do Dragão (BFS + aleatoriedade)
├── Telas especiais (Capa, Tutorial, Vitória, Derrota)
└── Loop principal (eventos → lógica → renderização)
```

### Decisões de design
- **Tela virtual escalável**: o jogo renderiza em 991×730 e escala para qualquer tamanho de janela com `pygame.transform.smoothscale`
- **Snapshot do mapa**: o mapa aleatório é gerado uma vez e salvo em `copy.deepcopy` para o reinício restaurar exatamente o mesmo layout
- **Graceful degradation**: imagens e sons ausentes geram avisos no console mas não travam o jogo
- **Canais de áudio dedicados**: loop do Dragão (canal 8) e música de batalha final (canal 7) usam canais fixos para controle preciso de volume e loop

---

## 👥 Créditos

Desenvolvido como projeto acadêmico.

- **Motor**: Python 3 + Pygame 2
- **Arte**: assets criados para o projeto
- **Fonte**: NewRocker (Google Fonts)
