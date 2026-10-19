"""Quick orthographic diagnostic views (Workbench, no lighting setup)."""
import os
import sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shoelib, shoe, materials, studio


def main():
    studio.clear_scene()
    mats = materials.build_materials()
    shoe.build_shoe(mats)

    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = 'BOTH'
    sc.display.shading.curvature_ridge_factor = 1.0
    sc.display.shading.curvature_valley_factor = 1.0
    sc.render.resolution_x = 900
    sc.render.resolution_y = 450
    sc.render.image_settings.file_format = 'PNG'

    cd = bpy.data.cameras.new("C")
    cd.type = 'ORTHO'
    cd.ortho_scale = 0.36
    cam = bpy.data.objects.new("C", cd)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    views = {
        'side': (0.0, 0.0),
        'top': (0.0, 89.5),
        'front': (90.0, 8.0),
        'back': (270.0, 8.0),
        'medial': (180.0, 0.0),
        'q34': (34.0, 15.0),
        'back34': (150.0, 18.0),
        'other': (-34.0, 12.0),
        'q34h': (34.0, 34.0),
    }
    for name, (az, el) in views.items():
        a = __import__('math').radians(az)
        e = __import__('math').radians(el)
        d = Vector((__import__('math').cos(e) * __import__('math').cos(a),
                    __import__('math').cos(e) * __import__('math').sin(a),
                    __import__('math').sin(e)))
        cam.location = Vector((0, 0, 0.06)) + d * 2.0
        studio.aim(cam, (0, 0, 0.06))
        sc.render.filepath = os.path.join(HERE, 'diag_%s.png' % name)
        bpy.ops.render.render(write_still=True)


main()
