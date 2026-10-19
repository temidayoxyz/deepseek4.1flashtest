"""Flag any vertex sitting above the toe box's crest line (spikes/fins)."""
import bpy
from materials import build_materials
from shoe import build_shoe, LAST

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

mats = build_materials()
objs = build_shoe(mats)


def u_of_y(y):
    lo, hi = 0.0, 0.44
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if LAST.y(mid) > y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


y_lim = LAST.y(0.42)
for name in ('upper', 'toe', 'midsole', 'outsole_f'):
    ob = objs[name]
    if not hasattr(ob, "data"):
        continue
    bad = []
    for v in ob.data.vertices:
        c = v.co
        if c.y < y_lim:
            continue
        u = u_of_y(c.y)
        crest = LAST.point(u, 0.5, 0.0)
        if c.z > crest.z + 0.0008:
            bad.append((c.x, c.y, c.z, crest.z))
    print("%-10s verts above crest+0.8mm (toe box): %d" % (name, len(bad)))
    for b in sorted(bad, key=lambda t: -t[2])[:8]:
        print("      x=%+.4f y=%+.4f z=%.4f (crest %.4f)" % b)
