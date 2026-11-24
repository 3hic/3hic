"""Gera os SVGs do perfil 3hic: preto e azul frio, sem enfeite.

Um tema só, escuro, igual em qualquer tema do GitHub. Tudo usa uma fonte só, a Zen Kaku Gothic New
(SIL OFL 1.1), embutida só com as letras usadas, porque imagem no README do GitHub não carrega
nada de fora. Os quadros saem no tamanho real (720px de largura): nada é esticado pelo README.

Uso:  pip install fonttools brotli
      python gerador/gerar.py
Na primeira vez a fonte é baixada do google/fonts para gerador/.fontes (fora do git).
"""
import base64
import html
import io
import urllib.request
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

try:
    import brotli  # noqa: F401
    FORMATO, MIME = 'woff2', 'font/woff2'
except ImportError:  # sem brotli sai WOFF (zlib), só um pouco maior
    FORMATO, MIME = 'woff', 'font/woff'

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI.parent / 'assets'
CACHE = AQUI / '.fontes'
GOOGLE_FONTS = 'https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/'
PESOS = {'l': 'ZenKakuGothicNew-Light.ttf', 'r': 'ZenKakuGothicNew-Regular.ttf'}   # fino e normal
PILHA = "'Yu Gothic','Hiragino Sans',sans-serif"

EMAIL = 'icizim8@gmail.com'
DISCORD = 'naturalismos'

# a noite: preto quase puro, tinta cinza-azulada e um azul de aço bem apagado
NOITE = dict(fundo='#030405', borda='#141920', linha='#0F1318', tinta='#BAC3CF', tinta2='#7A8798',
             tinta3='#566275', azul='#5B7694')


# ---------------------------------------------------------------- fonte

def esc(s):
    return html.escape(s, quote=True)


def n(v):
    """Número curto para o SVG."""
    if isinstance(v, float):
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    return str(v)


def arquivo_fonte(peso):
    destino = CACHE / PESOS[peso]
    if not destino.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print('baixando', PESOS[peso])
        with urllib.request.urlopen(GOOGLE_FONTS + PESOS[peso], timeout=180) as r:
            destino.write_bytes(r.read())
    return destino


@lru_cache(maxsize=None)
def avancos(peso):
    f = TTFont(arquivo_fonte(peso), lazy=True)
    upm, hmtx = f['head'].unitsPerEm, f['hmtx']
    return {cp: hmtx[g][0] / upm for cp, g in f.getBestCmap().items()}


def medir(texto, peso, tam, espaco=0):
    av = avancos(peso)
    return sum(av.get(ord(c), 0.5) * tam + espaco for c in texto)


def embutir(peso, letras):
    """Subconjunto da fonte (base64) só com as letras usadas. Mantém nome, copyright e licença."""
    op = subset.Options()
    op.flavor = FORMATO
    op.name_IDs = ['*']
    op.name_languages = ['*']
    op.notdef_outline = True
    op.hinting = False
    fonte = TTFont(arquivo_fonte(peso))
    sub = subset.Subsetter(options=op)
    sub.populate(text=letras)
    sub.subset(fonte)
    buf = io.BytesIO()
    fonte.flavor = FORMATO
    fonte.save(buf)
    return base64.b64encode(buf.getvalue()).decode('ascii')


# ---------------------------------------------------------------- SVG

class Svg:
    def __init__(self, w, h, titulo, desc):
        self.w, self.h, self.titulo, self.desc = w, h, titulo, desc
        self.letras = {k: set() for k in PESOS}
        self.defs, self.corpo, self.css = [], [], []

    def t(self, s, x, y, tam, cor, peso='r', ancora='start', espaco=0):
        """Texto. Devolve a largura, para quem vem depois se alinhar."""
        self.letras[peso].update(s)
        a = '' if ancora == 'start' else f' text-anchor="{ancora}"'
        e = f' letter-spacing="{n(espaco)}"' if espaco else ''
        self.corpo.append(f'<text class="{peso}" x="{n(x)}" y="{n(y)}" font-size="{n(tam)}" '
                          f'fill="{cor}"{a}{e}>{esc(s)}</text>')
        return medir(s, peso, tam, espaco)

    def add(self, *partes):
        self.corpo.extend(partes)

    def render(self, fontes):
        css = ["@font-face{font-family:'Z-%s';src:url(data:%s;base64,%s) format('%s')}"
               % (peso, MIME, dados, FORMATO) for peso, dados in fontes.items()]
        css += [".%s{font-family:'Z-%s',%s}" % (peso, peso, PILHA) for peso in PESOS]
        css += self.css
        defs = f'<defs>{"".join(self.defs)}</defs>\n' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="titulo desc">\n'
                f'<title id="titulo">{esc(self.titulo)}</title>\n<desc id="desc">{esc(self.desc)}</desc>\n'
                '<!-- gerado por gerador/gerar.py; fonte Zen Kaku Gothic New (SIL OFL 1.1), só as letras usadas -->\n'
                f'<style>{"".join(css)}</style>\n{defs}' + '\n'.join(self.corpo) + '\n</svg>\n')


