"""Gera os SVGs do perfil 3hic no tema Serial Experiments Lain.

Tema único, escuro: a Wired (o quarto da Lain à noite) — todos os quadros iguais, em qualquer tema
do GitHub. Cada SVG leva embutidas só as letras que usa, porque imagem no README do GitHub não
carrega nada de fora:
  - DotGothic16 (Fontworks, SIL OFL 1.1) é a voz da máquina: NAVI, terminal, código;
  - Shippori Mincho (SIL OFL 1.1) é a voz humana: o nome e as frases.

Uso:  pip install fonttools brotli
      python gerador/gerar.py
Na primeira vez as fontes são baixadas do google/fonts para gerador/.fontes (fora do git).
As animações rodam sempre, mesmo com "reduzir movimento" ligado no sistema (pedido do dono do perfil).
"""
import base64
import html
import io
import math
import random
import re
import urllib.request
from collections import Counter
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI.parent / 'assets'
CACHE = AQUI / '.fontes'
GOOGLE_FONTS = 'https://github.com/google/fonts/raw/main/ofl/'
FONTES = {  # nome: (arquivo no google/fonts, pilha de fontes)
    'dot': ('dotgothic16/DotGothic16-Regular.ttf', "'L-dot','MS Gothic','Osaka-Mono',monospace"),
    'min': ('shipporimincho/ShipporiMincho-Medium.ttf', "'L-min','Yu Mincho','Hiragino Mincho ProN',serif"),
    'minb': ('shipporimincho/ShipporiMincho-SemiBold.ttf', "'L-minb','Yu Mincho','Hiragino Mincho ProN',serif"),
}

# a Wired: o quarto da Lain à noite (índigo, lavanda do GIF, creme da pele, as manchas vermelhas)
TEMA = dict(ceu1='#1A1836', ceu2='#25214B', ceu3='#4A2A55', chao='#0A0918', fio='#06050E',
            fundo='#14122B', sup='#1C1A38', borda='#34305C', texto='#EFE9DC', texto2='#ABA6DA',
            texto3='#6F6B9C', vermelho='#E0304E', urso='#D9C3A0', tela='#C9DCFF',
            placa='#EFE9DC', placa_txt='#14122B', grao='.16')
LARANJA, FOLHA = '#E8892B', '#7FA35B'   # tachibana: a mexerica que dá nome à fabricante do NAVI


# ---------------------------------------------------------------- utilidades

def esc(s):
    return html.escape(s, quote=True)


def n(v):
    """Número curto para o SVG."""
    if isinstance(v, float):
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    return str(v)


def arquivo_fonte(nome):
    rel = FONTES[nome][0]
    destino = CACHE / Path(rel).name
    if not destino.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print('baixando', rel)
        with urllib.request.urlopen(GOOGLE_FONTS + rel, timeout=180) as r:
            destino.write_bytes(r.read())
    return destino


@lru_cache(maxsize=None)
def avancos(nome):
    f = TTFont(arquivo_fonte(nome), lazy=True)
    upm, hmtx = f['head'].unitsPerEm, f['hmtx']
    return {cp: hmtx[g][0] / upm for cp, g in f.getBestCmap().items()}


def medir(texto, nome, tam):
    av = avancos(nome)
    return sum(av.get(ord(c), 0.5) for c in texto) * tam


@lru_cache(maxsize=None)
def embutir(nome, letras):
    """Subconjunto WOFF2 (base64) só com as letras usadas. Mantém o nome/copyright/licença da fonte."""
    op = subset.Options()
    op.flavor = 'woff2'
    op.name_IDs = ['*']
    op.name_languages = ['*']
    op.notdef_outline = True
    op.hinting = False
    fonte = TTFont(arquivo_fonte(nome))
    sub = subset.Subsetter(options=op)
    sub.populate(text=letras)
    sub.subset(fonte)
    buf = io.BytesIO()
    fonte.flavor = 'woff2'
    fonte.save(buf)
    return base64.b64encode(buf.getvalue()).decode('ascii')


class Svg:
    def __init__(self, w, h, titulo, desc):
        self.w, self.h, self.titulo, self.desc = w, h, titulo, desc
        self.letras = {k: set() for k in FONTES}
        self.defs, self.css, self.corpo = [], [], []

    def texto(self, s, fonte, x, y, tam, cor, ancora=None, cls='', extra=''):
        self.letras[fonte].update(s)
        a = f' text-anchor="{ancora}"' if ancora else ''
        c = f' {cls}' if cls else ''
        return (f'<text class="{fonte}{c}" x="{n(x)}" y="{n(y)}" font-size="{n(tam)}" fill="{cor}"{a}{extra}>'
                f'{esc(s)}</text>')

    def add(self, *partes):
        self.corpo.extend(partes)

    def salvar(self, caminho):
        css = []
        for nome, letras in self.letras.items():
            letras = ''.join(sorted(letras - {'\n'}))
            faltam = ''.join(c for c in letras if c.strip() and ord(c) not in avancos(nome))
            if faltam:
                print(f'  AVISO {caminho.name}: a fonte {nome} não tem "{faltam}"')
            if letras:
                css.append("@font-face{font-family:'L-%s';src:url(data:font/woff2;base64,%s) format('woff2')}"
                           % (nome, embutir(nome, letras)))
        css += ['.%s{font-family:%s}' % (k, v[1]) for k, v in FONTES.items()]
        css.append('.dot{font-kerning:none;font-variant-ligatures:none}')
        css += self.css
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="titulo desc">\n'
               f'<title id="titulo">{esc(self.titulo)}</title>\n<desc id="desc">{esc(self.desc)}</desc>\n'
               '<!-- gerado por gerador/gerar.py; fontes DotGothic16 e Shippori Mincho (SIL OFL 1.1), '
               'só as letras usadas -->\n'
               f'<style>{"".join(css)}</style>\n<defs>{"".join(self.defs)}</defs>\n'
               + '\n'.join(self.corpo) + '\n</svg>\n')
        caminho.write_text(svg, encoding='utf-8')
        return len(svg.encode('utf-8'))


