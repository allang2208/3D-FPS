"""201 sight clearance and connected trigger housing. Retains the A40 assembly."""
from pathlib import Path
O=Path(__file__).parent;S=O.parent;(O/'Exports').mkdir(exist_ok=True)
helpers=(S/'Assembly40/model.py').read_text().split('# Preserve the edited receiver')[0]
helpers=helpers.replace('HardSurface39/LMG201_HardSurface39.blend','Assembly40/LMG201_Assembly40.blend').replace(".replace('M_LMG201_R38_','M_LMG201_A40_')",".replace('M_LMG201_R38_','M_LMG201_S41_')")
exec(compile(helpers,str(O/'model.py'),'exec'),globals())
previous=json.loads((S/'Assembly40/model.json').read_text())
parts=[bpy.data.objects[n] for n in previous['parts'] if n not in ['TriggerGuard_A40','Trigger_A40']]
for name in ['TriggerGuard_A40','Trigger_A40','RearSight_A40']:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

# The current receiver underside is z=.0026 on its web and z=.0042/.0046
# on the side flanges. A40 stopped at -.003, leaving an actual vertical gap.
guard=ring_slab('S41_ConnectedGuard',round_profile(-.075,-.010,-.043,.0045,.007),round_profile(-.0715,-.0135,-.0395,-.0010,.005),.0057,coat)
# A visible blade emerges through a real bounded opening in the upper web.
slot=box('S41_TriggerExitCut',(cx,-.0355,.003),(.0080,.016,.012),inside,.0006)
boolean(guard,slot,'DIFFERENCE');finish(guard,.00015)
housing=[guard]
for y0,y1 in [(-.075,-.063),(-.023,-.010)]:
 housing.append(slab('S41_GuardShoulder',[(y0,-.005),(y1,-.005),(y1,.0030),(y1-.002,.0062),(y0+.002,.0062),(y0,.0030)],.0095,coat,.00055))
parts.append(joined('TriggerGuard_S41',housing))
# Root above the visible slot is inside the receiver. Native trigger animation
# and its reference transform are retained; only the upper blade is extended.
trigger=slab('S41_ConnectedTrigger',[(-.030,.012),(-.030,.005),(-.034,-.002),(-.034,-.008),(-.038,-.012),(-.042,-.018),(-.045,-.025),(-.045,-.030),(-.042,-.033),(-.046,-.032),(-.049,-.029),(-.049,-.023),(-.046,-.016),(-.041,-.009),(-.040,-.003),(-.038,.005),(-.038,.012)],.0031,satin,.00045)
trigger_root=poses['clips']['idle']['bones']['WPN_Trigger']['p']
hub=cylinder('S41_TriggerRootHub',(trigger_root[0],-trigger_root[1],trigger_root[2]),.0042,.007,'X',satin)
trigger=joined('S41_TriggerWithRoot',[trigger,hub],None)
trigger_mat=satin.copy();trigger_mat.name='M_LMG201_Trigger_S41';trigger.data.materials.clear();trigger.data.materials.append(trigger_mat)
for p in trigger.data.polygons:p.material_index=0
unpose(trigger,'WPN_Trigger');parts.append(joined('Trigger_S41',[trigger],'WPN_Trigger'))

# The aim markers in A_LMG201_aim are z=.11361999, not the A40 leaf's
# .1151 notch floor. Clear the projected front ring around that existing line.
rear_point=poses['clips']['aim']['bones']['WPN_RearSight']['p'];front_point=poses['clips']['aim']['bones']['WPN_FrontSight']['p']
aim_z=rear_point[2];pivot_z=.0855;opening_floor=aim_z-pivot_z-.0062
head=[]
for side in [-1,1]:
 ear=slab('S41_RearSightEar',[(-.004,0),(.004,0),(.004,.0338),(.0028,.0352),(-.0028,.0352),(-.004,.0338)],.00145,coat,.0005);displaced(ear,side*.010);head.append(ear)
# Recess the middle down to a broad rounded U. No opaque plate crosses ADS.
profile=[(-.008,.004),(.008,.004),(.008,.0315),(.0054,.0315),(.0054,opening_floor+.0013),(.0051,opening_floor+.0005),(.0043,opening_floor),(-.0043,opening_floor),(-.0051,opening_floor+.0005),(-.0054,opening_floor+.0013),(-.0054,.0315),(-.008,.0315)]
vs=[(cx+x,y,z) for y in [-.0018,.0018] for x,z in profile];n=len(profile);fs=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
head+=[shape('S41_OpenNotchLeaf',vs,fs,coat,.00025),box('S41_RearLowerBridge',(cx,0,.0035),(.019,.010,.007),coat,.0006),cylinder('S41_RearPivot',(cx,0,.010),.0028,.023,'X',satin)]
rear=joined('RearSight_S41',head,None)
for v in rear.data.vertices:v.co.x-=cx
select([rear]);rearfbx=O/'Exports/SM_LMG201_S41_RearSight.fbx';bpy.ops.export_scene.fbx(filepath=str(rearfbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
rear.hide_render=True;rear.hide_set(True)
select(parts+[rig]);fbx=O/'Exports/SK_LMG201_S41_Parts.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_SightFinish41.blend'))
notes={'native_tracks_changed':False,'aim_rear_root_ue_m':rear_point,'aim_front_root_ue_m':front_point,'old_notch_floor_m':.1151,'new_notch_floor_m':pivot_z+opening_floor,'notch_width_m':.0108,'guard_top_m':.0045,'shoulder_top_m':.0062,'trigger_root_top_idle_m':.012}
(O/'model.json').write_text(json.dumps({'body_fbx':str(fbx),'rear_fbx':str(rearfbx),'parts':[o.name for o in parts],'notes':notes},indent=2));print('S41_AUTHORED',json.dumps(notes),flush=True)
