import re
import math
from colormath.color_objects import xyYColor, XYZColor, LabColor, sRGBColor
from colormath.color_conversions import convert_color

EPSILON = 1e-6

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
    h0 = math.floor(h / 9.) * 9.
    v0 = [k for k in lums if k <= v and k < 100][-1]
    c0 = math.floor(c / 2.) * 2.
    h1 = (h0 + 9.) % 360.
    v1 = lums[lums.index(v0)+1]
    c1 = c0 + 2

    kh = (h - h0) / 9.
    kv = (v - v0) / (v1 - v0)
    kc = (c - c0) / 2.

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
