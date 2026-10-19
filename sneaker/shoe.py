"""Procedural construction of a performance running sneaker (Blender 5 / bpy).

Coordinate system (metres):
    +X  lateral (outside of the right shoe)      -X medial
    +Y  towards the toe                          -Y towards the heel
    +Z  up, ground plane at z = 0
"""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

from shoelib import (MB, pchip, smoothstep, TAU, tube, resample, solidify,
                     bevel, join, set_smooth_angle, apply_modifiers)

MM = 0.001

# ---------------------------------------------------------------------------
# longitudinal control grid  (u = 0 toe tip ... 1 heel tip)
# y spacing blends cosine (round tip/heel) with a linear term so that the
# poles are still resolved without clustering everything at the middle.
# ---------------------------------------------------------------------------
U = np.linspace(0.0, 1.0, 21)

Y_C = 0.006
Y_H = 0.1445          # half length about Y_C  -> y(0)=+0.1505  y(1)=-0.1385


def y_of_u(u):
    u = np.asarray(u, dtype=float)
    return Y_C + Y_H * (0.45 * np.cos(np.pi * u) + 0.55 * (1.0 - 2.0 * u))


LEN = float(y_of_u(0.0) - y_of_u(1.0))


def y_of_u_s(u):
    return float(y_of_u(u))


# --- profile tables (metres), one entry per U sample ------------------------
# every table converges to the *same* height at both poles so the sections
# collapse to a single point there (toe 22 mm, heel 36 mm)
_ZTIP, _ZHEEL = 0.0220, 0.0360

# ground-contact plane of the outsole rubber (toe spring / heel bevel)
ZGB = np.array([0.0220, 0.0165, 0.0116, 0.0072, 0.0036, 0.0012, 0.0000, 0.0000,
                0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0002,
                0.0008, 0.0024, 0.0056, 0.0135, 0.0360])
# outsole rubber thickness (exposed foam in the waist)
TRUB = np.array([0.0000, 0.0045, 0.0060, 0.0062, 0.0062, 0.0062, 0.0062, 0.0060,
                 0.0050, 0.0032, 0.0014, 0.0006, 0.0005, 0.0010, 0.0026, 0.0044,
                 0.0058, 0.0062, 0.0062, 0.0052, 0.0000])
# top of the midsole (stack height)
ZST = np.array([0.0220, 0.0243, 0.0262, 0.0276, 0.0286, 0.0292, 0.0296, 0.0302,
                0.0308, 0.0316, 0.0326, 0.0338, 0.0352, 0.0368, 0.0382, 0.0392,
                0.0398, 0.0400, 0.0398, 0.0386, 0.0360])
# top edge of the material: dome crest where the shell is closed, collar rim
# where it is open
ZRIM = np.array([0.0220, 0.0330, 0.0415, 0.0490, 0.0545, 0.0590, 0.0625, 0.0655,
                 0.0680, 0.0700, 0.0720, 0.0745, 0.0775, 0.0810, 0.0845, 0.0880,
                 0.0910, 0.0920, 0.0905, 0.0870, 0.0360])
# half width of the collar/throat opening  (0 = shell closed)
XOPEN = np.array([0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
                  0.0000, 0.0020, 0.0120, 0.0160, 0.0184, 0.0200, 0.0212, 0.0220,
                  0.0226, 0.0222, 0.0206, 0.0150, 0.0000])
# midsole half width (max), before the pole round-off
WM = np.array([0.0000, 0.0125, 0.0215, 0.0295, 0.0358, 0.0408, 0.0446, 0.0472,
               0.0488, 0.0496, 0.0498, 0.0490, 0.0474, 0.0456, 0.0440, 0.0428,
               0.0424, 0.0428, 0.0432, 0.0400, 0.0000])
# upper half width at the sole seam (follows the midsole, slightly inside)
WUP = np.array([0.0000, 0.0089, 0.0179, 0.0259, 0.0322, 0.0372, 0.0410, 0.0436,
                0.0452, 0.0460, 0.0462, 0.0454, 0.0438, 0.0420, 0.0404, 0.0392,
                0.0388, 0.0392, 0.0396, 0.0364, 0.0000])

_f = {name: pchip(U, tab) for name, tab in
      dict(wup=WUP, wm=WM, zgb=ZGB, trub=TRUB, zst=ZST, zrim=ZRIM,
           xopen=XOPEN).items()}

# upper section lateral profile --------------------------------------------
# superellipse: u = (1 - s^K)^(1/M)  ->  blunt rounded crest, near-vertical
# walls low down
_K = 3.2
_M = 1.92


def up_shape(s):
    s = np.clip(np.asarray(s, dtype=float), 0.0, 1.0)
    return np.power(np.clip(1.0 - s ** _K, 0.0, 1.0), 1.0 / _M)


# inverse of up_shape (both monotone on [0,1]) ------------------------------
_GS = np.linspace(0.0, 1.0, 4001)
_GV = up_shape(_GS)


def g_inv(v):
    v = np.clip(np.asarray(v, dtype=float), 0.0, 1.0)
    out = np.interp(v, _GV[::-1], _GS[::-1])
    return float(out) if np.ndim(v) == 0 else out


def q_of_s(s):
    s = np.clip(np.asarray(s, dtype=float), 0.0, 1.0)
    return np.arccos(np.clip(1.0 - 2.0 * s, -1.0, 1.0)) / TAU


def s_of_q(q):
    return (1.0 - np.cos(TAU * np.asarray(q, dtype=float))) * 0.5


# midsole section lateral profile (normalised bulge over the ledge width) ----
_GM = pchip(np.array([0.00, 0.05, 0.12, 0.22, 0.35, 0.55, 0.72, 0.85, 0.93, 0.975, 1.0]),
            np.array([0.905, 0.955, 0.982, 0.997, 1.0, 0.990, 0.958, 0.868, 0.700, 0.420, 0.0]))


def mid_shape(s):
    return _GM(np.clip(np.asarray(s, dtype=float), 0.0, 1.0))


