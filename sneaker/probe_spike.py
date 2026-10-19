"""Check for solidify spikes: stray vertices near the toe pole."""
import math
import bpy
import numpy as np
from materials import build_materials
from shoe import LAST, smoothstep, MB
import shoe as SH


def spike_report(ob, tag):
    me = ob.data
    bad = []
    for v in me.vertices:
        c = v.co
        if c.y > 0.1480 and c.z > 0.0285:
            bad.append((v.index, c.x, c.y, c.z))
    print("%-16s verts=%6d  stray(z>28.5mm @ y>148mm)=%d" % (tag, len(me.vertices), len(bad)))
    for i, x, y, z in bad[:6]:
        print("        v%-6d x=%+.5f y=%+.5f z=%+.5f" % (i, x, y, z))
    return len(bad)


for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

mats = build_materials()
objs = SH.build_shoe(mats)
for k in ('toe', 'upper', 'midsole', 'outsole_f', 'stitch', 'eyestay_L', 'quarter_L'):
    spike_report(objs[k], k)

# --- rebuild the bumper patch without solidify ---
print()
mb = MB()


def bump_u(q):
    return 0.105 + 0.115 * (1.0 - math.sin(math.pi * q) ** 0.7)


NU, NV = 60, 72
idx = []
for i in range(NU + 1):
    ti = i / NU
    row = []
    for j in range(NV + 1):
        q = j / NV
        uu = ti * bump_u(q)
        off = 0.00025 + 0.00105 * float(smoothstep(0.0, 0.022, uu))
        row.append(mb.add(LAST.point(uu, q, off), (uu * 240.0, q * 190.0)))
    idx.append(row)
mb.grid(idx, NU + 1, NV + 1)
ob = mb.to_object("BumpRaw", merge=1e-5, auto_angle=44.0, materials=[mats['panel_dense']])
print("raw (no solidify):")
spike_report(ob, "bump_raw")
print("  verts=%d  faces=%d" % (len(ob.data.vertices), len(ob.data.polygons)))
# how many verts within 0.02 mm of the pole point
pole = LAST.point(0.0, 0.5, 0.0)
near = [v.index for v in ob.data.vertices if (v.co - pole).length < 2e-5]
print("  verts within 0.02mm of pole:", len(near))
