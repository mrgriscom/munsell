import re
import math
import bisect
from colormath.color_objects import xyYColor, XYZColor, LabColor, sRGBColor
from colormath.color_conversions import convert_color

EPSILON = 1e-6

HUE_RES = 9.
CHROMA_RES = 2.

LUT = {}
lums = {}

def parse_hue(s):
    sector = re.search('[A-Z]+', s).group(0).lower()
    num = float(s[:-len(sector)])
    sectors = ['r', 'yr', 'y', 'gy', 'g', 'bg', 'b', 'pb', 'p', 'rp']
    return (.1 * sectors.index(sector) + .01 * (num - 5)) % 1.

def toLab(x, y, Y):
    color = convert_color(xyYColor(x, y, Y, illuminant='C'), XYZColor)
    color.apply_adaptation('D65')
    return convert_color(color, LabColor)

def parse_line(ln):
    pcs = ln.strip().split()

    h = int(360.*parse_hue(pcs[0]) + EPSILON)
    v = int(10.*float(pcs[1]) + EPSILON)
    c = int(pcs[2])
    x = float(pcs[3])
    y = max(float(pcs[4]), EPSILON)
    Y = float(pcs[5])/100.

    lums[v] = Y
    return ((h, v, c), toLab(x, y, Y))

def init():
    data = open('all.dat').readlines()[1:]
    for ln in data:
        muns, lab = parse_line(ln)
        LUT[muns] = lab

    global lums
    lums[0] = 0
    whitepoint = convert_color(LabColor(100., 0., 0., illuminant='C'), xyYColor)
    for lm, ll in sorted(lums.iteritems()):
        LUT[(0, lm, 0)] = toLab(whitepoint.xyy_x, whitepoint.xyy_y, ll)

    lums = sorted(lums.keys())

def mix(k, a, b):
    return (1-k)*a + k*b

def mixv(k, va, vb):
    return [mix(k, a, b) for a, b in zip(va, vb)]

def convert(h, v, c):
    h = float(h)
    v = float(v)
    c = float(c)
    h = h % 360.

    h0 = math.floor(h / HUE_RES) * HUE_RES
    h1 = (h0 + HUE_RES) % 360.
    v0ix = min(bisect.bisect_right(lums, v) - 1, len(lums) - 2)
    v0 = lums[v0ix]
    v1 = lums[v0ix+1]
    c0 = math.floor(c / CHROMA_RES) * CHROMA_RES
    c1 = c0 + 2

    kh = (h - h0) / HUE_RES
    kv = (v - v0) / (v1 - v0)
    kc = (c - c0) / CHROMA_RES

    def lookup(h, v, c):
        return LUT[(h if c > 0 else 0, v, c)].get_value_tuple()
    def interp_for_hue(h):
        def _interp(p0, px0, px1, py0, py1):
            def getp(i):
                return lookup(h, v0 if i < 2 else v1, c0 if i % 2 == 0 else c1)
            def calc(f):
                dx = f[2] - f[1]
                dy = f[4] - f[3]
                offset = 1 if p0 == 3 else 0
                return f[0] + (kc-offset)*dx + (kv-offset)*dy
            return [calc(f) for f in zip(*(getp(i) for i in (p0, px0, px1, py0, py1)))]

        if c < .5:
            if kv > kc:
                return _interp(0, 2, 3, 0, 2)
            else:
                return _interp(0, 0, 1, 1, 3)
        else:
            if kv > 1 - kc:
                return _interp(3, 2, 3, 1, 3)
            else:
                return _interp(0, 0, 1, 0, 2)

    try:
        result = mixv(kh, interp_for_hue(h0), interp_for_hue(h1))
    except (KeyError, ValueError, TypeError):
        return None

    return convert_color(LabColor(*result), sRGBColor).get_value_tuple()

def munsell(h, l, c):
    return convert(360.*h, 100.*l, 20.*c)

def in_gamut(c):
    return c is not None and all(k >= 0. and k < 1. for k in c)

def solve(func, min, max, res):
    if not func(min):
        return min
    elif func(max):
        return max
    while True:
        x = .5 * (min + max)
        if abs(max - min) <= res:
            return x
        if func(x):
            min = x
        else:
            max = x

def lum_limits(hue, chroma):
    return [solve(lambda x: in_gamut(munsell(hue, x, chroma)), .5, extreme, EPSILON) for extreme in (0., 1.)]

def chroma_limit(hue, lum):
    return solve(lambda x: in_gamut(munsell(hue, lum, x)), 0, 50, EPSILON) - EPSILON

def rgb_to_hex(rgb):
    return [min(max(int(256.*k), 0), 255) for k in rgb]

def write_card(func, pathout):
    W = 100
    H = 100

    import tempfile
    tmpraw = tempfile.mktemp()

    with open(tmpraw, 'w') as f:
        for i in range(H):
            y = (H-.5-i)/H
            for j in range(W):
                x = (j+.5)/W
                color = munsell(*func(x, y))
                if not in_gamut(color):
                    color = (.5, .5, .5)
                f.write(''.join(chr(k) for k in rgb_to_hex(color)))
    import os
    os.popen('convert -size %dx%d -depth 8 rgb:%s %s.png' % (W, H, tmpraw, pathout))


if __name__ == "__main__":

    init()
    for hue in range(0, 360, 5):
        write_card(lambda x, y: (hue / 360., y, x), '~/tmp/munsell/clh%03d' % hue)
    for chroma in range(0, 126):
        write_card(lambda x, y: (x, y, .01*chroma), '~/tmp/munsell/hlc%03d' % chroma)
