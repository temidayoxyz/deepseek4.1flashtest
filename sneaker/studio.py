"""Studio environment: cyclorama, lighting, camera, render settings."""
import math
import bpy
from mathutils import Vector, Matrix

from shoelib import MB


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
              bpy.data.cameras, bpy.data.objects, bpy.data.images):
        for x in list(c):
            try:
                c.remove(x)
            except Exception:
                pass


# ---------------------------------------------------------------------------
def build_cyclorama(mat):
    mb = MB()
    prof = [(0.00, 0.000), (0.55, 0.000), (0.95, 0.0008), (1.30, 0.004),
            (1.62, 0.016), (1.90, 0.048), (2.12, 0.108), (2.30, 0.205),
            (2.44, 0.345), (2.54, 0.535), (2.61, 0.775), (2.66, 1.10),
            (2.69, 1.60), (2.70, 3.20), (2.70, 6.0)]
    NTH = 128
    rings = []
    for i, (r, z) in enumerate(prof):
        ring = []
        for k in range(NTH):
            a = 2.0 * math.pi * k / NTH
            ring.append(Vector((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    idx = []
    for i, ring in enumerate(rings):
        row = []
        for k, p in enumerate(ring):
            row.append(mb.add(p, (prof[i][0] * 0.4, k / NTH * 3.0)))
        idx.append(row)
    for i in range(len(rings) - 1):
        for k in range(NTH):
            k2 = (k + 1) % NTH
            mb.quad(idx[i][k], idx[i][k2], idx[i + 1][k2], idx[i + 1][k])
    # close the centre hole
    c = mb.add(Vector((0, 0, 0)), (0, 0))
    for k in range(NTH):
        k2 = (k + 1) % NTH
        mb.tri(idx[0][k2], idx[0][k], c)
    ob = mb.to_object("Studio", merge=1e-6, auto_angle=60.0, materials=[mat])
    return ob


def studio_material():
    m = bpy.data.materials.new("Studio_Wall")
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    b = nodes.get("Principled BSDF")
    b.inputs['Base Color'].default_value = (0.515, 0.515, 0.522, 1.0)
    b.inputs['Roughness'].default_value = 0.56
    b.inputs['Specular IOR Level'].default_value = 0.28
    if 'Sheen Weight' in b.inputs:
        b.inputs['Sheen Weight'].default_value = 0.10
    return m


# ---------------------------------------------------------------------------
def area_light(name, loc, look_at, size=(1.0, 1.0), power=200.0, color=(1, 1, 1),
               shape='RECTANGLE', spread=math.pi):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size[0]
    if shape == 'RECTANGLE':
        ld.size_y = size[1]
    ld.energy = power
    ld.color = color
    ld.spread = spread
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    aim(ob, look_at)
    return ob


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def build_lights():
    L = {}
    tgt = (0.0, 0.0, 0.055)
    # key : soft, upper front-left of camera (camera sits at +X +Y)
    L['key'] = area_light("Key", (-1.15, 1.05, 1.05), tgt, (1.60, 0.90), 820.0,
                          (1.0, 0.992, 0.972))
    # fill : broad, opposite side, lower power
    L['fill'] = area_light("Fill", (1.75, -0.55, 0.85), tgt, (2.0, 2.0), 75.0,
                           (0.975, 0.985, 1.0))
    # rim : behind, separates the silhouette
    L['rim'] = area_light("Rim", (-1.30, -1.05, 1.15), tgt, (0.9, 0.9), 260.0,
                          (0.99, 0.99, 1.0))
    # top softbox : broad wrap, kept well below the key so form stays readable
    L['top'] = area_light("Top", (0.10, 0.35, 2.05), (0.05, 0.0, 0.0), (2.6, 1.7), 220.0,
                          (1.0, 0.997, 0.99))
    # low kicker to lift the front of the shoe
    L['front'] = area_light("Front", (0.55, 1.55, 0.30), tgt, (1.1, 0.55), 55.0,
                            (1.0, 1.0, 1.0))
    # background wash (behind the shoe, lights the cyclorama wall)
    L['bg'] = area_light("BgWash", (0.6, -1.4, 1.30), (0.0, -0.85, 1.05), (1.9, 1.5), 360.0,
                         (1.0, 0.998, 0.99))
    return L


# ---------------------------------------------------------------------------
def build_world(strength=0.22, col=(0.60, 0.615, 0.64)):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*col, 1.0)
    bg.inputs[1].default_value = strength
    return w


def build_camera(target=(0.0, -0.004, 0.052), dist=1.06, az=34.0, el=15.0, lens=88.0,
                 sensor=36.0, name="Cam"):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    cd.clip_start = 0.05
    cd.clip_end = 100.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(ob)
    a = math.radians(az)
    e = math.radians(el)
    d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
    ob.location = Vector(target) + d * dist
    aim(ob, target)
    return ob


# ---------------------------------------------------------------------------
def setup_render(res=(1920, 1080), samples=256, gpu=True, denoise=True,
                 view_transform='AgX', look='AgX - Medium High Contrast', exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'GPU' if gpu else 'CPU'
    if gpu:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type = 'CUDA'
            prefs.get_devices()
            for d in prefs.devices:
                d.use = (d.type == 'CUDA')
        except Exception:
            pass
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.01
    sc.cycles.adaptive_min_samples = 32
    sc.cycles.max_bounces = 10
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.use_denoising = denoise
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        sc.cycles.denoising_use_gpu = False
    except Exception:
        pass
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.use_fast_gi = False
    sc.render.resolution_x = res[0]
    sc.render.resolution_y = res[1]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.compression = 25
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.threads_mode = 'AUTO'
    sc.view_settings.view_transform = view_transform
    try:
        sc.view_settings.look = look
    except Exception:
        pass
    sc.view_settings.exposure = exposure
    sc.view_settings.gamma = 1.0
    return sc
