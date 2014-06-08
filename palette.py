import math
from grapefruit import Color

MIN = -500
MAX = 9000
CYCLE = 500

HUE_RED = (lambda c: math.atan2(c[2], c[1]))(Color.NewFromRgb(1., 0., 0.).lab)
def hlc_to_rgb(h, l, c):
    theta = 2*math.pi*h + HUE_RED
    return Color.NewFromLab(
        100. * l,
        c * math.cos(theta),
        c * math.sin(theta)
    ).rgb

def rgb_to_hex(rgb):
    return [min(max(int(256.*k), 0), 255) for k in rgb]

def in_gamut(c):
    return all(k >= 0. and k < 1. for k in c)

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

def mix(k, min, max):
    return (1-k)*min + k*max

def color(elev):
    ka = float(elev) / (MAX - MIN)
    kb = (float(elev) / CYCLE) % 1. # no phase change needed for below sea level,
                                    # as change in hue and lummin is apparent enough

    kval = 1 - abs(1 - 2 * kb)
    ksat = abs(math.sin(2*math.pi*kb))

    HUE0_ABOVE = .08
    HUE0_BELOW = .7
    SATMIN = .05
    SATMAX = .6

    hue = ka + (HUE0_ABOVE if elev > 0 else HUE0_BELOW)
    lummax = solve(lambda x: in_gamut(hlc_to_rgb(hue, x, SATMIN)), .5, 1., 1e-4)
    lummin = solve(lambda x: in_gamut(hlc_to_rgb(hue, x, SATMIN)), .5, 0., 1e-4)
    val = mix(kval, lummin, lummax)
    satmax = mix(ksat, SATMIN, SATMAX)
    satmax = min(satmax, solve(lambda x: in_gamut(hlc_to_rgb(hue, val, x)), SATMIN, satmax, .0001))
    sat = mix(1. if kb < .5 else .3333, SATMIN, satmax)

    return hlc_to_rgb(hue, val, sat)
    
def print_step(elev):
    print elev, ' '.join(str(k) for k in rgb_to_hex(color(elev)))

def palette():
    STEP = float(CYCLE) / 200
    for i in range(int(math.floor(MIN / STEP)), 1):
        print_step(i * STEP)
    print_step(.001)
    for i in range(1, int(math.ceil(MAX / STEP)) + 1):
        print_step(i * STEP)

def legend():
    W = 1200
    H = 50
    data = []
    for i in range(W):
        elev = MIN + (i + .5)/W * (MAX - MIN)
        data.extend(chr(k) for k in rgb_to_hex(color(elev)))
    line = ''.join(data)

    import tempfile
    import os
    tmpraw = tempfile.mktemp()
    tmpout = tempfile.mktemp()
    with open(tmpraw, 'w') as f:
        for i in range(H):
            f.write(line)
    os.popen('convert -size %dx%d -depth 8 rgb:%s png:%s' % (W, H, tmpraw, tmpout))
    print open(tmpout).read()

#palette()
legend()
