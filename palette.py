import math
from grapefruit import Color

MIN = -500
MAX = 9000
CYCLE = 500

import munsell as m
m.init()

def color(elev):
    HUE0_ABOVE = .08
    HUE0_BELOW = .71
    SATMIN = .05
    SATMAX = .6

    ka = float(elev) / (MAX - MIN)
    kb = (float(elev) / CYCLE) % 1. # no phase change needed for below sea level,
                                    # as change in hue and lummin is apparent enough

    kval = 1 - abs(1 - 2 * kb)
    ksat = abs(math.sin(2*math.pi*kb))

    hue = ka + (HUE0_ABOVE if elev > 0 else HUE0_BELOW)
    lummin, lummax = m.lum_limits(hue, SATMIN)
    val = m.mix(kval, lummin, lummax)
    satmax = m.mix(ksat, SATMIN, SATMAX)
    satmax = min(satmax, m.chroma_limit(hue, val))
    sat = m.mix(1. if kb < .5 else .3333, SATMIN, satmax)

    return m.munsell(hue, val, sat)
    
def print_step(elev):
    print elev, ' '.join(str(k) for k in m.rgb_to_hex(color(elev)))

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
        data.extend(chr(k) for k in m.rgb_to_hex(color(elev)))
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

palette()
#legend()