def bulge_of_u(u):
    return 0.0030 * float(smoothstep(0.02, 0.11, u)) * \
        (1.0 - float(smoothstep(0.90, 0.99, u))) + 0.0007


# --- pole round-off ---------------------------------------------------------
# the sections collapse to a point at u=0/1; the *widths* must approach that
# point like a circle (w ~ sqrt(1-t^2)) or the tip looks cut off
def _round(u, u0, u1):
    t = np.clip((np.asarray(u, dtype=float) - u0) / (u1 - u0), 0.0, 1.0)
    return np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0))


def pole_factor(u):
    return _round(u, 0.055, 0.0) * _round(u, 0.860, 1.0)


def wm_eff(u):
    return float(_f['wm'](u)) * float(pole_factor(u))


def wup_eff(u):
    return float(_f['wup'](u)) * float(pole_factor(u))


def tuck_of_u(u):
    """how far the upper's hem sits below the midsole top edge"""
    return 0.0035 * float(smoothstep(0.0, 0.075, u)) * \
        (1.0 - float(smoothstep(0.94, 1.0, u)))


# collar / throat opening ----------------------------------------------------
U_THROAT = 0.428


def x_open(u):
    """half width of the opening; closes over the collar's back (u >~ 0.968)"""
    u = float(u)
    cf = 1.0 - float(smoothstep(0.885, 0.968, u)) ** 1.6
    return float(_f['xopen'](u)) * max(0.0, cf)


def ratio_open(u):
    w = wup_eff(u)
    xr = min(x_open(u), w * 0.9997)
    return (xr / w) if w > 1e-7 else 0.0


def s_open(u):
    return g_inv(ratio_open(u))


def z_rim(u):
    return float(_f['zrim'](u))


def z_bupper(u):
    return float(_f['zst'](u)) - tuck_of_u(u)


def z_top(u):
    """virtual section crest: stretched so that the rim lands on (x_open, zrim)"""
    zb = z_bupper(u)
    s = max(s_open(u), 1e-4)
    return zb + (z_rim(u) - zb) / s


def q_lo(u):
    return float(q_of_s(s_open(u)))


def q_hi(u):
    return 1.0 - q_lo(u)


# ---------------------------------------------------------------------------
class Last:
    """Analytic description of the last / upper shell."""

    def y(self, u):
        return float(y_of_u(u))

    def zgb(self, u):
        return float(_f['zgb'](u))

    def trub(self, u):
        return float(_f['trub'](u))

    def zst(self, u):
        return float(_f['zst'](u))

    def wm(self, u):
        return wm_eff(u)

    def wledge(self, u):
        return wm_eff(u) - bulge_of_u(u)

    def wup(self, u):
        return wup_eff(u)

    def zt(self, u):
        return z_top(u)

    def zrim(self, u):
        return min(z_rim(u), z_top(u))

    def zbupper(self, u):
        """bottom of the upper's material (tucked into the midsole)."""
        return z_bupper(u)

    def sopen(self, u):
        return s_open(u)

    def xrim(self, u):
        """half width of the collar opening at u"""
        return min(x_open(u), wup_eff(u) * 0.9997)

    def qside(self, s, side=1.0):
        q = q_of_s(s)
        return q if side >= 0.0 else 1.0 - q

    def s_for_z(self, u, z):
        zb, zt = z_bupper(u), z_top(u)
        return float(np.clip((z - zb) / max(zt - zb, 1e-9), 0.0, 1.0))

    def spoint(self, u, s, side=1.0):
        """point on the section at height fraction s (side = +1 lateral)"""
        w = wup_eff(u)
        x = side * w * float(up_shape(s))
        z = z_bupper(u) + float(s) * (z_top(u) - z_bupper(u))
        return Vector((x, self.y(u), z))

    # ---- upper surface ----------------------------------------------------
    def section_xz(self, u, q):
        """x,z of the upper's surface for parameter arrays u,q."""
        u = np.asarray(u, dtype=float)
        q = np.asarray(q, dtype=float)
        s = (1.0 - np.cos(TAU * q)) * 0.5
        w = self.wup_scalar(u)
        x = w * up_shape(s) * np.where(q < 0.5, -1.0, 1.0)
        zb = self.zbupper_scalar(u)
        zt = self.zt_scalar(u)
        z = zb + s * (zt - zb)
        return x, z

    def wup_scalar(self, u):
        return np.asarray(_f['wup'](u)) * pole_factor(u)

    def zbupper_scalar(self, u):
        u = np.asarray(u, dtype=float)
        return np.asarray(_f['zst'](u)) - 0.0035 * \
            smoothstep(0.0, 0.075, u) * (1.0 - smoothstep(0.94, 1.0, u))

    def zt_scalar(self, u):
        u = np.asarray(u, dtype=float)
        return z_bupper(u) + (z_rim(u) - z_bupper(u)) / np.maximum(s_open(u), 1e-4)

    def point(self, u, q, off=0.0):
        u = float(u)
        q = float(q)
        x, z = self.section_xz(u, q)
        p = Vector((float(x), self.y(u), float(z)))
        if off:
            p = p + self.normal(u, q) * off
        return p

    def normal(self, u, q, eps=2e-3):
        du = eps * 0.05
        a = self.raw(u + du, q)
        b = self.raw(u - du, q)
        c = self.raw(u, min(q + eps, 1.0))
        d = self.raw(u, max(q - eps, 0.0))
        n = (c - d).cross(a - b)
        if n.length < 1e-12:
            return Vector((0, 0, 1))
        n.normalize()
        # outward reference: away from the section's vertical axis
        ref = Vector((float(self.section_xz(u, q)[0]), 0.0,
                      float(self.section_xz(u, q)[1]) - (self.zbupper(u) + self.zt(u)) * 0.5))
        if ref.length < 1e-9:
            ref = Vector((0, 0, 1))
        ref.normalize()
        if n.dot(ref) < 0:
            n = -n
        return n

    def raw(self, u, q):
        x, z = self.section_xz(u, q)
        return Vector((float(x), float(y_of_u(u)), float(z)))

    # ---- rim curve (boundary of the collar / throat opening) --------------
    def rim_points(self, n=180):
        """throat tip -> medial side -> heel -> lateral side -> back to throat"""
        # ends where the opening pinches shut over the collar's back
        u1, u2 = U_THROAT, 0.969
        us = np.linspace(u1, u2, n)
        pts = [self.point(u, q_lo(u)) for u in us]
        pts += [self.point(u, q_hi(u)) for u in us[::-1]]
        return pts

    def rim_tangent_param(self, pts):
        return pts


