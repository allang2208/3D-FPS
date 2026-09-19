import bpy, json
from pathlib import Path
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4ReloadFinger20260909/M4_Reload_FingerCurl.blend')
rig=bpy.data.objects['SK_M4_Infima']
report={'m4_objects':[], 'm4_bones':{}, 'actions':[]}
for o in rig.children:
    if o.type!='MESH':continue
    points=[v.co for v in o.data.vertices]
    report['m4_objects'].append({'name':o.name,'groups':[g.name for g in o.vertex_groups],
        'bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]})
a=bpy.data.actions['M4_idle'];rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
for n in ['WPN_root','WPN_bolt','WPN_SOCKET_Magazine','hand_l','lowerarm_l','upperarm_l','hand_r']:
    b=rig.pose.bones[n];report['m4_bones'][n]={'head':list(b.head),'tail':list(b.tail),'matrix':[list(r) for r in b.matrix]}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='E:/3d/3-dfps/assets/models/hk416/hk416.glb')
report['hk_objects']=[{'name':o.name,'type':o.type,'bones':[b.name for b in o.data.bones] if o.type=='ARMATURE' else []} for o in bpy.data.objects]
report['hk_actions']=[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions]
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HK416_reference.blend'))
(OUT/'source_probe.json').write_text(json.dumps(report,indent=2))
print('SOURCE_PROBE_COMPLETE')
