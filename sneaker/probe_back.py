"""Numeric probe of the heel's back face region (pull tab design)."""
import numpy as np
from shoe import LAST, s_open, q_of_s, _s_heel_counter_top

hdr = "  u      y(mm)   zrim(mm) s_open  q_lo    crest(x,z)mm       normal"
print(hdr)
for u in np.arange(0.950, 1.0001, 0.005):
    p = LAST.point(u, 0.5)
    n = LAST.normal(u, 0.5)
    print("  %.3f  %7.2f  %7.2f  %6.3f  %6.3f  (%6.2f,%7.2f)  (%5.2f,%5.2f,%5.2f)" % (
        u, p.y * 1000, p.z * 1000, s_open(u), q_of_s(s_open(u)),
        p.x * 1000, p.z * 1000, n.x, n.y, n.z))

print()
for u in (0.9600, 0.9680, 0.9705, 0.9775, 0.9850):
    p = LAST.point(u, 0.5)
    n = LAST.normal(u, 0.5)
    print("u=%.4f  P=(%7.2f,%7.2f,%7.2f)mm  N=(%5.2f,%5.2f,%5.2f)" % (
        u, p.x * 1000, p.y * 1000, p.z * 1000, n.x, n.y, n.z))

pts = LAST.rim_points(220)
print()
print("rim curve: n=%d" % len(pts))
for i in (0, 1, 108, 109, 110, 111, 218, 219):
    p = pts[i]
    print("  rim[%3d] = (%7.2f,%7.2f,%7.2f) mm" % (i, p.x * 1000, p.y * 1000, p.z * 1000))

print()
for u in (0.90, 0.94, 0.958, 0.968, 0.98):
    s = _s_heel_counter_top(u)
    q = LAST.qside(s, 1.0)
    p = LAST.point(u, q)
    print("hc top u=%.3f s=%.3f -> (%6.2f,%7.2f,%7.2f) mm" % (u, s, p.x * 1000, p.y * 1000, p.z * 1000))