def cabe(texto, fonte, tam, largura, onde):
    w = medir(texto, fonte, tam)
    if w > largura:
        print(f'  AVISO {onde}: "{texto}" mede {w:.0f}px (cabe {largura}px)')


def catenaria(x0, y0, x1, y1, flecha):
    """Fio entre dois pontos, caído no meio (o meio desce `flecha` abaixo da reta)."""
    return f'M{n(x0)} {n(y0)}Q{n((x0 + x1) / 2)} {n((y0 + y1) / 2 + 2 * flecha)} {n(x1)} {n(y1)}'


def fio(d, cor, largura, zumbido=None, extra=''):
    base = f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="{largura}" stroke-linecap="round"{extra}'
    if not zumbido:
        return base + '/>'
    d2, dur = zumbido
    return (base + f'><animate attributeName="d" values="{d};{d2};{d}" dur="{dur:.1f}s" repeatCount="indefinite" '
            'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/></path>')


def janela(s, t, w, h, titulo, direita):
    """Janela do Copland OS: barra com a tachibana (mexerica), título à esquerda e um detalhe à direita."""
    s.add(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="7" fill="{t["fundo"]}" stroke="{t["borda"]}"/>',
          f'<path d="M.5 32V7.5A7 7 0 0 1 7.5 .5H{w - 7.5}A7 7 0 0 1 {w - .5} 7.5V32Z" fill="{t["sup"]}"/>',
          f'<path d="M.5 32.5H{w - .5}" stroke="{t["borda"]}"/>',
          f'<circle cx="20" cy="16.5" r="5.5" fill="{LARANJA}"/>'
          f'<ellipse cx="23.6" cy="10.6" rx="3.1" ry="1.4" transform="rotate(-32 23.6 10.6)" fill="{FOLHA}"/>',
          s.texto(titulo, 'dot', 34, 21.5, 14, t['texto2']),
          s.texto(direita, 'dot', w - 16, 21.5, 13, t['texto3'], ancora='end'))


def ceu(s, t, w, h):
    """O céu da Wired, com linhas de varredura e grão por cima (fica no fundo; as camadas vêm depois)."""
    s.defs.append(f'<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["ceu1"]}"/>'
                  f'<stop offset=".58" stop-color="{t["ceu2"]}"/><stop offset="1" stop-color="{t["ceu3"]}"/>'
                  '</linearGradient>'
                  '<filter id="grao" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" '
                  'baseFrequency=".9" numOctaves="2" seed="7" stitchTiles="stitch"/>'
                  '<feColorMatrix values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1.4 -.55"/></filter>'
                  '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
                  '<rect width="4" height="1" fill="#000" fill-opacity=".22"/></pattern>')
    s.add(f'<rect width="{w}" height="{h}" fill="url(#ceu)"/>')


def textura(s, t, w, h):
    s.add(f'<rect width="{w}" height="{h}" fill="url(#scan)"/>',
          f'<rect width="{w}" height="{h}" filter="url(#grao)" opacity="{t["grao"]}"/>')


def linhas_digitadas(s, t, comandos, x0, ys, tam, inicio):
    """Prompt + comandos digitados letra por letra. Devolve o instante em que o último termina."""
    prompt, cw, tt = '3hic@navi ~ % ', tam * .5, inicio
    for texto, y in zip(comandos, ys):
        s.letras['dot'].update(prompt + texto)
        partes = [f'<tspan class="p" style="animation-delay:{tt:.2f}s">{esc(prompt.rstrip())}</tspan>']
        t0 = tt + .25
        for k, ch in enumerate(texto):
            if ch != ' ':
                partes.append(f'<tspan class="c" x="{n(x0 + (len(prompt) + k) * cw)}" fill="{t["texto"]}" '
                              f'style="animation-delay:{t0 + k * .045:.2f}s">{esc(ch)}</tspan>')
        s.add(f'<text class="dot" x="{x0}" y="{n(y)}" font-size="{tam}" fill="{t["texto3"]}">{"".join(partes)}</text>')
        tt = t0 + len(texto) * .045 + .35
    return tt


CSS_DIGITACAO = ('.p,.c{fill-opacity:0;animation:liga .01s steps(1,end) forwards}'
                 '.l{opacity:0;animation:mostra .01s steps(1,end) forwards}'
                 '@keyframes liga{to{fill-opacity:1}}@keyframes mostra{to{opacity:1}}'
                 '.cur{opacity:0;animation:pisca 1.1s steps(1,end) infinite}@keyframes pisca{0%{opacity:1}50%{opacity:0}}')


# ---------------------------------------------------------------- hero: postes e fios

