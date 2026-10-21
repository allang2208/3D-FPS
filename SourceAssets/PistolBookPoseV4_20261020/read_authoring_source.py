"""Read the saved contact author scene; never opens UE or edits its assets."""
import bpy, json
import numpy as np
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
source = ROOT/'SourceAssets/M1911Contact20260913/M1911_Contact_Editable.blend'
try:
    bpy.ops.wm.open_mainfile(filepath=str(source))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):
        raise
rig = bpy.data.objects['SK_M1911_Manny']
rig.data.pose_position = 'POSE'
result = {'source': str(source), 'rest': {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}, 'poses': {}}
for kind in ('idle', 'aim'):
    action = bpy.data.actions['M1911_Contact_'+kind]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    result['poses'][kind] = {b.name: [list(row) for row in b.matrix] for b in rig.pose.bones}
    # Rollout snapshots intentionally contain only skin. Read the actual gun
    # from the saved contact scene, including its accepted component motion.
    vertices=[];triangles=[];uvs=[];materials=[];slots=[]
    deps=bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.collections['M1911_LOW'].objects:
        if obj.type!='MESH':continue
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        xf=rig.matrix_world.inverted()@evaluated.matrix_world
        start=len(vertices);vertices.extend([list(xf@v.co) for v in mesh.vertices])
        for t in mesh.loop_triangles:
            triangles.append([start+i for i in t.vertices])
            uvs.append([list(mesh.uv_layers.active.data[i].uv) for i in t.loops])
            name=mesh.materials[t.material_index].name
            if name not in materials:materials.append(name)
            slots.append(materials.index(name))
        evaluated.to_mesh_clear()
    np.savez_compressed(OUT/('gun_'+kind+'.npz'),X=np.array(vertices),T=np.array(triangles),UV=np.array(uvs),slots=np.array(slots))
    result['gun_materials']=materials
(OUT/'contact_source.json').write_text(json.dumps(result), encoding='utf-8')
print('CONTACT_SOURCE_SAVED', flush=True)
