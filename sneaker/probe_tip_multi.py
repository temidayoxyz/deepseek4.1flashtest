"""Macro renders of the toe tip with different parts hidden (one build)."""
import os
import sys
import bpy
import materials
import shoe
import studio

HERE = os.path.dirname(os.path.abspath(__file__))

studio.clear_scene()
mats = materials.build_materials()
parts = shoe.build_shoe(mats)
studio.build_cyclorama(studio.studio_material())
studio.build_lights()
studio.build_world()

cam = studio.build_camera(target=(0.0, 0.1480, 0.0250), dist=0.055, az=30.0, el=6.0,
                          lens=80.0)
sc = studio.setup_render(res=(700, 520), samples=40, gpu=True, denoise=True,
                         exposure=-3.4)
sc.camera = cam

VARIANTS = [("all", []),
            ("notoe", ["toe"]),
            ("noupper", ["upper"]),
            ("nomid", ["midsole"])]

objs = [(k, v) for k, v in parts.items() if hasattr(v, "hide_render")]
for tag, hide in VARIANTS:
    for k, v in objs:
        v.hide_render = k in hide or v.name in hide
    sc.render.filepath = os.path.join(HERE, "tipv_%s.png" % tag)
    bpy.ops.render.render(write_still=True)
    print("wrote tipv_%s.png" % tag)
