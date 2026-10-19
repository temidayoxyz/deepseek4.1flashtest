"""Procedural PBR materials for the sneaker."""
import bpy


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes = nt.nodes
    for n in list(nodes):
        nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nodes, nt.links, bsdf


def setv(bsdf, key, val):
    if key in bsdf.inputs:
        sock = bsdf.inputs[key]
        if isinstance(val, (tuple, list)):
            try:
                sock.default_value = tuple(val)
                return
            except Exception:
                if len(val) == 3:
                    sock.default_value = tuple(val) + (1.0,)
                    return
                if len(val) == 4:
                    sock.default_value = tuple(val)[:3]
                    return
                raise
        sock.default_value = val


def S(x):
    """Accept a node (use its first output) or a socket."""
    if x is None:
        return None
    if hasattr(x, 'outputs'):
        return x.outputs[0]
    return x


def N(nodes, kind, loc, **kw):
    n = nodes.new(kind)
    n.location = loc
    for k, v in kw.items():
        if k == 'name':
            n.name = v
        else:
            setattr(n, k, v)
    return n


def setin(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value


def texcoord(nodes, loc=(-1500, 0)):
    tc = N(nodes, "ShaderNodeTexCoord", loc)
    return tc


def mapping(nodes, links, src, loc=(-1300, 0), scale=(1, 1, 1), rot=(0, 0, 0)):
    mp = N(nodes, "ShaderNodeMapping", loc)
    setin(mp, 'Scale', scale)
    setin(mp, 'Rotation', rot)
    links.new(S(src), mp.inputs['Vector'])
    return mp


def noise(nodes, links, vec, loc, scale=1.0, detail=2.0, rough=0.5, dist=0.0):
    n = N(nodes, "ShaderNodeTexNoise", loc)
    setin(n, 'Scale', scale)
    setin(n, 'Detail', detail)
    setin(n, 'Roughness', rough)
    setin(n, 'Distortion', dist)
    if vec is not None:
        links.new(S(vec), n.inputs['Vector'])
    return n


def voronoi(nodes, links, vec, loc, scale=1.0, rand=0.5, feature='DISTANCE_TO_EDGE',
            metric='EUCLIDEAN'):
    n = N(nodes, "ShaderNodeTexVoronoi", loc)
    n.feature = feature
    n.distance = metric
    setin(n, 'Scale', scale)
    setin(n, 'Randomness', rand)
    if vec is not None:
        links.new(S(vec), n.inputs['Vector'])
    return n


def wave(nodes, links, vec, loc, scale=1.0, dist=0.0, detail=1.0, direction='X',
         profile='SIN', phase=0.0):
    n = N(nodes, "ShaderNodeTexWave", loc)
    n.wave_type = 'BANDS'
    n.bands_direction = direction
    n.wave_profile = profile
    setin(n, 'Scale', scale)
    setin(n, 'Distortion', dist)
    setin(n, 'Detail', detail)
    setin(n, 'Detail Scale', 2.0)
    setin(n, 'Phase Offset', phase)
    if vec is not None:
        links.new(S(vec), n.inputs['Vector'])
    return n


def maprange(nodes, links, src, loc, fmin=0.0, fmax=1.0, tmin=0.0, tmax=1.0, clamp=True):
    n = N(nodes, "ShaderNodeMapRange", loc)
    setin(n, 'From Min', fmin)
    setin(n, 'From Max', fmax)
    setin(n, 'To Min', tmin)
    setin(n, 'To Max', tmax)
    n.clamp = clamp
    links.new(S(src), n.inputs['Value'])
    return n


def mathn(nodes, links, op, loc, a=None, b=None, clamp=False, av=None, bv=None):
    n = N(nodes, "ShaderNodeMath", loc)
    n.operation = op
    n.use_clamp = clamp
    if a is not None:
        links.new(S(a), n.inputs[0])
    elif av is not None:
        n.inputs[0].default_value = av
    if b is not None:
        links.new(S(b), n.inputs[1])
    elif bv is not None:
        n.inputs[1].default_value = bv
    return n


def mixrgb(nodes, links, loc, fac=0.5, c1=(0, 0, 0), c2=(1, 1, 1), f=None, a=None, b=None,
           blend='MIX'):
    n = N(nodes, "ShaderNodeMix", loc)
    n.data_type = 'RGBA'
    n.blend_type = blend
    n.clamp_result = False
    if f is not None:
        links.new(S(f), n.inputs['Factor'])
    else:
        n.inputs['Factor'].default_value = fac
    ia = n.inputs[6]
    ib = n.inputs[7]
    if a is not None:
        links.new(S(a), ia)
    else:
        ia.default_value = (*c1, 1.0)
    if b is not None:
        links.new(S(b), ib)
    else:
        ib.default_value = (*c2, 1.0)
    return n


def mixf(nodes, links, loc, f=None, a=0.0, b=1.0):
    n = N(nodes, "ShaderNodeMix", loc)
    n.data_type = 'FLOAT'
    if f is not None:
        links.new(S(f), n.inputs['Factor'])
    else:
        n.inputs['Factor'].default_value = 0.5
    n.inputs[2].default_value = a
    n.inputs[3].default_value = b
    return n


def bump(nodes, links, loc, height, strength=0.2, dist=0.001):
    n = N(nodes, "ShaderNodeBump", loc)
    setin(n, 'Strength', strength)
    setin(n, 'Distance', dist)
    links.new(S(height), n.inputs['Height'])
    return n


def color_ramp(nodes, links, src, loc, stops):
    n = N(nodes, "ShaderNodeValToRGB", loc)
    el = n.color_ramp.elements
    while len(el) > 1:
        el.remove(el[-1])
    el[0].position = stops[0][0]
    el[0].color = (*stops[0][1], 1.0)
    for pos, col in stops[1:]:
        e = el.new(pos)
        e.color = (*col, 1.0)
    links.new(S(src), n.inputs['Fac'])
    return n


# ---------------------------------------------------------------------------
def mat_knit(name, base=(0.850, 0.842, 0.824), hole=(0.560, 0.556, 0.548),
             cell=2.25, rand=0.92, rough=0.80, detail_scale=1.0, sheen=0.34,
             darkness=1.0, tint2=(0.72, 0.725, 0.735), tint_fac=0.0):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    uv = tc.outputs['UV']
    mp = mapping(nodes, links, uv, loc=(-1300, 200))

    # main weave lattice
    v1 = voronoi(nodes, links, mp.outputs['Vector'], (-1080, 380),
                 scale=1.0 / cell, rand=rand)
    holes = maprange(nodes, links, v1.outputs['Distance'], (-880, 380),
                     0.0, 0.30, 0.0, 1.0)
    yarn = mathn(nodes, links, 'SUBTRACT', (-700, 380), av=1.0, b=holes, clamp=True)

    # fine fibre fuzz
    fz = noise(nodes, links, mp.outputs['Vector'], (-1080, 60),
               scale=1.0 / (0.34 * detail_scale), detail=4.0, rough=0.62)
    fzi = maprange(nodes, links, fz.outputs['Fac'], (-880, 60), 0.35, 0.72, 0.0, 1.0)

    # medium thread irregularity
    th = noise(nodes, links, mp.outputs['Vector'], (-1080, -200),
               scale=1.0 / (2.6 * detail_scale), detail=3.0, rough=0.55)
    thi = maprange(nodes, links, th.outputs['Fac'], (-880, -200), 0.3, 0.75, 0.0, 1.0)

    # broad tonal variation (many cm)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -460),
                scale=1.0 / 26.0, detail=3.0, rough=0.5)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -460), 0.3, 0.72, 0.0, 1.0)

    hcol = mixrgb(nodes, links, (-520, 380), f=holes, c1=base, c2=hole)
    hcol2 = mixrgb(nodes, links, (-320, 380), f=thi, a=hcol.outputs[2],
                   c2=(min(base[0] * 0.90, 1), min(base[1] * 0.90, 1), min(base[2] * 0.92, 1)))
    hcol3 = mixrgb(nodes, links, (-120, 380), f=bigi, a=hcol2.outputs[2], c2=tint2)
    if tint_fac > 0:
        hcol3 = mixrgb(nodes, links, (80, 380), fac=tint_fac, a=hcol3.outputs[2], c2=tint2)
    links.new(hcol3.outputs[2], bsdf.inputs['Base Color'])

    # roughness
    r1 = maprange(nodes, links, yarn, (-320, 60), 0.0, 1.0, rough - 0.10, rough + 0.07)
    r2 = maprange(nodes, links, fzi, (-320, -120), 0.0, 1.0, -0.05, 0.05)
    radd = mathn(nodes, links, 'ADD', (-120, -30), a=r1.outputs['Result'],
                 b=r2.outputs['Result'], clamp=True)
    links.new(radd.outputs[0], bsdf.inputs['Roughness'])

    # bump chain
    b1 = bump(nodes, links, (-180, -320), yarn, strength=0.55, dist=0.0009)
    b2 = bump(nodes, links, (40, -320), fzi, strength=0.10, dist=0.0004)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    b3 = bump(nodes, links, (260, -320), thi, strength=0.06, dist=0.0012)
    links.new(b2.outputs['Normal'], b3.inputs['Normal'])
    links.new(b3.outputs['Normal'], bsdf.inputs['Normal'])

    setv(bsdf, 'Sheen Weight', sheen)
    setv(bsdf, 'Sheen Roughness', 0.30)
    setv(bsdf, 'Specular IOR Level', 0.32)
    setv(bsdf, 'Metallic', 0.0)
    return m