def hero(t):
    W, H = 900, 340
    s = Svg(W, H, 'serial experiments 3hic',
            'Céu noturno com postes e fios elétricos, como na abertura de Serial Experiments Lain. O nome 3hic em '
            'letras grandes, a frase "present day, present time." e uma risada vermelha. Na placa do poste está '
            'escrito ワイヤード (Wired). No chão, as sombras têm manchas vermelhas, como no anime.')
    ceu(s, t, W, H)
    px = 748                                     # o poste
    isol1, y_isol1 = [690, 716, 780, 806], 36    # isoladores da cruzeta de cima
    isol2, y_isol2 = [708, 788], 77              # e da de baixo

    # fios longos: chegam de fora pela esquerda, caem por cima do título e sobem até o poste (zumbindo)
    for i, (xi, (y0, flecha)) in enumerate(zip(isol1, [(-8, 44), (-2, 48), (4, 53), (10, 58)])):
        d = catenaria(-20, y0, xi, y_isol1, flecha)
        s.add(fio(d, t['fio'], 1.6, (catenaria(-20, y0, xi, y_isol1, flecha + 3.5), 6 + i * .9)))

    # chão: telhados baixos de bairro japonês (com caixas d'água e antenas de TV dos anos 90)
    rnd = random.Random(1998)
    predios, x = [], -12
    while x < W + 10:
        w = rnd.randint(46, 112)
        predios.append((x, w, rnd.randint(280, 306), rnd.choice(['plano', 'telhado', 'plano', 'telhado', 'caixa'])))
        x += w
    partes = []
    for x, w, topo, tipo in predios:
        if tipo == 'telhado':
            partes.append(f'M{x} {H}V{topo}L{n(x + w / 2)} {topo - 13}L{x + w} {topo}V{H}Z')
        else:
            partes.append(f'M{x} {H}V{topo}H{x + w}V{H}Z')
            if tipo == 'caixa':
                partes.append(f'M{n(x + w * .58)} {topo}v-11h15v11Z')
    chao = ''.join(partes)
    s.defs.append(f'<clipPath id="chao"><path d="{chao}"/></clipPath>')
    s.add(f'<path d="{chao}" fill="{t["chao"]}"/>')
    for x, w, topo, _ in [p for p in predios if p[3] == 'plano'][::2][:4]:
        ax = x + w * .3
        s.add(f'<path d="M{n(ax)} {topo}v-24M{n(ax - 8)} {topo - 22}h16M{n(ax - 6)} {topo - 17}h12M{n(ax - 4)} '
              f'{topo - 12}h8" stroke="{t["chao"]}" stroke-width="1.4" fill="none"/>')
    for x, w, topo, _ in predios[1::3]:
        s.add(f'<rect x="{n(x + w * .62)}" y="{topo + 12}" width="5" height="7" fill="{t["tela"]}" fill-opacity=".5"/>')
    manchas = []
    for _ in range(18):           # as manchas vermelhas que o anime põe dentro das sombras
        cx, cy = rnd.uniform(0, W), rnd.uniform(300, 336)
        for _ in range(rnd.randint(6, 13)):
            manchas.append(f'<circle cx="{n(rnd.gauss(cx, 10))}" cy="{n(rnd.gauss(cy, 4))}" '
                           f'r="{n(rnd.uniform(.7, 2.5))}" fill-opacity="{n(rnd.uniform(.45, .95))}"/>')
    s.add(f'<g clip-path="url(#chao)" fill="{t["vermelho"]}">{"".join(manchas)}</g>')

    def topo_em(xx):
        return next((topo for x, w, topo, _ in predios if x <= xx < x + w), 300)

    # ramais do poste até as casas, e os fios que seguem para a direita
    s.add(fio(catenaria(isol2[0], y_isol2, 606, topo_em(606), 10), t['fio'], 1.1))
    s.add(fio(catenaria(isol2[1], y_isol2, 868, topo_em(868), 8), t['fio'], 1.1))
    for xi, y1, fl in zip(isol1, [50, 55, 61, 66], [9, 8, 6, 5]):
        s.add(fio(catenaria(xi, y_isol1, 920, y1, fl), t['fio'], 1.6))
    s.add(fio(catenaria(px + 6, 150, 920, 160, 6), t['fio'], 3.2))

    # o poste: cruzetas, isoladores, mão-francesa, transformador, degraus e a placa
    f = t['fio']
    s.add(f'<path d="M{px - 4} 16H{px + 4}L{px + 6.5} {H}H{px - 6.5}Z" fill="{f}"/>',
          f'<rect x="680" y="44" width="136" height="5" fill="{f}"/><rect x="700" y="84" width="96" height="4" fill="{f}"/>',
          f'<path d="M{px - 34} 49L{px - 4} 70M{px + 34} 49L{px + 4} 70" stroke="{f}" stroke-width="2"/>',
          ''.join(f'<rect x="{xi - 2.2}" y="{y_isol1}" width="4.4" height="8" fill="{f}"/>'
                  f'<circle cx="{xi}" cy="{y_isol1}" r="2.6" fill="{f}"/>' for xi in isol1),
          ''.join(f'<rect x="{xi - 2}" y="{y_isol2}" width="4" height="7" fill="{f}"/>'
                  f'<circle cx="{xi}" cy="{y_isol2}" r="2.3" fill="{f}"/>' for xi in isol2),
          f'<rect x="{px + 5}" y="112" width="6" height="3" fill="{f}"/><rect x="{px + 10}" y="100" width="22" '
          f'height="38" rx="4" fill="{f}"/><rect x="{px + 14}" y="95" width="3" height="5" fill="{f}"/>'
          f'<rect x="{px + 24}" y="95" width="3" height="5" fill="{f}"/>',
          ''.join(f'<path d="M{px + (6 if k % 2 else -6)} {y}h{6 if k % 2 else -6}" stroke="{f}" stroke-width="2"/>'
                  for k, y in enumerate(range(150, 330, 16))))
    placa = [f'<rect x="{px - 11}" y="170" width="22" height="100" rx="1.5" fill="{t["placa"]}"/>',
             f'<path d="M{px - 13} 176h26M{px - 13} 264h26" stroke="{f}" stroke-width="1.5"/>']
    for k, ch in enumerate('ワイヤード'):
        y = 192 + k * 17.5
        giro = f' transform="rotate(90 {px} {n(y - 5.5)})"' if ch == 'ー' else ''
        placa.append(s.texto(ch, 'dot', px, y, 14, t['placa_txt'], ancora='middle', extra=giro))
    s.add(*placa)

    # título: um único glitch na entrada; depois, só os fios zumbem
    tx = 56
    s.add(s.texto('serial experiments', 'dot', tx, 86, 16, t['texto2']))
    s.add(s.texto('3hic', 'minb', tx - 6, 208, 140, t['vermelho'], cls='g1'),
          s.texto('3hic', 'minb', tx - 6, 208, 140, t['texto2'], cls='g2'),
          s.texto('3hic', 'minb', tx - 6, 208, 140, t['texto'], cls='g0'))
    frase = 'present day, present time.'
    s.add(s.texto(frase, 'min', tx + 2, 250, 25, t['texto'], cls='pd'))
    s.add(s.texto('hahahaha', 'dot', tx + 2 + medir(frase, 'min', 25) + 16, 250, 16, t['vermelho'], cls='ha'))
    s.css.append(
        '.g0{animation:g0 .9s steps(1,end) .25s both}.g1,.g2{opacity:0}'
        '.g1{animation:g1 .9s steps(1,end) .25s both}.g2{animation:g2 .9s steps(1,end) .25s both}'
        '@keyframes g0{0%{opacity:0}15%{opacity:1;transform:translate(4px,0)}30%{transform:translate(-3px,0)}'
        '45%{opacity:.35;transform:none}60%,100%{opacity:1}}'
        '@keyframes g1{0%{opacity:.9;transform:translate(-9px,2px)}20%{transform:translate(6px,-1px)}'
        '40%{transform:translate(-4px,0)}60%{opacity:.7;transform:translate(3px,0)}80%,100%{opacity:0;transform:none}}'
        '@keyframes g2{0%{opacity:.8;transform:translate(9px,-2px)}20%{transform:translate(-6px,1px)}'
        '40%{transform:translate(4px,0)}60%{opacity:.6;transform:translate(-3px,0)}80%,100%{opacity:0;transform:none}}'
        '.pd{animation:aparece .8s ease-out 1.1s both}@keyframes aparece{from{opacity:0}to{opacity:1}}'
        '.ha{opacity:.8;animation:riso 1.4s steps(1,end) 1.9s both}'
        '@keyframes riso{0%{opacity:0}10%{opacity:1}20%{opacity:0}32%{opacity:1}44%{opacity:.15}58%{opacity:1}'
        '100%{opacity:.8}}')
    textura(s, t, W, H)
    return s


