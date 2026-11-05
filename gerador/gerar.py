"""Gera os SVGs do perfil 3hic no tema Serial Experiments Lain.

Duas camadas, como no anime: o tema claro é o mundo real (o dia estourado de branco, postes e
fios zumbindo) e o escuro é a Wired (o quarto da Lain à noite). Cada SVG leva embutidas só as
letras que usa, porque imagem no README do GitHub não carrega nada de fora:
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

TEMAS = {
    # a Wired: o quarto da Lain à noite (índigo, lavanda do GIF, creme da pele)
    'escuro': dict(ceu1='#1A1836', ceu2='#25214B', ceu3='#4A2A55', chao='#0A0918', fio='#06050E',
                   fundo='#14122B', sup='#1C1A38', borda='#34305C', texto='#EFE9DC', texto2='#ABA6DA',
                   texto3='#6F6B9C', vermelho='#E0304E', urso='#D9C3A0', tela='#C9DCFF',
                   placa='#EFE9DC', placa_txt='#14122B', grao='.16', scan=True, janelas=True),
    # o mundo real: céu estourado de branco, fios e sombras em tinta (com as manchas vermelhas)
    'claro': dict(ceu1='#F3F3F6', ceu2='#E9E8EF', ceu3='#D8D2E6', chao='#191628', fio='#191628',
                  fundo='#EEEDF2', sup='#F7F6FA', borda='#CFCBDC', texto='#191628', texto2='#5F5A8A',
                  texto3='#8F8AAE', vermelho='#C8243F', urso='#7A5536', tela='#2E2A55',
                  placa='#191628', placa_txt='#EEEDF2', grao='.12', scan=False, janelas=False),
}
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


# ---------------------------------------------------------------- hero: postes e fios

def hero(t):
    W, H = 900, 340
    s = Svg(W, H, 'serial experiments 3hic',
            'Céu com postes e fios elétricos, como na abertura de Serial Experiments Lain. O nome 3hic em letras '
            'grandes, a frase "present day, present time." e uma risada vermelha. Na placa do poste está escrito '
            'ワイヤード (Wired). No chão, as sombras têm manchas vermelhas, como no anime.')
    s.defs.append(f'<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["ceu1"]}"/>'
                  f'<stop offset=".58" stop-color="{t["ceu2"]}"/><stop offset="1" stop-color="{t["ceu3"]}"/>'
                  '</linearGradient>')
    s.defs.append('<filter id="grao" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" '
                  'baseFrequency=".9" numOctaves="2" seed="7" stitchTiles="stitch"/>'
                  '<feColorMatrix values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1.4 -.55"/></filter>')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#ceu)"/>')

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
    if t['janelas']:
        for x, w, topo, _ in predios[1::3]:
            s.add(f'<rect x="{n(x + w * .62)}" y="{topo + 12}" width="5" height="7" fill="{t["tela"]}" '
                  'fill-opacity=".5"/>')
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

    if t['scan']:   # na Wired a imagem é tela: linhas de varredura
        s.defs.append('<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
                      '<rect width="4" height="1" fill="#000" fill-opacity=".22"/></pattern>')
        s.add(f'<rect width="{W}" height="{H}" fill="url(#scan)"/>')
    s.add(f'<rect width="{W}" height="{H}" filter="url(#grao)" opacity="{t["grao"]}"/>')
    return s


# ---------------------------------------------------------------- NAVI: o terminal do Copland OS

def navi(t):
    W, H = 564, 400      # mesma proporção do GIF da Lain (400×284), para ficarem lado a lado
    s = Svg(W, H, 'NAVI, terminal do Copland OS',
            'Um terminal digita say -v Whisper "Weird: Layer zero one" (a voz que anuncia cada episódio); '
            'whoami responde 3hic; cat sobre.txt responde: python, automação e bots para discord. Sempre '
            'aprendendo, sempre construindo. ping -c 1 wired responde: 64 bytes de lain, tempo 7,83 ms.')
    janela(s, t, W, H, 'navi', 'copland os enterprise')
    tam, x0, y0, lh = 16, 22, 70, 28
    cw = tam * .5                      # DotGothic16: toda letra latina mede meia eme
    prompt = '3hic@navi ~ % '
    roteiro = [('cmd', 'say -v Whisper "Weird: Layer zero one"'),
               ('cmd', 'whoami'),
               ('out', '3hic', t['texto']),
               ('cmd', 'cat sobre.txt'),
               ('out', 'python, automação e bots para discord.', t['texto2']),
               ('out', 'sempre aprendendo, sempre construindo.', t['texto2']),
               ('cmd', 'ping -c 1 wired'),
               ('out', '64 bytes de lain: tempo=7,83 ms', t['texto2']),
               ('fim', '')]
    tt = .6
    for i, (tipo, conteudo, *cor) in enumerate(roteiro):
        y = y0 + i * lh
        if tipo == 'out':
            s.add(s.texto(conteudo, 'dot', x0, y, tam, cor[0], cls='l', extra=f' style="animation-delay:{tt:.2f}s"'))
            tt += .14 + (.3 if roteiro[i + 1][0] != 'out' else 0)
            continue
        s.letras['dot'].update(prompt + conteudo)
        partes = [f'<tspan class="p" style="animation-delay:{tt:.2f}s">{esc(prompt.rstrip())}</tspan>']
        t0 = tt + .28
        for k, ch in enumerate(conteudo):
            if ch != ' ':
                partes.append(f'<tspan class="c" x="{n(x0 + (len(prompt) + k) * cw)}" fill="{t["texto"]}" '
                              f'style="animation-delay:{t0 + k * .052:.2f}s">{esc(ch)}</tspan>')
        s.add(f'<text class="dot" x="{x0}" y="{y}" font-size="{tam}" fill="{t["texto3"]}">{"".join(partes)}</text>')
        if tipo == 'cmd':
            tt = t0 + len(conteudo) * .052 + .38
        else:
            s.add(s.texto('█', 'dot', x0 + len(prompt) * cw, y, tam, t['vermelho'], cls='cur',
                          extra=f' style="animation-delay:{tt + .25:.2f}s"'))
    # a ressonância Schumann: 7,83 ciclos cabem na largura da janela
    lam, pts, xx = 520 / 7.83, [], 22.0
    while xx <= 542 + lam + 2:
        pts.append(f'{n(xx)},{n(332 + 7 * math.sin((xx - 22) / lam * 2 * math.pi))}')
        xx += 2
    s.defs.append('<clipPath id="faixa"><rect x="22" y="318" width="520" height="28"/></clipPath>')
    s.add(f'<g clip-path="url(#faixa)"><polyline class="onda" points="{" ".join(pts)}" fill="none" '
          f'stroke="{t["texto3"]}" stroke-width="1.3" stroke-opacity=".75"/></g>',
          f'<path d="M.5 368.5H{W - .5}" stroke="{t["borda"]}"/>',
          f'<circle cx="24" cy="385" r="3.2" fill="{t["vermelho"]}"/>',
          s.texto('conectado à wired', 'dot', 34, 389.5, 13, t['texto3']),
          s.texto('7,83 Hz', 'dot', W - 18, 389.5, 13, t['texto3'], ancora='end'))
    s.css.append('.p,.c{fill-opacity:0;animation:liga .01s steps(1,end) forwards}'
                 '.l{opacity:0;animation:mostra .01s steps(1,end) forwards}'
                 '@keyframes liga{to{fill-opacity:1}}@keyframes mostra{to{opacity:1}}'
                 '.cur{opacity:0;animation:pisca 1.1s steps(1,end) infinite}@keyframes pisca{0%{opacity:1}50%{opacity:0}}'
                 '.onda{animation:onda 2.6s linear infinite}@keyframes onda{to{transform:translateX(-'
                 + n(lam) + 'px)}}')
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


# ---------------------------------------------------------------- rodapé

def rodape(t):
    W, H = 900, 150
    s = Svg(W, H, "no matter where you go, everyone's connected.",
            "A frase da Lain no Layer:02, com um fio atravessando e um ponto vermelho correndo por ele.")
    d1, d2 = catenaria(-20, 30, 920, 16, 24), catenaria(-20, 42, 920, 30, 26)
    s.add(fio(d2, t['texto3'], 1, extra=' stroke-opacity=".45"'), fio(d1, t['texto3'], 1.3),
          f'<circle r="3.2" fill="{t["vermelho"]}"><animateMotion dur="9s" repeatCount="indefinite" path="{d1}"/>'
          '</circle>',
          s.texto('no matter where you go, everyone’s connected.', 'min', W / 2, 98, 26, t['texto'], ancora='middle'),
          s.texto('lain, layer:02', 'dot', W / 2, 128, 14, t['texto3'], ancora='middle'))
    return s


# ---------------------------------------------------------------- refs.txt: o que o perfil cita do anime

LAYERS = ['weird', 'girls', 'psyche', 'religion', 'distortion', 'kids', 'society', 'rumors', 'protocol', 'love',
          'infornography', 'landscape', 'ego']
CITADOS = {1: 'no terminal', 2: 'no rodapé', 3: 'cartão agora', 7: 'cartão Bot-discord', 9: 'cartão stack'}
REFS = [
    ('present day, present time.', 'a narração que abre cada episódio'),
    ('say -v Whisper', 'a voz da Apple que anuncia cada Layer'),
    ('copland os enterprise', 'o sistema do NAVI (o Copland da Apple nunca saiu)'),
    ('tachibana', 'a fabricante do NAVI; tachibana é uma mexerica (a Apple)'),
    ('jogo da vida em lisp', 'o que a Lain digita no HandiNAVI, no Layer:07'),
    ('knights of the eastern calculus', 'a sociedade secreta de hackers da série'),
    ('protocol 7', 'o protocolo de Masami Eiri para fundir os dois mundos'),
    ('7,83 Hz', 'a ressonância Schumann, que liga a Wired ao mundo real'),
    ('psyche', 'o processador que a Lain instala no NAVI'),
    ('pijama de urso', 'o escudo da Lain no mundo real'),
    ('ワイヤード', 'a Wired, a rede da série'),
    ("everyone's connected", 'o que a Lain diz na Cyberia, no Layer:02'),
    ('duvet', 'a abertura, da banda britânica bôa'),
]


def refs(t):
    W, H = 900, 452
    s = Svg(W, H, 'refs.txt: as referências de Serial Experiments Lain neste perfil',
            'Os 13 layers: ' + ', '.join(f'Layer:{i:02d} {n}' for i, n in enumerate(LAYERS, 1))
            + '. Referências: ' + '; '.join(f'{a}: {b}' for a, b in REFS) + '.')
    janela(s, t, W, H, 'refs.txt', 'serial experiments lain, 1998')
    s.add(s.texto('os 13 layers', 'min', 24, 70, 15, t['texto2']),
          s.texto('referências', 'min', 344, 70, 15, t['texto2']),
          f'<path d="M322.5 52V{H - 58}" stroke="{t["borda"]}"/>')
    y0, lh = 102, 24
    for i, nome in enumerate(LAYERS, 1):
        y, citado = y0 + (i - 1) * lh, i in CITADOS
        rotulo = f'Layer:{i:02d}'
        if citado:   # os Layers que aparecem no perfil ganham a mancha vermelha
            s.add(f'<circle cx="28" cy="{y - 4.5}" r="3" fill="{t["vermelho"]}"/>',
                  s.texto(CITADOS[i], 'min', 300, y, 12, t['texto3'], ancora='end'))
        s.add(s.texto(rotulo, 'dot', 40, y, 14, t['texto2'] if citado else t['texto3']),
              s.texto(nome, 'min', 40 + medir(rotulo + ' ', 'dot', 14), y, 14, t['texto'] if citado else t['texto3']))
    for i, (chave, explica) in enumerate(REFS):
        y, wk = y0 + i * lh, medir(chave, 'dot', 14)
        total = wk + 12 + medir(explica, 'min', 13.5)
        if total > 532:
            print(f'  AVISO refs: "{chave}" ocupa {total:.0f}px (cabe 532px)')
        s.add(s.texto(chave, 'dot', 344, y, 14, t['texto']),
              s.texto(explica, 'min', 344 + wk + 12, y, 13.5, t['texto2']))
    creditos = ('13 layers, TV Tokyo, 1998. Direção Ryutaro Nakamura, roteiro Chiaki J. Konaka, '
                'personagens Yoshitoshi ABe, estúdio Triangle Staff.')
    cabe(creditos, 'min', 12.5, 852, 'refs')
    s.add(f'<path d="M.5 {H - 44.5}H{W - .5}" stroke="{t["borda"]}"/>',
          s.texto(creditos, 'min', 24, H - 17, 12.5, t['texto3']))
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
    s.add(f'<g clip-path="url(#capa)">{"".join(capa)}</g>')
    tx = cx + lado + 22
    s.add(s.texto(MUSICA['titulo'], 'minb', tx, 86, 30, t['texto']),
          s.texto(MUSICA['legenda'], 'min', tx, 109, 14, t['texto2']))
    # equalizador
    barras = ''.join(f'<rect class="eq" x="{W - 76 + i * 9}" y="62" width="5" height="24" rx="1" fill="{t["texto2"]}" '
                     f'style="animation-duration:{.55 + (i * 37 % 7) / 10:.2f}s;animation-delay:-{i * .23:.2f}s"/>'
                     for i in range(6))
    s.add(barras)
    # barra de progresso: anda no tempo real da música
    bw = W - 22 - tx
    s.add(f'<rect x="{tx}" y="125" width="{bw}" height="3" rx="1.5" fill="{t["borda"]}"/>',
          f'<rect class="prog" x="{tx}" y="125" width="{bw}" height="3" rx="1.5" fill="{t["vermelho"]}"/>',
          s.texto('ouvir no spotify', 'dot', tx, 147, 12, t['texto2']),
          s.texto(MUSICA['tempo'], 'dot', W - 22, 147, 12, t['texto3'], ancora='end'))
    s.css.append('.eq{transform-box:fill-box;transform-origin:50% 100%;animation:eq .8s ease-in-out infinite alternate}'
                 '@keyframes eq{from{transform:scaleY(.22)}to{transform:scaleY(1)}}'
                 '.prog{transform-box:fill-box;transform-origin:0 50%;animation:prog ' + n(MUSICA['duracao'])
                 + 's linear infinite}@keyframes prog{from{transform:scaleX(.06)}to{transform:scaleX(1)}}')
    return s


PECAS = {'wired-hero': hero, 'navi': navi, 'card-society': card_society, 'card-protocol': card_protocol,
         'card-psyche': card_psyche, 'refs': refs, 'sobre-lisp': sobre, 'player': player, 'rodape': rodape}

if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    for tema, cores_tema in TEMAS.items():
        for nome, fazer in PECAS.items():
            caminho = ASSETS / f'{nome}-{tema}.svg'
            tamanho = fazer(cores_tema).salvar(caminho)
            print(f'{caminho.name}: {tamanho / 1024:.0f} KB')
