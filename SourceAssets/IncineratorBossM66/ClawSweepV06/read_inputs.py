import bpy,json,numpy as np
from pathlib import Path

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66')
OUT=BASE/'ClawSweepV06/Records'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SurfaceLifeV05/Authoring/M66_surface_life_v05.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body']
rig.animation_data_clear()
for p in rig.pose.bones:p.matrix_basis.identity()
bpy.context.view_layer.update()
names=['Bone_%03d'%i for i in (0,1,7,6,5,20,28,27,26,25,24,37,36,32,31,30,57,61,65,69,73)]
bones={n:{'parent':rig.data.bones[n].parent.name if rig.data.bones[n].parent else None,
          'head':list(rig.data.bones[n].head_local),'tail':list(rig.data.bones[n].tail_local)} for n in names}
positions=np.array([v.co[:] for v in mesh.data.vertices]);groups=[g.name for g in mesh.vertex_groups]
arm_names=set()
for b in rig.data.bones:
    p=b
    while p:
        if p.name=='Bone_027':arm_names.add(b.name);break
        p=p.parent
arm_mass=np.array([sum(g.weight for g in v.groups if groups[g.group] in arm_names) for v in mesh.data.vertices])
body=positions[arm_mass<.03];hand=positions[np.array([sum(g.weight for g in v.groups if groups[g.group] in {'Bone_025','Bone_036','Bone_057','Bone_061','Bone_065','Bone_069','Bone_073'}) for v in mesh.data.vertices])>.5]
bands=[]
for lo in np.arange(.5,3.8,.25):
    p=body[(body[:,2]>=lo)&(body[:,2]<lo+.25)]
    if len(p):bands.append({'z':[float(lo),float(lo+.25)],'min':p.min(0).tolist(),'max':p.max(0).tolist()})
report={'bones':bones,'arm_bones':sorted(arm_names),'body_bands':bands,'mesh_matrix':list(map(list,mesh.matrix_world)),
        'rig_matrix':list(map(list,rig.matrix_world)),'hand_bounds':[hand.min(0).tolist(),hand.max(0).tolist()]}
report['weighted_bounds']={}
for name in ('Bone_027','Bone_026','Bone_025','Bone_037','Bone_036'):
    group=mesh.vertex_groups[name].index
    selected=positions[[any(g.group==group and g.weight>.5 for g in v.groups) for v in mesh.data.vertices]]
    report['weighted_bounds'][name]={'vertices':len(selected),'bounds':[selected.min(0).tolist(),selected.max(0).tolist()] if len(selected) else None}
(OUT/'pose_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_POSE_INPUTS_SAVED',flush=True)