# ---------------------------------------------------------------- NAVI: fastfetch no Copland OS

CLAWD = [  # o bonequinho do Claude Code, do jeito que aparece no terminal: a NAVI do 3hic
    ' ▐▛███▜▌',
    '▝▜█████▛▘',
    '  ▘▘ ▝▝',
]
QUADRANTES = {' ': '', '█': 'abcd', '▌': 'ac', '▐': 'bd', '▀': 'ab', '▄': 'cd', '▘': 'a', '▝': 'b', '▖': 'c',
              '▗': 'd', '▛': 'abc', '▜': 'abd', '▙': 'acd', '▟': 'bcd'}   # a b / c d = os 4 quadrantes do bloco
CLAUDE = '#D97757'
FICHA = [  # o que o fastfetch mostra: o "sistema" é a Wired, o resto é o 3hic
    ('OS', 'Copland OS Enterprise'),
    ('Host', 'NAVI (Claude Code)'),
    ('Kernel', 'protocol 7'),
    ('Uptime', 'na wired desde jul. de 2024'),
    ('Shell', 'lisp'),
    ('CPU', 'psyche'),
    ('Linguagens', 'Python, JavaScript'),
    ('Faz', 'bots para Discord, automação'),
    ('Agora', 'automação com IA'),
    ('Lema', 'sempre aprendendo, sempre construindo'),
]


def navi(t):
    W, H = 570, 400      # do lado do GIF quadrado: 40% + 57% da largura, mesma altura
    s = Svg(W, H, 'NAVI: fastfetch no Copland OS',
            'Terminal do NAVI. Digita say -v Whisper "Weird: Layer zero one" e depois fastfetch, que mostra o '
            'bonequinho do Claude Code (claude code, minha navi) e a ficha: '
            + '; '.join(f'{a}: {b}' for a, b in FICHA) + '.')
    janela(s, t, W, H, 'navi', 'copland os enterprise')
    tam, x0 = 14, 22
    cw = tam * .5                      # DotGothic16: toda letra latina mede meia eme
    tt = linhas_digitadas(s, t, ['say -v Whisper "Weird: Layer zero one"', 'fastfetch'], x0, [58, 80], tam, .5)
    # o logo: o Clawd em pixels (cada caractere de bloco vira 2×2 quadrantes, altos como no terminal)
    pix = {(c * 2 + (q in 'bd'), lin * 2 + (q in 'cd'))
           for lin, linha in enumerate(CLAWD) for c, ch in enumerate(linha) for q in QUADRANTES[ch]}
    pw, ph = 9, 18
    largura = (max(x for x, _ in pix) + 1) * pw
    ox, oy = x0 + (24 * cw - largura) / 2, 92
    corridas = []      # junta os pixels vizinhos de cada linha num retângulo só (sem frestas)
    for y in sorted({y for _, y in pix}):
        xs = sorted(x for x, yy in pix if yy == y)
        ini = ant = xs[0]
        for x in xs[1:] + [None]:
            if x != ant + 1:
                corridas.append(f'<rect x="{n(ox + ini * pw)}" y="{oy + y * ph}" width="{(ant - ini + 1) * pw}" '
                                f'height="{ph}"/>')
                ini = x
            ant = x
    olhos = [(x, 1) for x in range(min(x for x, _ in pix), max(x for x, _ in pix)) if (x, 1) not in pix
             and (x - 1, 1) in pix and (x + 1, 1) in pix]
    piscar = ''.join(f'<rect class="olho" x="{n(ox + x * pw)}" y="{oy + y * ph}" width="{pw}" height="{ph}"/>'
                     for x, y in olhos)
    s.add(f'<g class="l" fill="{CLAUDE}" style="animation-delay:{tt:.2f}s">{"".join(corridas)}{piscar}</g>',
          s.texto('claude code', 'dot', x0 + 12 * cw, oy + 3 * ph + 58, 13, CLAUDE, ancora='middle', cls='l',
                  extra=f' style="animation-delay:{tt + .1:.2f}s"'),
          s.texto('minha navi ♡', 'dot', x0 + 12 * cw, oy + 3 * ph + 78, 12, t['texto3'], ancora='middle', cls='l',
                  extra=f' style="animation-delay:{tt + .15:.2f}s"'))
    s.css.append('.olho{opacity:0;animation:olho 4.6s steps(1,end) infinite}'
                 '@keyframes olho{0%,92%{opacity:0}93%,96%{opacity:1}97%,100%{opacity:0}}')
    # a ficha ao lado
    xi, lh = x0 + 24 * cw, 18.6
    s.letras['dot'].update('3hic@navi-')
    linhas = [f'<tspan fill="{t["vermelho"]}">3hic</tspan><tspan fill="{t["texto"]}">@</tspan>'
              f'<tspan fill="{t["vermelho"]}">navi</tspan>',
              f'<tspan fill="{t["texto3"]}">---------</tspan>']
    for chave, valor in FICHA:
        s.letras['dot'].update(chave + ': ' + valor)
        cabe(chave + ': ' + valor, 'dot', tam, W - 22 - xi, 'navi')
        linhas.append(f'<tspan fill="{t["texto2"]}">{esc(chave)}:</tspan>'
                      f'<tspan fill="{t["texto"]}" x="{n(xi + (len(chave) + 2) * cw)}">{esc(valor)}</tspan>')
    for i, conteudo in enumerate(linhas):
        s.add(f'<text class="dot l" x="{n(xi)}" y="{n(104 + i * lh)}" font-size="{tam}" '
              f'style="animation-delay:{tt + i * .035:.2f}s">{conteudo}</text>')
    # os blocos de cor do fastfetch
    blocos = [t['borda'], t['texto3'], t['texto2'], t['tela'], t['urso'], LARANJA, t['vermelho'], t['texto']]
    y_bl = 104 + len(linhas) * lh - 6
    s.add(f'<g class="l" style="animation-delay:{tt + len(linhas) * .035:.2f}s">'
          + ''.join(f'<rect x="{n(xi + k * 24)}" y="{n(y_bl)}" width="22" height="12" fill="{c}"/>'
                    for k, c in enumerate(blocos)) + '</g>')
    fim = tt + len(linhas) * .035 + .3
    s.letras['dot'].update('3hic@navi ~ %█')
    s.add(f'<text class="dot l" x="{x0}" y="352" font-size="{tam}" fill="{t["texto3"]}" '
          f'style="animation-delay:{fim:.2f}s">3hic@navi ~ %</text>',
          s.texto('█', 'dot', x0 + 14 * cw, 352, tam, t['vermelho'], cls='cur', extra=f' style="animation-delay:{fim:.2f}s"'),
          f'<path d="M.5 368.5H{W - .5}" stroke="{t["borda"]}"/>',
          f'<circle cx="24" cy="385" r="3.2" fill="{t["vermelho"]}"/>',
          s.texto('conectado à wired', 'dot', 34, 389.5, 13, t['texto3']),
          s.texto('7,83 Hz', 'dot', W - 18, 389.5, 13, t['texto3'], ancora='end'))
    s.css.append(CSS_DIGITACAO)
    return s


