import bpy,json,pathlib
R=pathlib.Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.data.bones.get('WPN_root'))
actions=[{'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions]
print('ACTIONS',json.dumps(actions))
print('OBJECTS',json.dumps([(o.name,o.type) for o in bpy.context.scene.objects if o.type in ['ARMATURE','MESH']]))
a=bpy.data.actions.get('M4_idle')
if a:
 r.animation_data_create();r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
 bpy.context.scene.frame_set(int(a.frame_range[0]));bpy.context.view_layer.update()
names=['root','WPN_root','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','clavicle_l','clavicle_r']
report={'rig':r.name,'action':a.name if a else None,'fps':bpy.context.scene.render.fps/bpy.context.scene.render.fps_base,'bones':{},'bone_names':[b.name for b in r.data.bones]}
grip=bpy.data.objects['M4_Grip Default Unreal_Export'];xf=r.data.bones['WPN_root'].matrix_local.inverted()@r.matrix_world.inverted()@grip.matrix_world
gv=[xf@v.co for v in grip.data.vertices]
report['donor_grip_bounds']=[[min(v[k] for v in gv) for k in range(3)],[max(v[k] for v in gv) for k in range(3)]]
for name in names:
 b=r.pose.bones.get(name)
 if b:report['bones'][name]={'head':list(b.head),'tail':list(b.tail),'pose':[list(row) for row in b.matrix],'rest':[list(row) for row in b.bone.matrix_local]}
(R/'hands_source.json').write_text(json.dumps(report,indent=2))
print('BONES',json.dumps({k:{'head':v['head'],'tail':v['tail']} for k,v in report['bones'].items()}))
