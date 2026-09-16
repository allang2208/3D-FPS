"""Print which refraction/transmission switches this Blender build exposes.

Blender renamed these between legacy EEVEE and EEVEE Next, and a wrong guess is
silently swallowed by the try/except guards in the render scripts.

Usage:
    blender --background --factory-startup --python probe_eevee_refraction.py
"""

import bpy

mat = bpy.data.materials.new("probe")
mat.use_nodes = True
keywords = ("refract", "transmission", "blend", "surface_render", "raytrace", "ssr", "alpha")
print("MAT_PROPS=" + ",".join(sorted(a for a in dir(mat) if any(k in a.lower() for k in keywords))))

eevee = bpy.context.scene.eevee
print("EEVEE_PROPS=" + ",".join(sorted(a for a in dir(eevee) if any(
    k in a.lower() for k in ("raytrac", "ssr", "refract", "sss")))))

bsdf = mat.node_tree.nodes.get("Principled BSDF")
print("BSDF_TRANSMISSION_SOCKET=" + ",".join(
    s.name for s in bsdf.inputs if "transmission" in s.name.lower()))
