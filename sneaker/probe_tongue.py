"""Check the tongue hugs the shell wall without poking through."""
import numpy as np
from shoe import LAST, up_shape, smoothstep

bad = 0
for a in np.linspace(0.0, 1.0, 61):
    u = 0.437 + (0.862 - 0.437) * a
    zr = LAST.zrim(u)
    drop = 0.0110 * float(smoothstep(0.80, 1.0, a))
    for b in (-1.0, -0.5, 0.0, 0.5, 1.0):
        z = zr - 0.0055 - drop - 0.0075 * (abs(b) ** 2.2)
        w = LAST.wup(u) * float(up_shape(LAST.s_for_z(u, z))) - 0.0008
        x = abs(b) * w
        # shell outer wall at that height
        xw = LAST.wup(u) * float(up_shape(LAST.s_for_z(u, z)))
        inner = xw - 0.0022
        flag = ""
        if x > xw:
            flag = "  POKES OUT"
            bad += 1
        elif x < inner - 0.0005 and abs(b) > 0.99:
            flag = "  gap"
        # is the tongue below the rim (never above)?
        if z > zr:
            flag += "  ABOVE RIM"
            bad += 1
        print("u=%.3f b=%+0.1f  z=%6.2f  x=%6.2f  wall=%6.2f inner=%6.2f%s" %
              (u, b, z * 1000, x * 1000, xw * 1000, inner * 1000, flag))
print("problems:", bad)
