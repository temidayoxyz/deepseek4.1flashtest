"""Core math + mesh construction helpers for the sneaker build."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

TAU = 2.0 * math.pi


# ----------------------------------------------------------------------------
# interpolation
# ----------------------------------------------------------------------------
def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolation. Returns f(x) vectorised."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    n = len(xs)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros(n)
    m[0] = d[0]
    m[-1] = d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        xa = np.clip(np.asarray(x, dtype=float), xs[0], xs[-1])
        i = np.clip(np.searchsorted(xs, xa, side='right') - 1, 0, n - 2)
        t = (xa - xs[i]) / h[i]
        t2 = t * t
        t3 = t2 * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        out = h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
        return float(out) if np.ndim(x) == 0 else out

    return f


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def catmull(pts, t):
    """Catmull-Rom through a list of Vectors, t in [0,1] over the whole list."""
    n = len(pts) - 1
    tt = np.clip(t, 0.0, 1.0) * n
    i = np.clip(np.floor(tt).astype(int), 0, n - 1)
    f = tt - i
    out = []
    for k in range(len(pts[0])):
        p0 = np.array([pts[max(j - 1, 0)][k] for j in i])
        p1 = np.array([pts[j][k] for j in i])
        p2 = np.array([pts[j + 1][k] for j in i])
        p3 = np.array([pts[min(j + 2, n)][k] for j in i])
        f2 = f * f
        f3 = f2 * f
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * f +
                          (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * f3))
    return np.stack(out, axis=-1)


# ----------------------------------------------------------------------------
# mesh builder
# ----------------------------------------------------------------------------
class MB:
    """Simple indexed mesh accumulator with per-vertex UVs."""

    def __init__(self):
        self.v = []
        self.uv = []
        self.f = []

    def add(self, p, uv):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        self.uv.append((float(uv[0]), float(uv[1])))
        return len(self.v) - 1

    def quad(self, a, b, c, d):
        self.f.append((a, b, c, d))

    def tri(self, a, b, c):
        self.f.append((a, b, c))

    def grid(self, idx, nu=None, nv=None, close_v=False):
        """idx[i][j] corner index grid -> quads."""
        nu = len(idx) - 1
        nv = len(idx[0]) if close_v else len(idx[0]) - 1
        for i in range(nu):
            for j in range(nv if close_v else nv):
                j2 = (j + 1) % len(idx[0])
                self.quad(idx[i][j], idx[i][j2], idx[i + 1][j2], idx[i + 1][j])

    def to_object(self, name, merge=1e-5, smooth=True, auto_angle=42.0,
                  recalc=True, materials=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate(verbose=False)
        uvl = me.uv_layers.new(name="UVMap")
        nl = len(me.loops)
        if nl:
            loop_vi = np.empty(nl, dtype=np.int32)
            me.loops.foreach_get('vertex_index', loop_vi)
            uv_arr = np.asarray(self.uv, dtype=np.float32)
            uvl.data.foreach_set('uv', uv_arr[loop_vi].ravel())
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        if materials:
            for m in materials:
                ob.data.materials.append(m)
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bm = bmesh.new()
        bm.from_mesh(me)
        if merge:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        if smooth:
            try:
                bpy.ops.object.shade_auto_smooth(angle=math.radians(auto_angle))
            except Exception:
                bpy.ops.object.shade_smooth()
        return ob


def apply_modifiers(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def solidify(ob, thickness, offset=-1.0, even=True, rim=True):
    m = ob.modifiers.new("solid", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = even
    m.use_quality_normals = True
    m.use_rim = rim
    m.use_rim_only = False
    apply_modifiers(ob)
    return ob


def bevel(ob, width, segments=2, angle=40.0, clamp=True):
    m = ob.modifiers.new("bev", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = clamp
    m.harden_normals = False
    apply_modifiers(ob)
    return ob


def subsurf(ob, levels=1):
    m = ob.modifiers.new("ss", 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    apply_modifiers(ob)
    return ob


def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def set_smooth_angle(ob, angle=42.0):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
    except Exception:
        bpy.ops.object.shade_smooth()


# ----------------------------------------------------------------------------
# small geometry generators
# ----------------------------------------------------------------------------
def tube(mb, path, radii, uv_scale=(1.0, 1.0), nseg=14,
         flatten=None, twist=None, caps=True, uv_off=(0.0, 0.0),
         up_hint=Vector((0, 0, 1))):
    """Sweep an ellipse cross-section along an arbitrary polyline (parallel transport)."""
    n = len(path)
    tangents = []
    for i in range(n):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        if t.length < 1e-12:
            t = Vector((0, 0, 1))
        tangents.append(t.normalized())

    # initial frame
    ref = up_hint if abs(tangents[0].dot(up_hint)) < 0.95 else Vector((1, 0, 0))
    nrm = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    frames = []
    for i in range(n):
        if i > 0:
            # parallel transport
            prev_t = tangents[i - 1]
            cur_t = tangents[i]
            v = prev_t.cross(cur_t)
            if v.length > 1e-9:
                ang = prev_t.angle(cur_t)
                q = Matrix.Rotation(ang, 3, v.normalized())
                nrm = (q @ nrm)
            nrm = (nrm - cur_t * nrm.dot(cur_t))
            if nrm.length < 1e-9:
                nrm = Vector((0, 0, 1))
            nrm.normalize()
        binorm = tangents[i].cross(nrm).normalized()
        frames.append((nrm.copy(), binorm))

    # arc length for u coord
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (path[i] - path[i - 1]).length)

    rings = []
    for i in range(n):
        nn, bb = frames[i]
        r = radii[i]
        fa = 1.0
        fb = 1.0
        if flatten is not None:
            fa = flatten[i]
        ang0 = 0.0
        if twist is not None:
            ang0 = twist[i]
        ring = []
        circ = 0.0
        for k in range(nseg):
            a = TAU * k / nseg + ang0
            ca = math.cos(a)
            sa = math.sin(a)
            p = path[i] + nn * (r * fa * ca) + bb * (r * fb * sa)
            ring.append(p)
            if k == 0:
                circ = 0.0
        rings.append(ring)

    idx = []
    rlen = max(radii[0], 1e-6) * TAU
    for i in range(n):
        row = []
        for k in range(nseg):
            u = uv_off[0] + acc[i] * uv_scale[0]
            v = uv_off[1] + (TAU * k / nseg) * radii[i] * uv_scale[1]
            row.append(mb.add(rings[i][k], (u, v)))
        idx.append(row)
    mb.grid(idx, n, nseg, close_v=True)
    if caps:
        # fans
        for i, direction in ((0, -1), (n - 1, 1)):
            nn, bb = frames[i]
            c = mb.add(path[i] + tangents[i] * (radii[i] * 0.9 * direction),
                       (uv_off[0] + acc[i] * uv_scale[0], uv_off[1]))
            for k in range(nseg):
                k2 = (k + 1) % nseg
                if direction < 0:
                    mb.tri(idx[i][k2], idx[i][k], c)
                else:
                    mb.tri(idx[i][k], idx[i][k2], c)
    return idx


def resample(points, n):
    """Catmull-Rom resample of a polyline into n points."""
    pts = [tuple(p) for p in points]
    arr = catmull(pts, np.linspace(0, 1, n))
    return [Vector(tuple(arr[i])) for i in range(n)]


def rounded_capsule(mb, p0, p1, r, uv_off=(0, 0)):
    tube(mb, [p0, p1], [r, r], caps=True, nseg=8, uv_scale=(1.0, 1.0), uv_off=uv_off)
