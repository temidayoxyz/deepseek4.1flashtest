"""Macro render of the toe tip; optionally hide parts to identify artefacts.

usage: python probe_tip_render.py [out.png] [hide1,hide2,...]
"""
import os
import sys
import bpy
import materials
import shoe
import studio

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else "tip_macro.png"
if not os.path.isabs(out):
    out = os.path.join(HERE, out)
hide = []
for a in sys.argv[2:]:
    hide += [h for h in a.split(",") if h]

studio.clear_scene()
mats = materials.build_materials()
parts = shoe.build_shoe(mats)
studio.build_cyclorama(studio.studio_material())
studio.build_lights()
studio.build_world()

keys_by_obj = {}
for k, v in parts.items():
    if hasattr(v, "name"):
        keys_by_obj[v.name] = k
for h in hide:
    ob = parts.get(h)
    if ob is not None and hasattr(ob, "hide_render"):
        ob.hide_render = True
        print("hidden:", h, ob.name)

# macro camera on the toe tip (tip is at y=+0.1505, z=0.022)
cam = studio.build_camera(target=(0.0, 0.1470, 0.0245), dist=0.075, az=22.0, el=12.0,
                          lens=70.0)
sc = studio.setup_render(res=(720, 540), samples=48, gpu=True, denoise=True,
                         exposure=-3.4)
sc.camera = cam
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("wrote", out)
