"""Render the toe tip with each part in a flat identity colour.

usage: python probe_tint.py [out.png] [az] [res_w]x[res_h]
"""
import os
import sys
import bpy
import materials
import shoe
import studio

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else "tint.png"
if not os.path.isabs(out):
    out = os.path.join(HERE, out)
azs = [float(a) for a in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["22"])]
el = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
dist = float(sys.argv[4]) if len(sys.argv) > 4 else 0.075
ty = float(sys.argv[5]) if len(sys.argv) > 5 else 0.1470
tz = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0245

COLS = {
    'upper': (0.85, 0.08, 0.08),      # red
    'toe': (0.10, 0.85, 0.15),        # green
    'midsole': (0.15, 0.30, 0.95),    # blue
    'outsole_f': (0.95, 0.85, 0.10),  # yellow
    'outsole_h': (0.95, 0.55, 0.05),  # orange
    'collar': (0.95, 0.15, 0.95),     # magenta
    'tongue': (0.10, 0.85, 0.95),     # cyan
    'pulltab': (0.60, 0.40, 0.15),    # brown
    'laces': (0.95, 0.95, 0.95),      # white
    'lace': (0.95, 0.95, 0.95),
    'bow': (0.95, 0.95, 0.95),
    'eyestay_L': (0.95, 0.45, 0.65),  # pink
    'eyestay_R': (0.95, 0.45, 0.65),
    'eyelets': (0.20, 0.20, 0.20),
    'eyelet_ob': (0.20, 0.20, 0.20),
    'quarter_L': (0.55, 0.85, 0.20),  # lime
    'quarter_R': (0.55, 0.85, 0.20),
    'heeltab_strip': (0.60, 0.60, 0.95),
    'liner': (0.35, 0.35, 0.35),
    'trim': (0.90, 0.90, 0.30),
    'stitch': (0.05, 0.05, 0.05),
}


def flat_mat(name, col):
    m = bpy.data.materials.new("tint_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (col[0], col[1], col[2], 1.0)
    out_node = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out_node.inputs[0])
    return m


studio.clear_scene()
mats = materials.build_materials()
parts = shoe.build_shoe(mats)
studio.build_cyclorama(studio.studio_material())
studio.build_lights()
studio.build_world()

seen = {}
for k, v in parts.items():
    items = v if isinstance(v, (list, tuple)) else [v]
    for ob in items:
        if not hasattr(ob, "data"):
            continue
        col = COLS.get(k, COLS.get(ob.name, (1.0, 0.0, 1.0)))
        m = flat_mat(ob.name, col)
        ob.data.materials.clear()
        ob.data.materials.append(m)
        seen.setdefault(k, []).append(ob.name)
for k in sorted(seen):
    print("part %-16s %s" % (k, ",".join(seen[k])))

sc = studio.setup_render(res=(720, 540), samples=6, gpu=True, denoise=False,
                         exposure=0.0)
for az in azs:
    cam = studio.build_camera(target=(0.0, ty, tz), dist=dist, az=az,
                              el=el, lens=70.0)
    sc.camera = cam
    sc.render.filepath = out if len(azs) == 1 else "%s_az%d.png" % (out[:-4], int(az))
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)
