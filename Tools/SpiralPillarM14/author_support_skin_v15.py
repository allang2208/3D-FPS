"""Apply the local support repair to the editable V14 mesh without changing poses."""
from pathlib import Path
import bpy, json
import numpy as np
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004');OUT=ROOT/'ProductionV15'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV14/Authoring/M14_SoftCollapse_v14.blend'))
rig=bpy.data.objects['M14_Rig'];obj=bpy.data.objects['M14_SoftDeathMesh']
rig.animation_data.action=None;bpy.context.scene.frame_set(0)
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
data=np.load(OUT/'Records/support_skin.npz');changed,bones,weights=data['changed'],data['bones'],data['weights']
for group in obj.vertex_groups:group.remove(changed.tolist())
for slot in range(8):
    active=np.flatnonzero(weights[:,slot]>0)
    keys=bones[active,slot]*65536+np.rint(weights[active,slot]*65535).astype(np.int64)
    order=np.argsort(keys);active,keys=active[order],keys[order]
    values,starts=np.unique(keys,return_index=True);ends=np.r_[starts[1:],len(keys)]
    for value,start,end in zip(values,starts,ends):
        obj.vertex_groups[int(value//65536)].add(changed[active[start:end]].tolist(),float(value%65536)/65535.,'REPLACE')
obj['support_skin_revision']='V15: low material patches follow local support tissue, eight-slot smooth transition.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M14_SupportSkin_v15.blend'),compress=True)
report={'complete':True,'source':'ProductionV14','changed_source_vertices':len(changed),
        'source_triangles':len(obj.data.polygons),'geometry_removed':0,'animation_changed':False,
        'death_shapes_changed':False,'runtime_tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_V15_SOURCE_SAVED',flush=True)