# ---------------------------------------------------------------- peças

def cartao(s, p, x, y, w, h):
    """Quadro preto com uma borda fina, sem enfeite."""
    s.add(f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="4" fill="{p["fundo"]}" '
          f'stroke="{p["borda"]}"/>')


def nevoa(s, p, w, h):
    """Uma névoa azul bem leve no pé do quadro."""
    s.defs.append(f'<linearGradient id="nev" x1="0" y1="0" x2="0" y2="1">'
                  f'<stop offset=".5" stop-color="{p["azul"]}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{p["azul"]}" stop-opacity=".09"/></linearGradient>')
    s.add(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="4" fill="url(#nev)"/>')


def selo(s, p, x, y, tam, letra):
    """Carimbo de tinta azul: só o contorno e a letra, levemente torto."""
    cx, cy = x + tam / 2, y + tam / 2
    giro = f'rotate(-4 {n(cx)} {n(cy)})'
    s.letras['r'].update(letra)
    s.add(f'<rect x="{n(x)}" y="{n(y)}" width="{tam}" height="{tam}" rx="{n(tam * .08)}" fill="none" '
          f'stroke="{p["azul"]}" stroke-width="1.2" transform="{giro}"/>',
          f'<text class="r" x="{n(cx)}" y="{n(cy + tam * .24)}" font-size="{n(tam * .66)}" fill="{p["azul"]}" '
          f'text-anchor="middle" transform="{giro}">{esc(letra)}</text>')


def coluna(s, letras, x, y, tam, passo, cor, peso='r'):
    """Texto na vertical (tategaki), uma letra por vez, de cima para baixo."""
    for i, c in enumerate(letras):
        s.t(c, x, y + i * passo, tam, cor, peso, ancora='middle')


def cabecalho(s, p, x, y, jp, pt, largura):
    """Título da seção: palavra em japonês, tradução miúda e uma linha fina por baixo."""
    w = s.t(jp, x, y, 14, p['tinta'], 'r', espaco=1.5)
    s.t(pt, x + w + 12, y, 12, p['tinta3'], 'r', espaco=1.2)
    s.add(f'<line x1="{n(x)}" y1="{n(y + 12)}" x2="{n(x + largura)}" y2="{n(y + 12)}" stroke="{p["linha"]}"/>')


def seta(s, p, x, y):
    s.add(f'<path d="M{n(x)} {n(y)}h18m-5-4 5 4-5 4" fill="none" stroke="{p["azul"]}" stroke-width="1.3" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')


CLAUDE = '#D97757'   # a cor do Claude, a única quente da página
CLAWD = [            # o bonequinho do Claude Code, do jeito que aparece no terminal
    ' ▐▛███▜▌',
    '▝▜█████▛▘',
    '  ▘▘ ▝▝',
]
QUADRANTES = {' ': '', '█': 'abcd', '▌': 'ac', '▐': 'bd', '▀': 'ab', '▄': 'cd', '▘': 'a', '▝': 'b', '▖': 'c',
              '▗': 'd', '▛': 'abc', '▜': 'abd', '▙': 'acd', '▟': 'bcd'}   # a b / c d: os 4 quadrantes do bloco
PIXELS_CLAWD = {(c * 2 + (q in 'bd'), lin * 2 + (q in 'cd'))
                for lin, linha in enumerate(CLAWD) for c, ch in enumerate(linha) for q in QUADRANTES[ch]}


def clawd(s, ox, oy, pw, ph):
    """O Clawd em retângulos (uma fileira de pixels vizinhos vira um retângulo só, sem frestas).
    Balança devagar e pisca: os olhos são os furos da fileira 1, que se fecham por um instante."""
    rets = []
    for y in sorted({y for _, y in PIXELS_CLAWD}):
        xs = sorted(x for x, yy in PIXELS_CLAWD if yy == y)
        ini = ant = xs[0]
        for x in xs[1:] + [None]:
            if x != ant + 1:
                # a altura leva um fio a mais: sobrepõe a fileira de baixo e some a fresta que o
                # antialiasing abre entre retângulos vizinhos (principalmente com a imagem reduzida)
                rets.append(f'<rect x="{n(ox + ini * pw)}" y="{n(oy + y * ph)}" '
                            f'width="{n((ant - ini + 1) * pw)}" height="{n(ph + .4)}"/>')
                ini = x
            ant = x
    todos = [x for x, _ in PIXELS_CLAWD]
    olhos = [x for x in range(min(todos), max(todos)) if (x, 1) not in PIXELS_CLAWD
             and (x - 1, 1) in PIXELS_CLAWD and (x + 1, 1) in PIXELS_CLAWD]
    piscar = ''.join(f'<rect class="olho" x="{n(ox + x * pw)}" y="{n(oy + ph)}" width="{n(pw)}" '
                     f'height="{n(ph)}"/>' for x in olhos)
    s.add(f'<g class="bob" fill="{CLAUDE}" shape-rendering="crispEdges">{"".join(rets)}{piscar}</g>')
    s.css.append('.bob{animation:bob 2.6s ease-in-out infinite}'
                 '@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}'
                 '.olho{opacity:0;animation:olho 4.6s steps(1,end) infinite}'
                 '@keyframes olho{0%,92%{opacity:0}93%,96%{opacity:1}97%,100%{opacity:0}}')


# ---------------------------------------------------------------- quadros

LARGURA = 720      # todos os quadros inteiros têm esta largura
CARTAO_W = 358     # cada um dos dois cartões lado a lado (358 + 358 + o espaço entre eles = 720)


def hero(p):
    h = 156
    s = Svg(LARGURA, h, '3hic',
            'Cartaz do perfil de 3hic, preto e azul frio: o nome com um carimbo azul, o lema "sempre '
            'aprendendo, sempre construindo" e, na vertical, 学び続ける e 作り続ける (continuar aprendendo, '
            'continuar construindo).')
    cartao(s, p, 0, 0, LARGURA, h)
    nevoa(s, p, LARGURA, h)
    w = s.t('3hic', 40, 88, 64, p['tinta'], 'l')
    selo(s, p, 40 + w + 16, 62, 26, '三')
    s.t('sempre aprendendo, sempre construindo.', 42, 118, 13, p['tinta2'], 'r', espaco=.5)
    coluna(s, '学び続ける', 671, 38, 17, 24, p['tinta2'])
    coluna(s, '作り続ける', 641, 38, 17, 24, p['tinta2'])
    return s


def card_projeto(p):
    h = 208
    s = Svg(CARTAO_W, h, 'Bot-discord',
            'Projeto Bot-discord: moderação, tickets, sorteios, logs e uma sociedade secreta, feito com '
            'python, discord.py e sqlite. Leva para github.com/3hic/Bot-discord.')
    cartao(s, p, 0, 0, CARTAO_W - 4, h)
    cabecalho(s, p, 32, 36, '作品', 'projeto', CARTAO_W - 4 - 64)
    s.t('Bot-discord', 31, 92, 28, p['tinta'], 'l')
    s.t('python · discord.py · sqlite', 32, 114, 12, p['tinta3'], 'r', espaco=.4)
    s.t('moderação, tickets, sorteios, logs', 32, 144, 13, p['tinta2'])
    s.t('e uma sociedade secreta.', 32, 163, 13, p['tinta2'])
    w = s.t('github.com/3hic/Bot-discord', 32, 192, 12.5, p['tinta'], 'r')
    seta(s, p, 32 + w + 10, 188)
    return s


def card_stack(p):
    dx = 4   # este cartão fica à direita do outro: sobra um vão entre os dois
    h = 208
    s = Svg(CARTAO_W, h, 'stack',
            'Stack: python (bots e automação), javascript (scripts no navegador), electron (apps de '
            'desktop), sqlite (dados dos bots), discord (comunidades) e git (versões).')
    cartao(s, p, dx, 0, CARTAO_W - 4, h)
    cabecalho(s, p, dx + 32, 36, '技術', 'stack', CARTAO_W - 4 - 64)
    itens = [('python', 'bots e automação'), ('javascript', 'scripts no navegador'),
             ('electron', 'apps de desktop'), ('sqlite', 'dados dos bots'),
             ('discord', 'comunidades'), ('git', 'versões')]
    for i, (nome, desc) in enumerate(itens):
        y = 48 + i * 25
        if i:
            s.add(f'<line x1="{dx + 32}" y1="{y}" x2="{CARTAO_W - 36}" y2="{y}" stroke="{p["linha"]}"/>')
        s.t(nome, dx + 32, y + 17, 14, p['tinta'], 'r')
        s.t(desc, CARTAO_W - 36, y + 17, 12, p['tinta3'], 'r', ancora='end')
    return s


def card_ia(p):
    h = 84
    s = Svg(LARGURA, h, 'uso IA',
            'Uso IA, o Claude: o bonequinho do Claude, que balança e pisca, e os textos "uso IA, Claude" e '
            '"automação com IA".')
    cartao(s, p, 0, 0, LARGURA, h)
    pw, ph = 4, 8   # pixel largo e alto, como o caractere do terminal (1:2)
    largura = (max(x for x, _ in PIXELS_CLAWD) + 1) * pw
    clawd(s, 36, (h - 6 * ph) / 2 + 1, pw, ph)
    x = 36 + largura + 24
    a = s.t('uso IA', x, 38, 16, p['tinta'])
    b = s.t('·', x + a + 8, 38, 16, p['tinta3'])
    s.t('Claude', x + a + b + 16, 38, 16, CLAUDE)
    s.t('automação com IA', x, 60, 12.5, p['tinta2'])
    ia = s.t('ia', LARGURA - 40, 38, 12, p['tinta3'], 'r', ancora='end', espaco=1.2)
    s.t('人工知能', LARGURA - 40 - ia - 12, 38, 14, p['tinta'], 'r', ancora='end', espaco=1.5)
    return s


def card_contato(p, dx, servico, valor, sublinhar):
    """Cartão baixo de contato. Sublinhado em azul só quando o cartão é um link."""
    h = 54
    s = Svg(CARTAO_W, h, f'contato: {servico}', f'Contato por {servico}: {valor}.')
    cartao(s, p, dx, 0, CARTAO_W - 4, h)
    w = s.t('連絡', dx + 32, 32, 14, p['tinta'], 'r', espaco=1.5)
    s.t(servico, dx + 32 + w + 12, 32, 12, p['tinta3'], 'r', espaco=1.2)
    x = dx + CARTAO_W - 4 - 32
    largura = s.t(valor, x, 32, 15, p['tinta'], 'r', ancora='end')
    if sublinhar:
        s.add(f'<rect x="{n(x - largura)}" y="38.5" width="{n(largura)}" height="1" fill="{p["azul"]}"/>')
    return s


def contato_gmail(p):
    return card_contato(p, 0, 'gmail', EMAIL, True)


def contato_discord(p):
    return card_contato(p, 4, 'discord', DISCORD, False)   # o da direita: 4px de vão, como projeto e stack


QUADROS = [('hero', hero), ('projeto', card_projeto), ('stack', card_stack), ('ia', card_ia),
           ('contato-gmail', contato_gmail), ('contato-discord', contato_discord)]


def main():
    ASSETS.mkdir(exist_ok=True)
    pronto = [(f'{nome}.svg', desenhar(NOITE)) for nome, desenhar in QUADROS]
    # uma fonte só por peso, com a união das letras de todos os quadros
    uniao = {peso: set() for peso in PESOS}
    for _, s in pronto:
        for peso, letras in s.letras.items():
            uniao[peso] |= letras
    fontes = {}
    for peso, letras in uniao.items():
        letras = ''.join(sorted(letras))
        faltam = ''.join(c for c in letras if c.strip() and ord(c) not in avancos(peso))
        if faltam:
            print(f'AVISO: a fonte {peso} não tem "{faltam}"')
        fontes[peso] = embutir(peso, letras)
    for arquivo, s in pronto:
        svg = s.render(fontes)
        (ASSETS / arquivo).write_text(svg, encoding='utf-8')
        print(f'{arquivo:16} {len(svg.encode("utf-8")) / 1024:6.1f} KB')


if __name__ == '__main__':
    main()
