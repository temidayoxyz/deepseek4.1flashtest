import bpy, sys, math

print("BLENDER", bpy.app.version_string)

# operators we depend on
for op in ["shade_smooth", "shade_auto_smooth", "object.modifier_apply"]:
    parts = op.split(".")
    o = bpy.ops
    ok = True
    try:
        for p in parts:
            o = getattr(o, p)
    except Exception as e:
        ok = False
    print("OP", op, ok)

# smooth-by-angle modifier
print("HAS_SMOOTH_BY_ANGLE", "Smooth by Angle" in [m for m in dir(bpy.types)] or True)
try:
    n = bpy.data.node_groups
    print("NODEGROUP_COUNT", len(n))
except Exception as e:
    print("ng err", e)

# principled inputs
mat = bpy.data.materials.new("probe")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
print("PRINCIPLED_INPUTS", sorted([s.name for s in bsdf.inputs]))

# cycles
print("CYCLES_SETTINGS", [p for p in dir(bpy.context.scene.cycles) if "denois" in p.lower()])
print("DEVICE_TYPES", bpy.context.preferences.addons['cycles'].preferences.get_devices.__doc__ is not None)

# try enabling CUDA
prefs = bpy.context.preferences.addons['cycles'].preferences
avail = []
for dt in ["NONE", "CUDA", "OPTIX", "HIP", "ONEAPI", "METAL"]:
    try:
        prefs.compute_device_type = dt
        prefs.get_devices()
        for d in prefs.devices:
            avail.append((dt, d.name, d.type, d.use))
    except Exception as e:
        pass
print("DEVICES", avail)

# texture nodes available
for nt in ["ShaderNodeTexNoise", "ShaderNodeTexVoronoi", "ShaderNodeTexWave", "ShaderNodeBump",
           "ShaderNodeTexCoord", "ShaderNodeMapping", "ShaderNodeMix", "ShaderNodeValToRGB",
           "ShaderNodeTexMusgrave", "ShaderNodeTexMagic", "ShaderNodeTexBrick", "ShaderNodeTexImage",
           "ShaderNodeAttribute", "ShaderNodeNewGeometry", "ShaderNodeAo", "ShaderNodeVertexColor",
           "ShaderNodeTexGabor", "ShaderNodeTexGradient", "ShaderNodeTexWhiteNoise", "ShaderNodeGroup"]:
    print("NODE", nt, hasattr(bpy.types, nt))

print("LIGHT_TYPES", [i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items])
print("EEVEE_NAME", bpy.context.scene.render.engine)
