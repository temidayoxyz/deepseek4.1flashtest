"""Entry point: build the sneaker scene and render it."""
import argparse
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import shoelib
import shoe
import materials
import studio


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', default='960x540')
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--out', default='preview.png')
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--az', type=float, default=34.0)
    ap.add_argument('--el', type=float, default=15.0)
    ap.add_argument('--dist', type=float, default=1.06)
    ap.add_argument('--lens', type=float, default=88.0)
    ap.add_argument('--view', default='AgX')
    ap.add_argument('--look', default='AgX - Medium High Contrast')
    # the studio lights are calibrated bright; this exposure suits the AgX look
    ap.add_argument('--exposure', type=float, default=-3.6)
    ap.add_argument('--views', default='')
    ap.add_argument('--save-blend', default='')
    ap.add_argument('--glb', default='')
    return ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


def main():
    a = parse()
    t0 = time.time()
    studio.clear_scene()
    mats = materials.build_materials()
    parts = shoe.build_shoe(mats)
    print("[build] %.1fs  objects=%d" % (time.time() - t0, len(bpy.data.objects)))

    tris = 0
    for o in bpy.data.objects:
        if o.type == 'MESH':
            tris += len(o.data.polygons)
    print("[geo] faces=%d" % tris)

    wall = studio.studio_material()
    studio.build_cyclorama(wall)
    studio.build_lights()
    studio.build_world()

    res = tuple(int(x) for x in a.res.split('x'))
    sc = studio.setup_render(res=res, samples=a.samples, gpu=not a.cpu,
                             view_transform=a.view, look=a.look, exposure=a.exposure)

    views = []
    if a.views:
        for v in a.views.split(';'):
            parts_ = v.split(',')
            views.append(dict(az=float(parts_[0]), el=float(parts_[1]),
                              dist=float(parts_[2]) if len(parts_) > 2 else a.dist,
                              name=parts_[3] if len(parts_) > 3 else None))
    else:
        views.append(dict(az=a.az, el=a.el, dist=a.dist, name=None))

    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)

    for idx, v in enumerate(views):
        cam = studio.build_camera(dist=v['dist'], az=v['az'], el=v['el'], lens=a.lens)
        sc.camera = cam
        out = a.out if v['name'] is None else a.out.replace('.png', '_%s.png' % v['name'])
        sc.render.filepath = os.path.join(HERE, out) if not os.path.isabs(out) else out
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("[render] %s  %.1fs" % (sc.render.filepath, time.time() - t1))

    if a.glb:
        # export just the shoe (studio: cyclorama, lights, camera stay out)
        keep = []
        for k, val in parts.items():
            items = val if isinstance(val, (list, tuple)) else [val]
            for ob in items:
                if hasattr(ob, "type") and ob.type == 'MESH':
                    keep.append(ob)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in keep:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = keep[0]
        path = a.glb if os.path.isabs(a.glb) else os.path.join(HERE, a.glb)
        try:
            bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                                      use_selection=True)
            print("[glb] %s  %d meshes" % (path, len(keep)))
        except Exception as exc:      # noqa: BLE001 - report, don't lose renders
            print("[glb] export failed:", exc)


if __name__ == '__main__':
    main()
