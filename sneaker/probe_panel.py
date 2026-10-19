"""Numeric sanity checks for the reshaped midfoot panel outline."""
import numpy as np
from shoe import LAST, smoothstep, _quarter_uv, _qp_s_lo, _qp_s_hi


def eyestay_low_s(u):
    b = (u - 0.442) / 0.443
    taper = 0.22 + 0.78 * float(smoothstep(0.0, 0.11, b))
    ds = (0.180 + 0.040 * np.sin(np.pi * max(0.0, min(1.0, b)))) * taper
    return min(1.0, LAST.sopen(u) + 0.02) - ds


print("boundaries")
print(" a    u_front  u_rear   s_lo    s_hi    s_hi-s_lo")
bad = 0
for a in np.linspace(0.0, 1.0, 9):
    u0, s0 = _quarter_uv(a, 0.0)
    u1, s1 = _quarter_uv(a, 1.0)
    d = s1 - s0
    if d < 0.15:
        bad += 1
        print("  INVERTED at a=%.2f  (s_hi-s_lo=%.3f)" % (a, d))
    print("%5.2f  %7.3f  %7.3f  %6.3f  %6.3f  %6.3f"
          % (a, u0, u1, s0, s1, d))

print()
print("bottom edge vs midsole top edge (raw edge must stay hidden):")
for a in np.linspace(0.0, 1.0, 9):
    u, s = _quarter_uv(a, 0.0)
    zb, zt = LAST.zbupper(u), LAST.zt(u)
    z = zb + s * (zt - zb)
    zst = LAST.zst(u)
    tag = "OK" if z < zst - 0.0002 else "VISIBLE"
    if tag != "OK":
        bad += 1
    print("  a=%.2f u=%.3f  edge z=%6.2f  midsole top z=%6.2f  %s"
          % (a, u, z * 1000, zst * 1000, tag))

print()
print("top edge vs eyestay lower edge (should leave a knit gap):")
for a in np.linspace(0.0, 1.0, 9):
    u, s = _quarter_uv(a, 1.0)
    if not (0.442 <= u <= 0.885):
        print("  a=%.2f u=%.3f -> outside eyestay range" % (a, u))
        continue
    low = eyestay_low_s(u)
    gap = low - s
    if gap < 0.05:
        bad += 1
    print("  a=%.2f u=%.3f  panel_top_s=%.3f  eyestay_low_s=%.3f  gap=%.3f"
          % (a, u, s, low, gap))

print()
print("bottom edge z vs midsole shoulder coverage (mm of overlap):")
for a in np.linspace(0.0, 1.0, 9):
    u, s = _quarter_uv(a, 0.0)
    zb, zt = LAST.zbupper(u), LAST.zt(u)
    z = zb + s * (zt - zb)
    print("  a=%.2f u=%.3f  edge z=%6.2f  (midsole top %6.2f)  headroom %5.2f mm"
          % (a, u, z * 1000, LAST.zst(u) * 1000, (LAST.zst(u) - z) * 1000))

print()
print("problems:", bad)
