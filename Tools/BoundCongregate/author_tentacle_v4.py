"""Repaint a continuous shoulder collar rather than a single fixed seam row."""
from pathlib import Path
import bpy,numpy as np,json
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'TentacleWhipV4'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TentacleWhipV3/BoundCongregate_TentacleV3.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
ob=bpy.data.objects['BC_Flesh'];body=ob.vertex_groups['body'];fixed=blended=0
for v in ob.data.vertices:
    p=np.array((v.co.x/2.25,v.co.y/2.25,v.co.z/2.25-.532125))
    r=np.linalg.norm((p-np.array([.377,.063,.220]))/np.array([.155,.155,.145]))
    f=np.clip((1.75-r)/.75,0,1);f=float(f*f*(3-2*f))
    if f<=0:continue
    old={g.group:g.weight for g in v.groups}
    for group,w in old.items():ob.vertex_groups[group].add([v.index],w*(1-f),'REPLACE')
    body.add([v.index],f+old.get(body.index,0)*(1-f),'REPLACE')
    if f>=.99999:fixed+=1
    else:blended+=1
report={'revision':'TentacleWhipV4','fixed_collar_vertices':fixed,'gradient_vertices':blended,'topology':'V3 original continuous root retained'}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_TentacleV4.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_TentacleV4.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
print(json.dumps(report),flush=True)