def mat_dense(name, base=(0.760, 0.760, 0.756), cell=1.35, rough=0.62,
              bump_strength=0.85, coat=0.10, sheen=0.22):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    mp = mapping(nodes, links, tc.outputs['UV'])
    v1 = voronoi(nodes, links, mp.outputs['Vector'], (-1080, 380),
                 scale=1.0 / cell, rand=0.55)
    holes = maprange(nodes, links, v1.outputs['Distance'], (-880, 380), 0.0, 0.26, 0.0, 1.0)
    yarn = mathn(nodes, links, 'SUBTRACT', (-700, 380), av=1.0, b=holes, clamp=True)
    fz = noise(nodes, links, mp.outputs['Vector'], (-1080, 60), scale=1.0 / 0.55,
               detail=4.0, rough=0.6)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -220), scale=1.0 / 22.0,
                detail=4.0, rough=0.55)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -220), 0.32, 0.7, 0.0, 1.0)

    c = mixrgb(nodes, links, (-420, 380), f=holes, c1=base,
               c2=(base[0] * 0.72, base[1] * 0.72, base[2] * 0.74))
    c = mixrgb(nodes, links, (-200, 380), f=bigi, a=c.outputs[2],
               c2=(base[0] * 1.06, base[1] * 1.06, base[2] * 1.05))
    links.new(c.outputs[2], bsdf.inputs['Base Color'])
    r = maprange(nodes, links, yarn, (-320, 60), 0.0, 1.0, rough - 0.06, rough + 0.06)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    b1 = bump(nodes, links, (-180, -320), yarn, strength=bump_strength, dist=0.0007)
    b2 = bump(nodes, links, (40, -320), fz.outputs['Fac'], strength=0.09, dist=0.0004)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    setv(bsdf, 'Coat Weight', coat)
    setv(bsdf, 'Coat Roughness', 0.35)
    setv(bsdf, 'Sheen Weight', sheen)
    setv(bsdf, 'Sheen Roughness', 0.32)
    setv(bsdf, 'Specular IOR Level', 0.35)
    return m