# ---------------------------------------------------------------- cartões (cada um cita um Layer do anime)

def cartao(s, t, layer, nome):
    s.add(f'<rect x=".5" y=".5" width="299" height="299" rx="8" fill="{t["sup"]}" stroke="{t["borda"]}"/>',
          s.texto(layer, 'dot', 24, 38, 13, t['texto3']),
          s.texto(nome, 'min', 24 + medir(layer + ' ', 'dot', 13), 38, 15, t['texto2']))


def vida(lado=12, geracoes=48):
    """Jogo da Vida num toro 12×12 com dois gliders (o emblema hacker). Em 48 gerações tudo volta ao início."""
    glider = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
    vivos = {((x + ox) % lado, (y + oy) % lado) for ox, oy in ((0, 0), (6, 0)) for x, y in glider}
    estados = []
    for _ in range(geracoes):
        estados.append(vivos)
        viz = Counter(((x + dx) % lado, (y + dy) % lado) for x, y in vivos
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
        vivos = {c for c, k in viz.items() if k == 3 or (k == 2 and c in vivos)}
    assert vivos == estados[0], 'o padrão não fecha o ciclo'
    return estados


def card_society(t):
    s = Svg(300, 300, 'Layer:07 society: Bot-discord',
            'Bot-discord: moderação, tickets, sorteios, logs e uma sociedade secreta. Python, discord.py e SQLite. '
            'Em cima, dois gliders do Jogo da Vida, o programa que a Lain digita no Layer:07.')
    cartao(s, t, 'Layer:07', 'society')
    lado, passo, cel, bx, by = 12, 9, 7, 168, 26
    s.add(f'<rect x="{bx - 6}" y="{by - 6}" width="{lado * passo + 10}" height="{lado * passo + 10}" rx="4" '
          f'fill="{t["fundo"]}" stroke="{t["borda"]}"/>')
    s.add(f'<g fill="{t["borda"]}">' + ''.join(f'<rect x="{n(bx + i * passo + cel / 2 - 1)}" '
                                                f'y="{n(by + j * passo + cel / 2 - 1)}" width="2" height="2"/>'
                                                for i in range(lado) for j in range(lado)) + '</g>')
    estados = vida(lado)
    dur = len(estados) * .32
    celulas = []
    for i in range(lado):
        for j in range(lado):
            vals = ['1' if (i, j) in e else '0' for e in estados]
            if '1' in vals:
                celulas.append(f'<rect x="{bx + i * passo}" y="{by + j * passo}" width="{cel}" height="{cel}" rx="1" '
                               f'opacity="{vals[0]}"><animate attributeName="opacity" values="{";".join(vals)}" '
                               f'dur="{n(dur)}s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    s.add(f'<g fill="{t["texto2"]}">{"".join(celulas)}</g>')
    linhas = [('Bot-discord', 'minb', 180, 27, t['texto']),
              ('moderação, tickets, sorteios, logs', 'min', 207, 14.5, t['texto2']),
              ('e uma sociedade secreta.', 'min', 227, 14.5, t['texto2']),
              ("'(python discord.py sqlite)", 'dot', 255, 13, t['texto3']),
              ('github.com/3hic/Bot-discord', 'dot', 279, 13, t['texto2'])]
    for txt, fonte, y, tam, cor in linhas:
        cabe(txt, fonte, tam, 252, 'society')
        s.add(s.texto(txt, fonte, 24, y, tam, cor))
    return s


def card_protocol(t):
    itens = [('python', 'bots e automação'), ('javascript', 'scripts no navegador'), ('electron', 'apps de desktop'),
             ('sqlite', 'dados dos bots'), ('discord', 'comunidades'), ('git', 'versões')]
    s = Svg(300, 300, 'Layer:09 protocol: stack',
            'A stack desenhada como camadas de protocolo: ' + '; '.join(f'{a} ({b})' for a, b in itens) + '.')
    cartao(s, t, 'Layer:09', 'protocol')
    s.add(s.texto('stack', 'minb', 24, 80, 27, t['texto']))
    for i, (nome, desc) in enumerate(itens):
        y = 96 + i * 29
        cabe(nome + '  ' + desc, 'min', 12.5, 230, 'protocol')
        s.add(f'<rect x="28" y="{y + 4}" width="248" height="24" rx="3" fill="{t["borda"]}"/>',
              f'<rect x="24" y="{y}" width="248" height="24" rx="3" fill="{t["fundo"]}" stroke="{t["borda"]}"/>',
              s.texto(nome, 'dot', 36, y + 16.5, 14, t['texto']),
              s.texto(desc, 'min', 260, y + 16.5, 12.5, t['texto3'], ancora='end'))
    return s


def card_psyche(t):
    s = Svg(300, 300, 'Layer:03 psyche: agora',
            'Agora: automação com IA, com Python, OCR e Selenium. Em cima, o chip Psyche, que no anime turbina o NAVI.')
    cartao(s, t, 'Layer:03', 'psyche')
    cx, cy, lado = 196, 24, 72
    pinos = []
    for k in range(6):
        p = 9 + k * 10.8
        pinos += [f'<rect x="{n(cx + p - 1.2)}" y="{cy - 7}" width="2.4" height="7"/>',
                  f'<rect x="{n(cx + p - 1.2)}" y="{cy + lado}" width="2.4" height="7"/>',
                  f'<rect x="{cx - 7}" y="{n(cy + p - 1.2)}" width="7" height="2.4"/>',
                  f'<rect x="{cx + lado}" y="{n(cy + p - 1.2)}" width="7" height="2.4"/>']
    s.add(f'<g fill="{t["texto3"]}">{"".join(pinos)}</g>',
          f'<rect x="{cx}" y="{cy}" width="{lado}" height="{lado}" rx="5" fill="{t["fundo"]}" stroke="{t["texto3"]}" '
          'stroke-width="1.2"/>',
          f'<rect x="{cx + 13}" y="{cy + 13}" width="{lado - 26}" height="{lado - 26}" rx="2" fill="none" '
          f'stroke="{t["borda"]}"/>',
          f'<circle cx="{cx + 8}" cy="{cy + 8}" r="2.2" fill="{t["borda"]}"/>',
          s.texto('psyche', 'dot', cx + lado / 2, cy + 40.5, 12, t['texto2'], ancora='middle'),
          f'<circle class="led" cx="{cx + lado - 8}" cy="{cy + lado - 8}" r="2.6" fill="{t["vermelho"]}"/>')
    s.css.append('.led{animation:led 2.4s ease-in-out infinite}@keyframes led{50%{opacity:.25}}')
    for txt, fonte, y, tam, cor in [('agora', 'min', 146, 15, t['texto2']), ('automação', 'minb', 190, 33, t['texto']),
                                    ('com IA', 'minb', 230, 33, t['texto']),
                                    ("'(python ocr selenium)", 'dot', 272, 13, t['texto3'])]:
        cabe(txt, fonte, tam, 252, 'psyche')
        s.add(s.texto(txt, fonte, 24, y, tam, cor))
    return s


# ---------------------------------------------------------------- mail: a caixa de entrada da Lain na Wired

CAIXA = [  # remetente, assunto, data (as datas são as estreias dos Layers 01 a 06)
    ('chisa yomoda', '(sem assunto)', '06 jul'),
    ('knights', 'a verdade única', '13 jul'),
    ('tachibana labs', 'protocol 7: atualização', '20 jul'),
    ('alice mizuki', 'vamos na cyberia hoje?', '27 jul'),
    ('masami eiri', 'a wired é a realidade', '03 ago'),
    ('navi', 'psyche instalado com sucesso', '10 ago'),
]
MENSAGEM = ['lain,', 'eu não morri.', 'só deixei o meu corpo para trás.', 'aqui na wired todo mundo está conectado.']
FRASE_GLITCH = 'deus está aqui.'


def mail(t):
    W, H = 900, 330
    s = Svg(W, H, 'mail: a caixa de entrada da Lain na Wired',
            'O programa de e-mail do NAVI. Na caixa: ' + '; '.join(f'{a}, "{b}", {c}' for a, b, c in CAIXA)
            + '. Aberta, a mensagem da Chisa: ' + ' '.join(MENSAGEM) + ' ' + FRASE_GLITCH)
    janela(s, t, W, H, 'mail', 'copland os enterprise')
    lw, rh = 318, 49
    for i, (de, assunto, data) in enumerate(CAIXA):
        y = 33 + i * rh
        if i == 0:      # a mensagem aberta
            s.add(f'<rect x="1" y="{y}" width="{lw - 1}" height="{rh}" fill="{t["sup"]}"/>',
                  f'<rect x="1" y="{y}" width="3" height="{rh}" fill="{t["vermelho"]}"/>',
                  f'<circle cx="21" cy="{y + 18}" r="3.2" fill="{t["vermelho"]}"/>')
        s.add(s.texto(de, 'dot', 32, y + 22, 13, t['texto'] if i == 0 else t['texto2']),
              s.texto(data, 'dot', lw - 16, y + 22, 11, t['texto3'], ancora='end'),
              s.texto(assunto, 'min', 32, y + 40, 13.5, t['texto2'] if i == 0 else t['texto3']))
        cabe(assunto, 'min', 13.5, lw - 48, 'mail')
        if i:
            s.add(f'<path d="M1 {y + .5}H{lw}" stroke="{t["borda"]}" stroke-opacity=".6"/>')
    s.add(f'<path d="M{lw + .5} 33V{H - .5}" stroke="{t["borda"]}"/>')
    x = lw + 26
    for k, (rotulo, valor) in enumerate([('de', 'chisa yomoda'), ('para', 'lain iwakura'), ('assunto', '(sem assunto)')]):
        y = 62 + k * 21
        s.add(s.texto(rotulo, 'dot', x, y, 12, t['texto3']), s.texto(valor, 'dot', x + 66, y, 13, t['texto']))
    s.add(s.texto('06 jul 1998, 23:47', 'dot', W - 22, 62, 12, t['texto3'], ancora='end'),
          f'<path d="M{lw + 1} 118.5H{W - 1}" stroke="{t["borda"]}"/>')
    for k, linha in enumerate(MENSAGEM):
        cabe(linha, 'min', 19, W - x - 26, 'mail')
        s.add(s.texto(linha, 'min', x, 158 + k * 33, 19, t['texto']))
    yg = 158 + len(MENSAGEM) * 33
    s.add(s.texto(FRASE_GLITCH, 'min', x, yg, 19, t['vermelho'], cls='m1'),
          s.texto(FRASE_GLITCH, 'min', x, yg, 19, t['tela'], cls='m2'),
          s.texto(FRASE_GLITCH, 'min', x, yg, 19, t['texto'], cls='m0'))
    s.css.append(  # a última frase falha de vez em quando, como se a Wired interferisse
        '.m1,.m2{opacity:0}.m0,.m1,.m2{animation-duration:7s;animation-iteration-count:infinite;'
        'animation-timing-function:steps(1,end)}.m0{animation-name:m0}.m1{animation-name:m1}.m2{animation-name:m2}'
        '@keyframes m0{0%,90%{transform:none;opacity:1}91%{transform:translate(3px,0);opacity:.6}'
        '93%{transform:translate(-2px,0);opacity:1}95%,100%{transform:none}}'
        '@keyframes m1{0%,90%{opacity:0}91%{opacity:.9;transform:translate(-5px,1px)}93%{transform:translate(4px,0)}'
        '95%,100%{opacity:0;transform:none}}'
        '@keyframes m2{0%,90%{opacity:0}91%{opacity:.8;transform:translate(5px,-1px)}93%{transform:translate(-4px,0)}'
        '95%,100%{opacity:0;transform:none}}')
    return s


# ---------------------------------------------------------------- sobre.lisp (o HandiNAVI roda Lisp)

CODIGO = [
    [(';; o HandiNAVI da Lain roda Lisp (Layer:07)', 'com')],
    [('(', 'p'), ('defparameter', 'kw'), (' ', 'p'), ('*3hic*', 'var')],
    [("  '((", 'p'), ('linguagem', 'sym'), (' . ', 'p'), ('"Python"', 'str'), (')', 'p')],
    [('    (', 'p'), ('banco', 'sym'), ('     . ', 'p'), ('"SQLite3"', 'str'), (')', 'p')],
    [('    (', 'p'), ('faz', 'sym'), ('       . ', 'p'), ('"bots para Discord"', 'str'), (')', 'p')],
    [('    (', 'p'), ('agora', 'sym'), ('     . ', 'p'), ('"automação com IA"', 'str'), (')))', 'p')],
    [],
    [('(', 'p'), ('loop', 'kw'), (' ', 'p'), ('for', 'kw'), (' (', 'p'), ('chave', 'sym'), (' . ', 'p'),
     ('valor', 'sym'), (') ', 'p'), ('in', 'kw'), (' ', 'p'), ('*3hic*', 'var')],
    [('      ', 'p'), ('do', 'kw'), (' (', 'p'), ('format', 'kw'), (' ', 'p'), ('t', 'sym'), (' ', 'p'),
     ('"~(~9@a~) › ~a~%"', 'str'), (' ', 'p'), ('chave', 'sym'), (' ', 'p'), ('valor', 'sym'), ('))', 'p')],
]
REPL = [  # o que o SBCL imprime ao carregar o arquivo acima
    [('* ', 'p'), ('(load ', 'sym'), ('"sobre.lisp"', 'str'), (')', 'sym')],
    [('linguagem', 'kw'), (' › ', 'p'), ('Python', 'sym')],
    [('    banco', 'kw'), (' › ', 'p'), ('SQLite3', 'sym')],
    [('      faz', 'kw'), (' › ', 'p'), ('bots para Discord', 'sym')],
    [('    agora', 'kw'), (' › ', 'p'), ('automação com IA', 'sym')],
    [('T', 'p')],
]


def linha_lisp(s, cores, tokens, x0, y, tam):
    cw, col, spans = tam * .5, 0, []
    for txt, tipo in tokens:
        for m in re.finditer(r'\S+', txt):
            spans.append(f'<tspan x="{n(x0 + (col + m.start()) * cw)}" fill="{cores[tipo]}">{esc(m.group())}</tspan>')
        col += len(txt)
        s.letras['dot'].update(txt)
    if spans:
        s.add(f'<text class="dot" y="{y}" font-size="{tam}">{"".join(spans)}</text>')


def sobre(t):
    W, H = 900, 300
    s = Svg(W, H, 'sobre.lisp',
            'Um sobre mim em Common Lisp, a linguagem do HandiNAVI da Lain. Ao carregar no SBCL imprime: '
            'linguagem: Python; banco: SQLite3; faz: bots para Discord; agora: automação com IA.')
    janela(s, t, W, H, 'sobre.lisp', 'sbcl')
    cores = {'com': t['texto3'], 'p': t['texto3'], 'kw': t['texto2'], 'var': t['vermelho'], 'sym': t['texto'],
             'str': t['urso']}
    tam, y0, lh = 15, 74, 24
    for i, tokens in enumerate(CODIGO):
        s.add(s.texto(str(i + 1), 'dot', 40, y0 + i * lh, 13, t['texto3'], ancora='end'))
        linha_lisp(s, cores, tokens, 58, y0 + i * lh, tam)
    s.add(f'<path d="M560.5 33V{H - .5}" stroke="{t["borda"]}"/>')
    for i, tokens in enumerate(REPL):
        linha_lisp(s, cores, tokens, 588, y0 + i * lh, tam)
    return s


# ---------------------------------------------------------------- player: Duvet, a abertura (link no README)

MUSICA = dict(titulo='duvet', legenda='bôa, a abertura de serial experiments lain', duracao=203.6, tempo='3:23')


def player(t):
    W, H = 640, 156
    s = Svg(W, H, 'tocando: Duvet, de bôa',
            'Player do Copland OS tocando Duvet, da banda bôa, a abertura de Serial Experiments Lain (3:23). '
            'A imagem é um link para ouvir no Spotify.')
    janela(s, t, W, H, 'player', 'spotify')
    # capa: um pedaço do céu do hero (fios, poste e as manchas vermelhas)
    cx, cy, lado = 22, 50, 88
    s.defs.append(f'<clipPath id="capa"><rect x="{cx}" y="{cy}" width="{lado}" height="{lado}" rx="4"/></clipPath>'
                  f'<linearGradient id="ceuCapa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["ceu1"]}"/>'
                  f'<stop offset=".6" stop-color="{t["ceu2"]}"/><stop offset="1" stop-color="{t["ceu3"]}"/></linearGradient>')
    px, f = cx + 66, t['fio']
    capa = [f'<rect x="{cx}" y="{cy}" width="{lado}" height="{lado}" fill="url(#ceuCapa)"/>',
            fio(catenaria(cx - 4, cy + 10, px - 9, cy + 20, 9), f, 1.2),
            fio(catenaria(cx - 4, cy + 18, px + 9, cy + 20, 11), f, 1.2),
            fio(catenaria(px - 9, cy + 20, cx + lado + 4, cy + 26, 3), f, 1.2),
            f'<path d="M{px - 1.6} {cy + 12}h3.2l1 {lado - 12}h-5.2Z" fill="{f}"/>',
            f'<rect x="{px - 13}" y="{cy + 20}" width="26" height="2.4" fill="{f}"/>',
            f'<path d="M{cx} {cy + lado}V{cy + 72}h20v-6h18v10h22v-4h28V{cy + lado}Z" fill="{t["chao"]}"/>']
    rnd = random.Random(7)
    capa += [f'<circle cx="{n(rnd.uniform(cx + 4, cx + lado - 4))}" cy="{n(rnd.uniform(cy + 78, cy + lado - 3))}" '
             f'r="{n(rnd.uniform(.6, 1.6))}" fill="{t["vermelho"]}"/>' for _ in range(14)]
    s.add(f'<g clip-path="url(#capa)">{"".join(capa)}</g>',
          # botão de play na capa: a imagem toda é o link para ouvir
          f'<circle cx="{cx + lado - 17}" cy="{cy + lado - 17}" r="13" fill="{t["texto"]}"/>'
          f'<path d="M{cx + lado - 21} {cy + lado - 24}l12 7-12 7Z" fill="{t["fundo"]}"/>')
    tx = cx + lado + 22
    s.add(s.texto(MUSICA['titulo'], 'minb', tx, 86, 30, t['texto']),
          s.texto(MUSICA['legenda'], 'min', tx, 109, 14, t['texto2']))
    barras = ''.join(f'<rect class="eq" x="{W - 76 + i * 9}" y="62" width="5" height="24" rx="1" fill="{t["texto2"]}" '
                     f'style="animation-duration:{.55 + (i * 37 % 7) / 10:.2f}s;animation-delay:-{i * .23:.2f}s"/>'
                     for i in range(6))
    s.add(barras)
    bw = W - 22 - tx    # barra de progresso: anda no tempo real da música
    s.add(f'<rect x="{tx}" y="125" width="{bw}" height="3" rx="1.5" fill="{t["borda"]}"/>',
          f'<rect class="prog" x="{tx}" y="125" width="{bw}" height="3" rx="1.5" fill="{t["vermelho"]}"/>',
          s.texto('clique para ouvir no spotify', 'dot', tx, 147, 12, t['texto2']),
          s.texto(MUSICA['tempo'], 'dot', W - 22, 147, 12, t['texto3'], ancora='end'))
    s.css.append('.eq{transform-box:fill-box;transform-origin:50% 100%;animation:eq .8s ease-in-out infinite alternate}'
                 '@keyframes eq{from{transform:scaleY(.22)}to{transform:scaleY(1)}}'
                 '.prog{transform-box:fill-box;transform-origin:0 50%;animation:prog ' + n(MUSICA['duracao'])
                 + 's linear infinite}@keyframes prog{from{transform:scaleX(.06)}to{transform:scaleX(1)}}')
    return s


# ---------------------------------------------------------------- rodapé: fecha com o mesmo céu do topo

def rodape(t):
    W, H = 900, 160
    s = Svg(W, H, "no matter where you go, everyone's connected.",
            "A frase da Lain no Layer:02, sob o céu da Wired, com um fio atravessando e um ponto vermelho correndo por ele.")
    ceu(s, t, W, H)
    d1, d2 = catenaria(-20, 26, 920, 14, 22), catenaria(-20, 38, 920, 28, 24)
    s.add(fio(d2, t['fio'], 1.2), fio(d1, t['fio'], 1.6),
          f'<circle r="3.2" fill="{t["vermelho"]}"><animateMotion dur="9s" repeatCount="indefinite" path="{d1}"/>'
          '</circle>',
          s.texto('no matter where you go, everyone’s connected.', 'min', W / 2, 104, 27, t['texto'], ancora='middle'),
          s.texto('lain, layer:02', 'dot', W / 2, 134, 14, t['texto2'], ancora='middle'))
    textura(s, t, W, H)
    return s


PECAS = {'wired-hero': hero, 'navi': navi, 'card-society': card_society, 'card-protocol': card_protocol,
         'card-psyche': card_psyche, 'mail': mail, 'sobre-lisp': sobre, 'player': player, 'rodape': rodape}

if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    for nome, fazer in PECAS.items():
        caminho = ASSETS / f'{nome}.svg'
        tamanho = fazer(TEMA).salvar(caminho)
        print(f'{caminho.name}: {tamanho / 1024:.0f} KB')
