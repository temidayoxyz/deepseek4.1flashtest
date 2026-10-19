"""General artefact sweep: flag any edge much longer than its neighbours."""
import bpy
import numpy as np
from materials import build_materials
from shoe import build_shoe

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

mats = build_materials()
objs = build_shoe(mats)

print("%-16s %8s %10s %10s %8s" % ("object", "verts", "max_edge", "p99_edge", ">6mm"))
worst = []
for name, ob in sorted(objs.items()):
    if not hasattr(ob, "data") or not hasattr(ob.data, "edges"):
        continue
    me = ob.data
    co = np.array([v.co[:] for v in me.vertices])
    if len(co) == 0:
        continue
    e = np.array([e.vertices[:] for e in me.edges])
    L = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
    n6 = int((L > 0.006).sum())
    print("%-16s %8d %10.4f %10.4f %8d"
          % (name, len(co), L.max(), np.percentile(L, 99), n6))
    if n6:
        idx = np.argsort(-L)[:5]
        for k in idx:
            a, b = e[k]
            print("      long edge %.4f m  (%+.4f %+.4f %+.4f) -> (%+.4f %+.4f %+.4f)"
                  % (L[k], *co[a][:], *co[b][:]))