def mat_foam(name, base=(0.772, 0.764, 0.748)):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    uv = tc.outputs['UV']
    mp = mapping(nodes, links, uv)
    grain = noise(nodes, links, mp.outputs['Vector'], (-1080, 300), scale=1.0 / 0.55,
                  detail=3.0, rough=0.55)
    wrin = noise(nodes, links, mp.outputs['Vector'], (-1080, 20), scale=1.0 / 9.0,
                 detail=6.0, rough=0.62, dist=0.4)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -260), scale=1.0 / 55.0,
                detail=4.0, rough=0.5)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -260), 0.32, 0.7, 0.0, 1.0)
    c = mixrgb(nodes, links, (-320, -260), f=bigi, c1=base,
               c2=(base[0] * 1.045, base[1] * 1.04, base[2] * 1.03))
    c = mixrgb(nodes, links, (-140, -260), f=wrin.outputs['Fac'], a=c.outputs[2],
               c2=(base[0] * 0.93, base[1] * 0.93, base[2] * 0.935), fac=0.35)
    links.new(c.outputs[2], bsdf.inputs['Base Color'])
    r = maprange(nodes, links, wrin.outputs['Fac'], (-320, 40), 0.28, 0.72, 0.52, 0.72)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    b1 = bump(nodes, links, (-180, -320), grain.outputs['Fac'], strength=0.16, dist=0.00035)
    b2 = bump(nodes, links, (40, -320), wrin.outputs['Fac'], strength=0.13, dist=0.0011)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    setv(bsdf, 'Sheen Weight', 0.14)
    setv(bsdf, 'Sheen Roughness', 0.4)
    setv(bsdf, 'Subsurface Weight', 0.055)
    setv(bsdf, 'Subsurface Radius', (0.010, 0.009, 0.007))
    setv(bsdf, 'Specular IOR Level', 0.32)
    return m


