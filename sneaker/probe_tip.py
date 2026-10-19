"""List the vertices nearest the toe tip for every part (find fins/outliers)."""
import bpy
from materials import build_materials
from shoe import build_shoe

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

mats = build_materials()
objs = build_shoe(mats)

rows = []
for name, ob in objs.items():
    if not hasattr(ob, "matrix_world"):
        continue
    mw = ob.matrix_world
    pts = [mw @ v.co for v in ob.data.vertices]
    if not pts:
        continue
    ymax = max(p.y for p in pts)
    if ymax < 0.130:
        continue
    rows.append((ymax, name, pts))

for ymax, name, pts in sorted(rows, reverse=True):
    print("%-14s  ymax=%.4f  (n=%d)" % (name, ymax, len(pts)))
    top = sorted(pts, key=lambda p: -p.y)[:6]
    for p in top:
        print("        y=%.4f  x=%+.4f  z=%.4f" % (p.y, p.x, p.z))