LAST = Last()

# ---------------------------------------------------------------------------
# ring generation
# ---------------------------------------------------------------------------
NU_UP = 240
NVP = 30          # points per ribbon (a and b)


def _dist(a, b):
    return (a - b).length


def build_upper(mb, mat_idx=0):
    us = np.linspace(0.0, 1.0, NU_UP)
    # cosine distribution across the ribbon to cluster at seam + rim
    t = np.linspace(0.0, 1.0, NVP)
    tc = 0.5 - 0.5 * np.cos(np.pi * t)

    def wall(u):
        # the section pinches to a point at both poles; taper the wall away
        # there so the inner sheet cannot flare out past the outer one
        return 0.0022 * float(smoothstep(0.0, 0.045, u)) * \
            float(smoothstep(1.0, 0.955, u))

    rows = []
    for u in us:
        ql = q_lo(u)
        qh = q_hi(u)
        w = wall(u)
        qA = [ql * x for x in tc]
        qB = [qh + (1.0 - qh) * x for x in tc]
        rowA = [LAST.point(u, q) for q in qA]
        rowB = [LAST.point(u, q) for q in qB]
        inA = [rowA[j] - LAST.normal(u, qA[j]) * w for j in range(NVP)]
        inB = [rowB[j] - LAST.normal(u, qB[j]) * w for j in range(NVP)]
        rows.append((rowA, rowB, inA, inB))

    # uv: accumulated arc length
    uv_u = [0.0]
    for i in range(1, len(us)):
        a = rows[i][0][NVP // 2]
        b = rows[i - 1][0][NVP // 2]
        uv_u.append(uv_u[-1] + _dist(a, b))
    uv_u = np.array(uv_u)

    idxA = []
    idxB = []
    idxA2 = []
    idxB2 = []
    for i, (rowA, rowB, inA, inB) in enumerate(rows):
        uu = uv_u[i] * 1000.0
        rowIA = []
        rowIB = []
        rowIA2 = []
        rowIB2 = []
        # arc length from seam
        accA = [0.0]
        for j in range(1, NVP):
            accA.append(accA[-1] + _dist(rowA[j], rowA[j - 1]))
        half_per = 0.0
        for j in range(1, NVP):
            half_per += _dist(rows[i][1][j], rows[i][1][j - 1])
        for j in range(NVP):
            rowIA.append(mb.add(rowA[j], (uu, accA[j] * 1000.0)))
            rowIA2.append(mb.add(inA[j], (uu, accA[j] * 1000.0)))
        for j in range(NVP):
            vv = (half_per + (sum(_dist(rowB[k], rowB[k - 1])
                                  for k in range(1, j + 1)) if j > 0 else 0.0)) * 1000.0
            rowIB.append(mb.add(rowB[j], (uu, vv)))
            rowIB2.append(mb.add(inB[j], (uu, vv)))
        idxA.append(rowIA)
        idxB.append(rowIB)
        idxA2.append(rowIA2)
        idxB2.append(rowIB2)

    mb.grid(idxA, NU_UP, NVP)
    mb.grid(idxB, NU_UP, NVP)
    mb.grid(idxA2, NU_UP, NVP)
    mb.grid(idxB2, NU_UP, NVP)
    # close the wall along the hem lines and the collar's edges
    for idx_o, idx_i, col in ((idxA, idxA2, 0), (idxA, idxA2, NVP - 1),
                              (idxB, idxB2, 0), (idxB, idxB2, NVP - 1)):
        for i in range(NU_UP - 1):
            mb.quad(idx_o[i][col], idx_o[i + 1][col],
                    idx_i[i + 1][col], idx_i[i][col])
    return us


# ---------------------------------------------------------------------------
def panel_grid(mb, uq_fn, nu, nv, off_fn, uv_off=(0, 0), uv_scale=1.0):
    """Generic surface-conforming patch. uq_fn(i01, j01) -> (u,q)."""
    idx = []
    for i in range(nu + 1):
        row = []
        for j in range(nv + 1):
            u, q = uq_fn(i / nu, j / nv)
            off = off_fn(i / nu, j / nv)
            p = LAST.point(u, q, off)
            row.append(mb.add(p, (uv_off[0] + i * uv_scale, uv_off[1] + j * uv_scale)))
        idx.append(row)
    mb.grid(idx, nu + 1, nv + 1)
    return idx


def uv_len_panel(mb, pts, uv_scale=1000.0):
    idx = []
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + _dist(pts[i], pts[i - 1]))
    for i, p in enumerate(pts):
        idx.append(mb.add(p, (acc[i] * uv_scale, 0.0)))
    return idx


# ---------------------------------------------------------------------------
# part builders
# ---------------------------------------------------------------------------
def make_midsole(mats):
    mb = MB()
    NU = 190
    NS = 46
    us = np.linspace(0.0, 1.0, NU)
    # s samples cosine spaced, denser near both ends
    t = np.linspace(0.0, 1.0, NS)
    ss = 0.5 - 0.5 * np.cos(np.pi * t)

    rings = []
    for u in us:
        wm = LAST.wm(u)
        wl = LAST.wledge(u)
        zb = LAST.zgb(u) + LAST.trub(u)
        # the foam's top edge rides the seam (zst) exactly: lifting it at the
        # pole would break the profiles' convergence to a point there and stand
        # out past the upper as a fin
        zt = LAST.zst(u)
        xs = []
        zs = []
        # right side (s increasing) then left side mirrored
        for s in ss:
            hw = wl + (wm - wl) * float(mid_shape(s))
            # faint moulding crease around the foam's mid-height: breaks up the
            # specular sweep along the shoulder and reads as a sculpted sidewall
            hw *= 1.0 - 0.032 * math.exp(-((s - 0.42) / 0.10) ** 2)
            xs.append(hw)
            zs.append(zb + s * (zt - zb))
        ring = [(xs[k], zs[k]) for k in range(len(ss))] + \
               [(-xs[len(ss) - 1 - k], zs[len(ss) - 1 - k]) for k in range(len(ss))]
        rings.append(ring)

    idx = []
    acc = 0.0
    prev = None
    for i, ring in enumerate(rings):
        u = us[i]
        yy = LAST.y(u)
        row = []
        for k, (x, z) in enumerate(ring):
            p = Vector((x, yy, z))
            row.append(mb.add(p, (u * 260.0, k / len(ring) * 270.0)))
        idx.append(row)
        acc += 1

    mb.grid(idx, NU, len(rings[0]), close_v=True)
    ob = mb.to_object("Midsole", merge=1e-5, auto_angle=38.0, materials=[mats['foam']])
    return ob


def make_outsole(mats, u0, u1, name, tread_fn):
    mb = MB()
    NU = max(30, int((u1 - u0) * 420))
    NB = 64      # points across the bottom
    NS = 10      # side points
    us = np.linspace(u0, u1, NU)

    rows = []
    for u in us:
        wm = LAST.wm(u)
        wb = wm * 0.950
        wt = wm * 0.947
        zg = LAST.zgb(u)
        ztop = zg + LAST.trub(u) + 0.0016
        ring = []
        # bottom from -1 to +1
        xi = np.linspace(-1.0, 1.0, NB)
        for x in xi:
            g = tread_fn(u, x)
            ring.append((wb * x, zg + g))
        # right wall
        for k in range(1, NS + 1):
            t = k / NS
            x = wb + (wt - wb) * t
            z = (zg + tread_fn(u, 1.0)) + (ztop - (zg + tread_fn(u, 1.0))) * (t ** 0.85)
            ring.append((x, z))
        # top back to the left
        for k in range(1, NS + 1):
            t = k / NS
            x = wt - 2.0 * wt * t
            z = ztop
            ring.append((x, z))
        for k in range(1, NS):
            t = k / NS
            x = -wt - (wb - wt) * t
            z = ztop - (ztop - (zg + tread_fn(u, -1.0))) * (t ** 0.85)
            ring.append((x, z))
        rows.append(ring)

    idx = []
    for i, ring in enumerate(rows):
        yy = LAST.y(us[i])
        row = [mb.add(Vector((x, yy, z)), (us[i] * 300.0, k * 1.4))
               for k, (x, z) in enumerate(ring)]
        idx.append(row)
    mb.grid(idx, NU, len(rows[0]), close_v=True)
    # end caps
    for i, sgn in ((0, -1), (NU - 1, 1)):
        ring = rows[i]
        yy = LAST.y(us[i]) + sgn * 0.0008
        c = np.mean(np.array(ring, dtype=float), axis=0)
        ci = mb.add(Vector((float(c[0]), yy, float(c[1]))), (0, 0))
        for k in range(len(ring)):
            k2 = (k + 1) % len(ring)
            if sgn < 0:
                mb.tri(idx[i][k2], idx[i][k], ci)
            else:
                mb.tri(idx[i][k], idx[i][k2], ci)

    ob = mb.to_object(name, merge=1e-5, auto_angle=34.0, materials=[mats['rubber']])
    return ob


def tread_forefoot(u, xi):
    D = 0.0034
    g = 0.0
    # longitudinal blades
    for c, wid in ((0.235, 0.070), (0.60, 0.070)):
        for sgn in (-1.0, 1.0):
            t = abs(sgn * xi - c) / wid
            g = max(g, 1.0 - float(smoothstep(0.55, 1.0, t)))
    # transverse chevron sipes
    for uc in (0.083, 0.150, 0.222, 0.298, 0.375):
        ue = uc + 0.030 * (1.0 - abs(xi)) - 0.018
        t = abs(u - ue) / 0.020
        g = max(g, 1.0 - float(smoothstep(0.5, 1.0, t)))
    edge = float(smoothstep(1.0, 0.85, abs(xi)))
    ends = float(smoothstep(0.0, 0.07, (u - 0.036) / 0.392)) * \
        float(smoothstep(0.0, 0.07, (0.424 - u) / 0.388))
    return D * g * edge * ends


def tread_heel(u, xi):
    D = 0.0036
    g = 0.0
    for uc in (0.760, 0.828, 0.898, 0.960):
        ue = uc + 0.022 * (1.0 - abs(xi))
        t = abs(u - ue) / 0.022
        g = max(g, 1.0 - float(smoothstep(0.5, 1.0, t)))
    for c, wid in ((0.30, 0.075),):
        for sgn in (-1.0, 1.0):
            t = abs(sgn * xi - c) / wid
            g = max(g, 0.85 * (1.0 - float(smoothstep(0.55, 1.0, t))))
    edge = float(smoothstep(1.0, 0.84, abs(xi)))
    ends = float(smoothstep(0.0, 0.05, (u - 0.726) / 0.266)) * \
        float(smoothstep(0.0, 0.05, (0.9940 - u) / 0.268))
    return D * g * edge * ends


# ---------------------------------------------------------------------------
def make_overlays(mats, out):
    """Toe rand / bumper, built as a closed double sheet by hand.

    Solidify would offset along the mesh's degenerate pole normals (flashing a
    fin at the tip) and would lay a wall along the sole seam (a lip where the
    foam pinches out at the toe).  Offsetting analytically instead lets the
    wall taper to nothing at the seam and at the pole, while a rim is laid
    only along the stitched edge - the one edge meant to be seen.
    """
    def bump_u(q):
        return 0.105 + 0.115 * (1.0 - math.sin(math.pi * q) ** 0.7)

    mb = MB()
    NU, NV = 60, 72
    THR = 0.0016

    def off_of(uu, q):
        # proud of the upper everywhere, but only a hair at the toe pole so the
        # rand never beaks out past the midsole's tip, and tapered towards the
        # sole seam where it tucks under the foam
        lat = 0.25 + 0.75 * float(smoothstep(0.0, 0.085, min(q, 1.0 - q)))
        return (0.00025 + 0.00105 * float(smoothstep(0.0, 0.022, uu))) * lat

    def thr_of(uu, q):
        hem = float(smoothstep(0.0, 0.10, min(q, 1.0 - q)))
        return THR * hem * float(smoothstep(0.0, 0.02, uu))

    out_rows, in_rows = [], []
    for i in range(NU + 1):
        ti = i / NU
        ro, ri = [], []
        for j in range(NV + 1):
            q = j / NV
            uu = ti * bump_u(q)
            uv = (uu * 240.0, q * 190.0)
            p = LAST.point(uu, q, off_of(uu, q))
            ro.append(mb.add(p, uv))
            ri.append(mb.add(p - LAST.normal(uu, q) * thr_of(uu, q), uv))
        out_rows.append(ro)
        in_rows.append(ri)
    mb.grid(out_rows, NU + 1, NV + 1)
    mb.grid(in_rows, NU + 1, NV + 1)
    # rim along the stitched edge only; the seam and pole edges close up on
    # their own because the wall's thickness tapers to zero there
    for j in range(NV):
        mb.quad(out_rows[NU][j], out_rows[NU][j + 1],
                in_rows[NU][j + 1], in_rows[NU][j])
    ob = mb.to_object("ToeBumper", merge=1e-5, auto_angle=44.0,
                      materials=[mats['panel_dense']])
    out['toe'] = ob


def _panel_top_quarter(u):
    """top edge of the midfoot reinforcement (as a height fraction)"""
    return (0.400 + 0.220 * float(smoothstep(0.36, 0.62, u))
            - 0.110 * float(smoothstep(0.62, 0.73, u)))


def _qp_u_front(b):
    """front edge of the midfoot panel: slants back as it climbs"""
    return 0.298 + 0.132 * (b ** 1.55)


def _qp_u_rear(b):
    """rear edge of the midfoot panel: leans slightly forward at the top"""
    return 0.726 - 0.040 * (b ** 1.2)


def _qp_s_lo(a):
    """bottom edge: follows the midsole line, dropping a touch at the back
    (kept below the midsole's top edge so the raw edge stays hidden)"""
    return 0.048 - 0.005 * float(smoothstep(0.50, 1.0, a))


def _qp_s_hi(u):
    return min(_panel_top_quarter(u), LAST.sopen(u) - 0.20)


def _quarter_uv(a, b):
    """Coons-style blend of the panel's four boundary curves -> (u, s)."""
    ul, uh = _qp_u_front(b), _qp_u_rear(b)
    u = (1.0 - a) * ul + a * uh
    u_top = (1.0 - a) * _qp_u_front(1.0) + a * _qp_u_rear(1.0)
    return u, (1.0 - b) * _qp_s_lo(a) + b * _qp_s_hi(u_top)


def make_quarter_panels(mats, out):
    """Midfoot reinforcement panels, one per side."""
    for side, sgn in (('L', 1.0), ('R', -1.0)):
        def uq_fn(a, b):
            u, s = _quarter_uv(a, b)
            return (u, LAST.qside(s, sgn))

        def off_fn(a, b):
            return 0.0013

        mb = MB()
        panel_grid(mb, uq_fn, 40, 56, off_fn, uv_scale=3.2)
        ob = mb.to_object("Quarter_%s" % side, merge=1e-5, auto_angle=44.0,
                          materials=[mats['panel_dense']])
        solidify(ob, 0.0010, offset=-1.0)
        out['quarter_' + side] = ob


def z_heel_counter(u):
    """design height of the heel counter's top edge (dips at the back)"""
    return 0.0840 - 0.0300 * float(smoothstep(0.930, 1.0, u)) ** 1.2


def _s_heel_counter_top(u):
    zb, zt = LAST.zbupper(u), LAST.zt(u)
    return min((z_heel_counter(u) - zb) / max(zt - zb, 1e-9), 0.93)


def make_heel_counter(mats, out):
    """Wrap-around heel stabiliser band, both sides meeting at the back."""
    for side, sgn in (('L', 1.0), ('R', -1.0)):
        def uq_fn(a, b):
            u = 0.795 + (0.9995 - 0.795) * b
            s = 0.045 + (_s_heel_counter_top(u) - 0.045) * a
            return (u, LAST.qside(s, sgn))

        mb = MB()
        panel_grid(mb, uq_fn, 26, 56, lambda a, b: 0.0013, uv_scale=3.0)
        ob = mb.to_object("HeelCounter_%s" % side, merge=1e-5, auto_angle=44.0,
                          materials=[mats['panel_dense']])
        solidify(ob, 0.0010, offset=-1.0)
        out['heel_' + side] = ob


def make_eyestay(mats, out):
    """Lacing reinforcement running along both sides of the opening."""
    for side, sgn in (('L', 1.0), ('R', -1.0)):
        def uq_fn(a, b):
            u = 0.442 + (0.885 - 0.442) * b
            s_top = min(1.0, LAST.sopen(u) + 0.02)
            # the front end tapers to a narrow wedge instead of a blunt cut
            taper = 0.22 + 0.78 * float(smoothstep(0.0, 0.11, b))
            ds = (0.180 + 0.040 * math.sin(math.pi * b)) * taper
            s = s_top - ds * a
            return (u, LAST.qside(s, sgn))

        mb = MB()
        panel_grid(mb, uq_fn, 26, 54, lambda a, b: 0.0013, uv_scale=3.0)
        ob = mb.to_object("Eyestay_%s" % side, merge=1e-5, auto_angle=44.0,
                          materials=[mats['eyestay']])
        solidify(ob, 0.0010, offset=-1.0)
        out['eyestay_' + side] = ob


def make_collar_roll(mats, out):
    """Padded collar along the opening's rim.

    The tube's ends are sunk into the shell at the throat so the padding
    appears to fade into the upper instead of stopping in a cut face.
    """
    n = 130
    us = np.linspace(U_THROAT, 0.969, n)
    seq = [(u, q_lo(u)) for u in us] + [(u, q_hi(u)) for u in us[::-1]]
    pts = [LAST.point(u, q) for u, q in seq]
    nrm = [LAST.normal(u, q) for u, q in seq]
    m = len(pts)
    path = []
    radii = []
    for i in range(m):
        t = i / (m - 1.0)
        # t 0 -> throat tip, 0.5 -> collar back, 1 -> throat tip
        w = 1.0 - abs(2.0 * t - 1.0)
        r = 0.0020 + 0.0036 * float(smoothstep(0.0, 0.42, w))
        sink = 0.0026 * (1.0 - float(smoothstep(0.0, 0.055, w)))
        path.append(pts[i] - nrm[i] * sink)
        radii.append(r)
    mb = MB()
    flat = [1.18] * m
    tube(mb, path, radii, uv_scale=(1.0, 1.0), nseg=16, flatten=flat,
         caps=True, uv_off=(0, 0))
    ob = mb.to_object("CollarRoll", merge=1e-5, auto_angle=48.0,
                      materials=[mats['collar']])
    out['collar'] = ob


def make_tongue(mats, out):
    """Padded tongue filling the opening.

    The lateral extent follows the shell's inner wall at the local height, so
    the tongue's edges tuck behind the eyestay instead of leaving a slot; the
    rear end dives out of sight inside the collar.
    """
    mb = MB()
    NU, NV = 76, 28

    def pt(a, b):
        u = 0.437 + (0.862 - 0.437) * a
        zr = LAST.zrim(u)
        drop = 0.0110 * float(smoothstep(0.80, 1.0, a))
        # flat padded pad a little under the rim: the laces press into it
        z = zr - 0.0055 - drop - 0.0075 * (abs(b) ** 2.2)
        w = LAST.wup(u) * float(up_shape(LAST.s_for_z(u, z))) - 0.0008
        return Vector((b * max(w, 0.0005), LAST.y(u), z))

    idx = []
    for i in range(NU + 1):
        a = i / NU
        row = []
        for j in range(NV + 1):
            b = -1.0 + 2.0 * j / NV
            row.append(mb.add(pt(a, b), (a * 95.0, (b * 0.5 + 0.5) * 36.0)))
        idx.append(row)
    mb.grid(idx, NU + 1, NV + 1)
    ob = mb.to_object("Tongue", merge=1e-5, auto_angle=44.0,
                      materials=[mats['tongue']])
    solidify(ob, 0.0045, offset=-1.0, even=False)
    out['tongue'] = ob


def make_liner(mats, out):
    """Insock closing the hollow interior: seen through the collar opening."""
    mb = MB()
    NU, NV = 70, 22

    def pt(a, b):
        u = 0.415 + (0.9740 - 0.415) * a
        z0 = float(_f['zst'](u)) + 0.0055 - 0.0040 * (1.0 - b * b)
        w = LAST.wup(u) * float(up_shape(LAST.s_for_z(u, z0))) - 0.0035
        return Vector((b * max(w, 0.0), LAST.y(u), z0))

    idx = []
    for i in range(NU + 1):
        a = i / NU
        row = []
        for j in range(NV + 1):
            b = -1.0 + 2.0 * j / NV
            row.append(mb.add(pt(a, b), (a * 90.0, (b * 0.5 + 0.5) * 40.0)))
        idx.append(row)
    mb.grid(idx, NU + 1, NV + 1)
    ob = mb.to_object("Liner", merge=1e-5, auto_angle=40.0, materials=[mats['liner']])
    out['liner'] = ob


def make_pull_tab(mats, out):
    """Flat webbing loop stitched over the rear of the collar band.

    Control points live in the x = 0 plane; the first and last sit *inside*
    the collar band's rolled volume so both ends are hidden exactly where the
    strap appears to pass under the band.
    """
    cps = [(-0.1385, 0.0705),   # inside the band (hidden)
           (-0.1425, 0.0720),
           (-0.1480, 0.0775),
           (-0.1480, 0.0855),
           (-0.1445, 0.0900),   # top of the loop
           (-0.1415, 0.0835),
           (-0.1396, 0.0775)]   # inside the band (hidden)
    path = resample([Vector((0.0, y, z)) for (y, z) in cps], 46)
    n = len(path)
    radii = []
    for i in range(n):
        e = min(i, n - 1 - i) / 3.0
        radii.append(0.0010 * (0.55 + 0.45 * min(1.0, e)))
    mb = MB()
    tube(mb, path, radii, nseg=12, flatten=[6.0] * n, caps=True,
         uv_scale=(1.0, 1.0), up_hint=Vector((1, 0, 0)))
    ob = mb.to_object("PullTab", merge=1e-5, auto_angle=48.0, materials=[mats['webbing']])
    out['pulltab'] = ob


def make_reflective(mats, out):
    """Restrained reflective trim: a thin strip on the heel counter's top edge."""
    for side, sgn in (('L', 1.0), ('R', -1.0)):
        def uq_fn(a, b):
            # runs right around to the heel's centre-back so its cut end faces
            # away from the camera instead of stopping mid-panel
            u = 0.845 + (0.992 - 0.845) * b
            s_top = _s_heel_counter_top(u)
            s = s_top - 0.060 + 0.050 * a
            return (u, LAST.qside(s, sgn))

        mb = MB()
        panel_grid(mb, uq_fn, 8, 56, lambda a, b: 0.0019, uv_scale=2.4)
        ob = mb.to_object("ReflectHeel_%s" % side, merge=1e-5, auto_angle=40.0,
                          materials=[mats['metal_soft']])
        solidify(ob, 0.0009, offset=-1.0)
        out['reflect_' + side] = ob


# ---------------------------------------------------------------------------
def eyelet_frame(u, side):
    sgn = 1.0 if side == 'L' else -1.0
    s = max(0.08, LAST.sopen(u) - 0.115)
    q = LAST.qside(s, sgn)
    p = LAST.point(u, q, 0.0016)
    n = LAST.normal(u, q)
    return p, n, q


EYE_U = [0.492, 0.552, 0.612, 0.672, 0.732, 0.792]


def make_eyelets(mats, out):
    mb = MB()
    pos = {'L': [], 'R': []}
    for side in ('L', 'R'):
        for u in EYE_U:
            p, n, q = eyelet_frame(u, side)
            pos[side].append((p, n, u, q))
            # torus
            seg, tub = 20, 8
            R, r = 0.0024, 0.0008
            up = Vector((0, 1, 0))
            if abs(n.dot(up)) > 0.9:
                up = Vector((0, 0, 1))
            ax = up - n * up.dot(n)
            ax.normalize()
            ay = n.cross(ax)
            rings = []
            for i in range(seg):
                a = TAU * i / seg
                c = p + ax * (R * math.cos(a)) + ay * (R * math.sin(a))
                ring = []
                for k in range(tub):
                    b = TAU * k / tub
                    d = (ax * math.cos(a) + ay * math.sin(a)) * (r * math.cos(b)) + n * (r * math.sin(b))
                    ring.append(c + d)
                rings.append(ring)
            idx = []
            for i, ring in enumerate(rings):
                row = [mb.add(qq, (i * 0.35, k * 0.35)) for k, qq in enumerate(ring)]
                idx.append(row)
            idx.append(idx[0][:])
            mb.grid(idx, close_v=True)
    out['eyelets'] = pos
    ob = mb.to_object("Eyelets", merge=2e-5, auto_angle=50.0, materials=[mats['metal']])
    out['eyelet_ob'] = ob
    return pos


# ---------------------------------------------------------------------------
def make_laces(mats, out):
    pos = out['eyelets']
    mb = MB()

    def seg_path(pA, pB, nA, nB, bulge=0.0042):
        pts = []
        for i in range(15):
            t = i / 14.0
            p = pA.lerp(pB, t)
            n = nA.lerp(nB, t).normalized()
            b = math.sin(math.pi * t) ** 0.8
            p = p + n * (bulge * b)
            # slight gravitational sag
            p = p + Vector((0, 0, -0.0007 * b))
            pts.append(p)
        return pts

    order = [('L', 5), ('R', 4), ('L', 3), ('R', 2), ('L', 1), ('R', 0),
             ('L', 0), ('R', 1), ('L', 2), ('R', 3), ('L', 4), ('R', 5)]

    def P(side, i):
        return pos[side][i]

    path = []
    for k in range(len(order) - 1):
        sA, iA = order[k]
        sB, iB = order[k + 1]
        pA, nA, uA, qA = P(sA, iA)
        pB, nB, uB, qB = P(sB, iB)
        # start/end slightly inside the eyelets
        pA2 = pA - nA * 0.0012
        pB2 = pB - nB * 0.0012
        seg = seg_path(pA2, pB2, nA, nB)
        if k == 0:
            path.extend(seg)
        else:
            path.extend(seg[1:])

    # top end extensions toward the bow knot
    pL, nL, _, _ = P('L', 5)
    pR, nR, _, _ = P('R', 5)
    mid = (pL + pR) * 0.5
    toec = (pL - pR).normalized()
    nrm = ((nL + nR) * 0.5).normalized()
    knot = mid + nrm * 0.0040 + Vector((0, -0.0030, 0.0055))
    extL = [pL + (knot - pL) * t for t in (0.75, 0.5, 0.25)]
    extR = [pR + (knot - pR) * t for t in (0.25, 0.5, 0.75)]
    path = [knot] + extL + path + extR + [knot]

    # build tube over the criss-cross path
    smooth = resample(path, 520)
    n = len(smooth)
    radii = [0.00135] * n
    flat = []
    for i in range(n):
        flat.append(0.72)
    idx = tube(mb, smooth, radii, nseg=12, flatten=flat, caps=True, uv_scale=(1.0, 1.0))

    # ---- bow : knot on the laces, two drooping loops, short tails ---------
    up = Vector((0, 0, 1))
    fwd = Vector((0, 1, 0))
    kp = [knot + toec * s for s in (-0.0045, -0.0022, 0.0, 0.0022, 0.0045)]
    kp = resample(kp, 13)
    tube(mb, kp, [0.0024 + 0.0009 * math.sin(math.pi * i / 12.0) for i in range(13)],
         nseg=12, flatten=[0.45] * 13, caps=True)

    for sgn in (-1.0, 1.0):
        # flattened ribbon loop, standing out sideways and drooping forward
        A = (toec * (sgn * 0.86) + fwd * 0.20 - up * 0.30).normalized()
        B = (fwd - A * fwd.dot(A)).normalized()
        c = knot + A * 0.0056 + up * 0.0011
        a_, b_ = 0.0086, 0.0050
        ear = []
        for k in range(25):
            th = TAU * k / 24.0
            ear.append(c + A * (a_ * 0.30 + a_ * math.cos(th)) + B * (b_ * math.sin(th)))
        tube(mb, ear + [ear[0]], [0.0022] * (len(ear) + 1), nseg=10,
             flatten=[0.32] * (len(ear) + 1), caps=True)
        # short ribbon tail resting on the tongue
        tail = []
        for k in range(13):
            t = k / 12.0
            tail.append(knot + toec * (sgn * 0.010 * t) + fwd * (0.013 * t) +
                        up * (0.0022 * t - 0.0125 * t * t))
        tube(mb, tail, [0.0020] * len(tail), nseg=10, flatten=[0.34] * len(tail),
             caps=True)

    ob = mb.to_object("Laces", merge=1.5e-5, auto_angle=50.0, materials=[mats['lace']])
    out['laces'] = ob
    out['knot'] = knot


# ---------------------------------------------------------------------------
def _stitch_line(mb, pts, spacing=0.0032, mat_len=0.0021, w=0.00032, h=0.00040,
                 nrm_fn=None, nrms=None):
    """Place small thread dashes along a 3D polyline."""
    n = len(pts)
    # cumulative length
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    total = acc[-1]
    if total < 1e-6:
        return
    count = max(1, int(total / spacing))
    for k in range(count + 1):
        d = k * spacing
        if d > total:
            break
        # find segment
        i = max(1, min(n - 1, np.searchsorted(acc, d)))
        f = (d - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-9)
        p = pts[i - 1].lerp(pts[i], f)
        t = (pts[i] - pts[i - 1]).normalized()
        if nrms is not None:
            nrm = (nrms[i - 1].lerp(nrms[i], f)).normalized()
        else:
            nrm = nrm_fn(p) if nrm_fn else Vector((0, 0, 1))
        if abs(nrm.dot(t)) > 0.95:
            nrm = Vector((1, 0, 0))
        side = t.cross(nrm).normalized()
        # alternate tilt
        tilt = 0.32 * (1 if k % 2 == 0 else -1)
        t2 = (t + side * tilt).normalized()
        side2 = t2.cross(nrm).normalized()
        base = p + nrm * 0.00022
        L = mat_len * 0.5
        # simple elongated box, 8 verts
        verts = []
        for sgn in (-1, 1):
            for u in (-1, 1):
                for v in (-1, 1):
                    pp = base + t2 * (L * u) + side2 * (w * 0.5 * v) + nrm * (h * 0.42 * sgn)
                    verts.append(pp)
        ix = [mb.add(pp, (k * 0.4, 0)) for pp in verts]
        a, b, c, d = ix[0], ix[1], ix[3], ix[2]
        e, f2, g, hh = ix[4], ix[5], ix[7], ix[6]
        mb.quad(a, b, c, d)
        mb.quad(f2, e, hh, g)
        mb.quad(e, a, d, hh)
        mb.quad(b, f2, g, c)
        mb.quad(a, e, f2, b)
        mb.quad(d, c, g, hh)


def _us_line(u_list, s_list, side, off=0.0019):
    pts, nrms = [], []
    for u, s in zip(u_list, s_list):
        q = LAST.qside(s, side)
        pts.append(LAST.point(u, q, off))
        nrms.append(LAST.normal(u, q))
    return pts, nrms


def make_stitching(mats, out):
    mb = MB()
    SOFF = 0.0019

    # 1) toe bumper boundary (one wrap)
    qs = np.linspace(0.035, 0.965, 120)
    pts, nrms = [], []
    for q in qs:
        u = (0.105 + 0.115 * (1.0 - math.sin(math.pi * q) ** 0.7)) * 0.94
        pts.append(LAST.point(u, q, SOFF))
        nrms.append(LAST.normal(u, q))
    _stitch_line(mb, pts, spacing=0.0029, nrms=nrms)

    # 2) eyestay lower edge
    for side in (1.0, -1.0):
        us = np.linspace(0.455, 0.878, 90)
        ss = []
        for u in us:
            b = (u - 0.442) / 0.443
            taper = 0.22 + 0.78 * float(smoothstep(0.0, 0.11, b))
            ds = (0.180 + 0.040 * math.sin(math.pi * b)) * taper
            ss.append(min(1.0, LAST.sopen(u) + 0.02) - ds + 0.014)
        pts, nrms = _us_line(us, ss, side, SOFF)
        _stitch_line(mb, pts, spacing=0.0030, nrms=nrms)

    # 3) quarter panel outline
    for side in (1.0, -1.0):
        # top edge
        us, ss = [], []
        for a in np.linspace(0.0, 1.0, 70):
            u, s = _quarter_uv(a, 1.0)
            us.append(u)
            ss.append(s - 0.014)
        pts, nrms = _us_line(us, ss, side, SOFF)
        _stitch_line(mb, pts, spacing=0.0030, nrms=nrms)
        # front and rear edges (inset along u)
        for b_end, du in ((0.0, 0.013), (1.0, -0.013)):
            us, ss = [], []
            for b in np.linspace(0.04, 0.94, 40):
                u, s = _quarter_uv(b_end, b)
                us.append(u + du)
                ss.append(s - 0.007)
            pts, nrms = _us_line(us, ss, side, SOFF)
            _stitch_line(mb, pts, spacing=0.0030, nrms=nrms)

    # 4) heel counter leading edge
    for side in (1.0, -1.0):
        ss = np.linspace(0.058, _s_heel_counter_top(0.798) - 0.014, 34)
        pts, nrms = _us_line([0.798] * len(ss), ss, side, SOFF)
        _stitch_line(mb, pts, spacing=0.0030, nrms=nrms)

    ob = mb.to_object("Stitching", merge=1e-6, auto_angle=60.0,
                      materials=[mats['thread']], recalc=False)
    out['stitch'] = ob


# ---------------------------------------------------------------------------
def build_shoe(mats):
    out = {}
    mb = MB()
    build_upper(mb, 0)
    # the upper carries its own analytic inner wall (see build_upper): Solidify
    # offsets along the mesh's degenerate pole normals and flashes a fin there
    upper = mb.to_object("Upper", merge=2e-5, auto_angle=46.0,
                         materials=[mats['knit']])
    out['upper'] = upper

    out['midsole'] = make_midsole(mats)
    out['outsole_f'] = make_outsole(mats, 0.030, 0.428, "Outsole_Fore", tread_forefoot)
    out['outsole_h'] = make_outsole(mats, 0.712, 0.994, "Outsole_Heel", tread_heel)

    make_overlays(mats, out)
    make_quarter_panels(mats, out)
    make_heel_counter(mats, out)
    make_eyestay(mats, out)
    make_collar_roll(mats, out)
    make_liner(mats, out)
    make_tongue(mats, out)
    make_pull_tab(mats, out)
    make_reflective(mats, out)
    pos = make_eyelets(mats, out)
    make_laces(mats, out)
    make_stitching(mats, out)
    return out
