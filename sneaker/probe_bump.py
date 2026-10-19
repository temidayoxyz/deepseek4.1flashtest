"""Deep probe of the toe bumper's stray tip vertex."""
import bpy
import bmesh
from materials import build_materials
from shoe import build_shoe

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

mats = build_materials()
objs = build_shoe(mats)
ob = objs['toe']
me = ob.data

hi = [v for v in me.vertices if v.co.z > 0.030 and v.co.y > 0.135]
print("vertices with z>30mm and y>135mm:", len(hi))
for v in hi[:10]:
    print("   idx=%d  x=%+.5f y=%+.5f z=%+.5f" % (v.index, v.co.x, v.co.y, v.co.z))

if hi:
    tgt = hi[0].index
    faces = [p for p in me.polygons if tgt in p.vertices]
    print("faces touching that vertex:", len(faces))
    for p in faces[:6]:
        print("   face %d  n=%s  area=%.2e" % (p.index, tuple(round(c, 3) for c in p.normal), p.area))
        for i in p.vertices:
            c = me.vertices[i].co
            print("        v%d  x=%+.5f y=%+.5f z=%+.5f" % (i, c.x, c.y, c.z))
        # vertex normals
        for i in p.vertices:
            n = me.vertices[i].normal
            print("        n%d  (%+.3f %+.3f %+.3f)" % (i, n.x, n.y, n.z))

# now rebuild the same patch without solidify and look for the same spot
import numpy as np
from shoe import LAST
import math
print()
print("--- raw patch check (no solidify) ---")
def bump_u(q):
    return 0.105 + 0.115 * (1.0 - math.sin(math.pi * q) ** 0.7)

for i in (0, 1, 2):
    for j in (0, 36, 72):
        q = j / 72.0
        ti = i / 60.0
        uu = ti * bump_u(q)
        from shoe import smoothstep as _ss
        off = 0.00025 + 0.00105 * float(_ss(0.0, 0.022, uu))
        p = LAST.point(uu, q, off)
        print("i=%2d j=%2d  u=%.5f q=%.3f  x=%+.5f y=%+.5f z=%+.5f"
              % (i, j, uu, q, p.x, p.y, p.z))