def mat_rubber(name, base=(0.048, 0.050, 0.054)):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    mp = mapping(nodes, links, tc.outputs['UV'])
    grain = noise(nodes, links, mp.outputs['Vector'], (-1080, 300), scale=1.0 / 0.30,
                  detail=4.0, rough=0.6)
    smudge = noise(nodes, links, mp.outputs['Vector'], (-1080, 20), scale=1.0 / 6.0,
                   detail=5.0, rough=0.6)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -260), scale=1.0 / 40.0,
                detail=3.0, rough=0.5)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -260), 0.3, 0.7, 0.0, 1.0)
    c = mixrgb(nodes, links, (-320, -260), f=bigi, c1=base,
               c2=(base[0] * 1.9 + 0.010, base[1] * 1.9 + 0.010, base[2] * 1.9 + 0.011))
    links.new(c.outputs[2], bsdf.inputs['Base Color'])
    r = maprange(nodes, links, smudge.outputs['Fac'], (-320, 40), 0.25, 0.75, 0.62, 0.80)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    b1 = bump(nodes, links, (-180, -320), grain.outputs['Fac'], strength=0.22, dist=0.00022)
    b2 = bump(nodes, links, (40, -320), smudge.outputs['Fac'], strength=0.06, dist=0.0009)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    setv(bsdf, 'Sheen Weight', 0.10)
    setv(bsdf, 'Sheen Roughness', 0.45)
    setv(bsdf, 'Specular IOR Level', 0.38)
    return m


def mat_metal(name, base=(0.870, 0.878, 0.892), rough=0.20, aniso=0.0):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    n = noise(nodes, links, tc.outputs['UV'], (-1080, 200), scale=1.0 / 2.0, detail=3.0)
    r = maprange(nodes, links, n.outputs['Fac'], (-800, 200), 0.3, 0.7, rough, rough + 0.08)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    setv(bsdf, 'Base Color', base)
    setv(bsdf, 'Metallic', 1.0)
    setv(bsdf, 'Anisotropic', aniso)
    return m


def mat_simple_fabric(name, base=(0.30, 0.305, 0.315), rough=0.78, cell=1.6, sheen=0.45,
                      bump_strength=0.6):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    mp = mapping(nodes, links, tc.outputs['UV'])
    v1 = voronoi(nodes, links, mp.outputs['Vector'], (-1080, 300), scale=1.0 / cell, rand=0.8)
    holes = maprange(nodes, links, v1.outputs['Distance'], (-880, 300), 0.0, 0.28, 0.0, 1.0)
    yarn = mathn(nodes, links, 'SUBTRACT', (-700, 300), av=1.0, b=holes, clamp=True)
    fz = noise(nodes, links, mp.outputs['Vector'], (-1080, 0), scale=1.0 / 0.4,
               detail=4.0, rough=0.6)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -260), scale=1.0 / 18.0,
                detail=4.0, rough=0.55)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -260), 0.3, 0.7, 0.0, 1.0)
    c = mixrgb(nodes, links, (-400, 300), f=holes, c1=base,
               c2=(base[0] * 0.6, base[1] * 0.6, base[2] * 0.62))
    c = mixrgb(nodes, links, (-200, 300), f=bigi, a=c.outputs[2],
               c2=(base[0] * 1.5, base[1] * 1.5, base[2] * 1.5))
    links.new(c.outputs[2], bsdf.inputs['Base Color'])
    r = maprange(nodes, links, yarn, (-320, 40), 0.0, 1.0, rough - 0.07, rough + 0.07)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    b1 = bump(nodes, links, (-180, -320), yarn, strength=bump_strength, dist=0.0005)
    b2 = bump(nodes, links, (40, -320), fz.outputs['Fac'], strength=0.12, dist=0.0004)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    setv(bsdf, 'Sheen Weight', sheen)
    setv(bsdf, 'Sheen Roughness', 0.32)
    setv(bsdf, 'Specular IOR Level', 0.3)
    return m


