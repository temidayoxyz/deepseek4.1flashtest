"""Probe LAST.point / normal right at the toe pole."""
from shoe import LAST

for u in (0.0, 0.0005, 0.002, 0.005, 0.01, 0.02, 0.05):
    print("u=%.4f  y=%+.5f" % (u, LAST.y(u)))
    for q in (0.0, 0.25, 0.5, 0.75, 1.0):
        p = LAST.point(u, q, 0.0)
        n = LAST.normal(u, q)
        print("    q=%.2f  x=%+.5f z=%+.5f   n=(%+.3f,%+.3f,%+.3f)"
              % (q, p.x, p.z, n.x, n.y, n.z))
