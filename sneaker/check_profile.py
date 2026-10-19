"""Numeric sanity check of the profile layer (no mesh, no render)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import shoe
from shoe import LAST

print("LEN = %.4f m   y(0)=%.4f y(1)=%.4f" % (shoe.LEN, LAST.y(0.0), LAST.y(1.0)))
print()
hdr = ("u      y(mm)  WM_eff WUP_eff  s_open  q_lo   zst    zrim    zt    "
       "xrim   zb    sec_h")
print(hdr)
us = np.linspace(0.0, 1.0, 41)
for u in us:
    wm = LAST.wm(u) * 1000
    wup = LAST.wup(u) * 1000
    se = LAST.sopen(u)
    zst = LAST.zst(u) * 1000
    zr = LAST.zrim(u) * 1000
    zt = LAST.zt(u) * 1000
    xr = LAST.xrim(u) * 1000
    zb = LAST.zbupper(u) * 1000
    print("%.3f  %7.1f  %6.1f %6.1f  %6.3f  %.3f  %5.1f  %6.1f %6.1f  %5.1f %6.1f %6.1f"
          % (u, LAST.y(u) * 1000, wm, wup, se, shoe.q_lo(u), zst, zr, zt, xr, zb, zt - zb))

print()
print("checks:")
ok = True
for u, name in ((0.0, 'toe'), (1.0, 'heel')):
    zs = [LAST.zgb(u), LAST.zgb(u) + LAST.trub(u), LAST.zst(u), LAST.zrim(u),
          LAST.zt(u), LAST.zbupper(u)]
    spread = max(zs) - min(zs)
    print("  %s pole: z spread = %.4f mm  (w=%.3f)" %
          (name, spread * 1000, LAST.wup(u)))
    if spread > 1e-6:
        ok = False
# monotone rim width, opening at the throat, no negative widths
for u in np.linspace(0.0, 1.0, 201):
    assert LAST.wm(u) >= -1e-9 and LAST.wup(u) >= -1e-9, "negative width at %.3f" % u
    assert LAST.zrim(u) >= LAST.zbupper(u) - 1e-9, "rim below hem at %.3f" % u
    assert LAST.wm(u) >= LAST.wup(u) - 1e-6, "upper wider than midsole at %.3f" % u
print("  widths/heights consistent over 201 samples")
print("  OK" if ok else "  POLE MISMATCH")
print()
print("opening outline (top view):")
for u in np.linspace(0.40, 1.0, 25):
    xr = LAST.xrim(u) * 1000
    if xr > 0.05:
        print("   u=%.3f y=%7.1f mm  half_open=%5.1f  rim z=%5.1f" %
              (u, LAST.y(u) * 1000, xr, LAST.zrim(u) * 1000))