def mat_lace(name, base=(0.905, 0.898, 0.880)):
    m, nodes, links, bsdf = new_mat(name)
    tc = texcoord(nodes)
    mp = mapping(nodes, links, tc.outputs['UV'])
    w = wave(nodes, links, mp.outputs['Vector'], (-1080, 320), scale=1.0 / 0.95,
             dist=1.2, detail=2.0, direction='X')
    w2 = wave(nodes, links, mp.outputs['Vector'], (-1080, 60), scale=1.0 / 0.42,
              dist=0.8, detail=2.0, direction='Y')
    wm = mathn(nodes, links, 'MULTIPLY', (-860, 200), a=w.outputs['Fac'], b=w2.outputs['Fac'])
    fz = noise(nodes, links, mp.outputs['Vector'], (-1080, -240), scale=1.0 / 0.6,
               detail=4.0, rough=0.6)
    big = noise(nodes, links, mp.outputs['Vector'], (-1080, -460), scale=1.0 / 30.0,
                detail=3.0, rough=0.5)
    bigi = maprange(nodes, links, big.outputs['Fac'], (-880, -460), 0.3, 0.7, 0.0, 1.0)
    c = mixrgb(nodes, links, (-520, -120), f=wm, c1=base,
               c2=(base[0] * 0.84, base[1] * 0.84, base[2] * 0.86))
    c = mixrgb(nodes, links, (-320, -120), f=bigi, a=c.outputs[2],
               c2=(base[0] * 1.0, base[1] * 1.0, base[2] * 0.99))
    links.new(c.outputs[2], bsdf.inputs['Base Color'])
    r = maprange(nodes, links, wm, (-320, 320), 0.3, 0.8, 0.76, 0.88)
    links.new(r.outputs['Result'], bsdf.inputs['Roughness'])
    b1 = bump(nodes, links, (-180, -340), wm, strength=0.30, dist=0.00035)
    b2 = bump(nodes, links, (40, -340), fz.outputs['Fac'], strength=0.10, dist=0.0003)
    links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    setv(bsdf, 'Sheen Weight', 0.5)
    setv(bsdf, 'Sheen Roughness', 0.28)
    setv(bsdf, 'Specular IOR Level', 0.3)
    return m


def build_materials():
    mats = {}
    mats['knit'] = mat_knit("Knit_Upper", base=(0.818, 0.810, 0.792),
                            hole=(0.545, 0.540, 0.532), cell=2.30, rough=0.80,
                            sheen=0.38, tint2=(0.76, 0.765, 0.775))
    mats['panel_dense'] = mat_dense("Panel_Dense", base=(0.690, 0.693, 0.697),
                                    cell=1.30, rough=0.60, bump_strength=0.9, coat=0.12)
    mats['eyestay'] = mat_dense("Eyestay", base=(0.300, 0.305, 0.315), cell=1.15,
                                rough=0.66, bump_strength=1.0, coat=0.06, sheen=0.3)
    mats['collar'] = mat_simple_fabric("Collar_Pad", base=(0.215, 0.220, 0.230),
                                       rough=0.80, cell=1.5, sheen=0.5, bump_strength=0.75)
    mats['tongue'] = mat_knit("Tongue", base=(0.735, 0.730, 0.718),
                              hole=(0.495, 0.492, 0.486), cell=1.7, rough=0.82,
                              sheen=0.42, tint2=(0.66, 0.66, 0.67))
    mats['lace'] = mat_lace("Lace_Cord")
    mats['metal'] = mat_metal("Eyelet_Metal", base=(0.880, 0.886, 0.898), rough=0.17)
    mats['metal_soft'] = mat_metal("Reflective", base=(0.760, 0.775, 0.800), rough=0.30,
                                   aniso=0.3)
    mats['foam'] = mat_foam("Midsole_Foam")
    mats['rubber'] = mat_rubber("Outsole_Rubber")
    mats['webbing'] = mat_simple_fabric("Webbing", base=(0.235, 0.240, 0.250),
                                        rough=0.76, cell=1.2, sheen=0.4)
    mats['thread'] = mat_simple_fabric("Thread", base=(0.840, 0.832, 0.815),
                                       rough=0.62, cell=0.9, sheen=0.4, bump_strength=0.4)
    mats['liner'] = mat_dense("Liner", base=(0.400, 0.405, 0.415), cell=1.40,
                              rough=0.78, bump_strength=0.70, coat=0.04, sheen=0.35)
    return mats
