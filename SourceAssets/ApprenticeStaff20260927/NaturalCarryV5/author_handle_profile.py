"""Extract the four real grip surfaces for skin-contact authoring. No render."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'apprentice_staff_modular.blend'))
names=['SM_Staff_grip_lining_'+n for n in ('false','alloy_grip','pine_grip','sandalwood_grip')]
deps=bpy.context.evaluated_depsgraph_get()
trees=[BVHTree.FromObject(bpy.data.objects[n],deps) for n in names]
z_values=[22+i*.5 for i in range(41)]
profiles=[]
for z in z_values:
    ring=[]
    for i in range(96):
        angle=math.tau*i/96;direction=Vector((math.cos(angle),math.sin(angle),0))
        radii=[]
        for tree in trees:
            hit=tree.ray_cast(Vector((0,0,z)),direction,12)
            if hit[0] is not None:radii.append(hit[0].xy.length)
        ring.append(max(radii) if radii else 2.98)
    profiles.append(ring)
(O/'handle-profile.json').write_text(json.dumps({'units':'cm','grip_z':32,'z':z_values,'radii':profiles,
    'sources':names,'purpose':'authoring envelope of the factory and replacement grip surfaces'},indent=2),encoding='utf-8')
print('STAFF_V5_HANDLE_PROFILE_AUTHORED')
