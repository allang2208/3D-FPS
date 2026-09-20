"""AKM-only free-drop and new-drum contact, retaining each grip's return motion."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parents[1]
manifest=json.loads((O/'source_manifest.json').read_text())
contact=json.loads((O/'contact_fit.json').read_text())
grasp=Matrix(contact['hand_in_mag'])
bpy.context.preferences.filepaths.save_version=0
def smooth(x): x=max(0,min(1,x));return x*x*(3-2*x)
def mix(a,b,t):
 al,aq,az=a.decompose();bl,bq,bz=b.decompose()
 return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),az.lerp(bz,t))
def solve_arm(p,H,weight):
 old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_l','lowerarm_l','hand_l'
 A=old[un].translation.copy();T=H.translation
 l1=(old[fn].translation-A).length;l2=(old[hn].translation-old[fn].translation).length
 axis=(T-A).normalized();dist=(T-A).length
 reach=max(0,dist-(l1+l2-.006))
 A+=axis*reach;p['clavicle_l'].translation+=axis*reach
 axis=(T-A).normalized();dist=max(.001,(T-A).length)
 pole=old[fn].translation-A;pole-=axis*pole.dot(axis)
 # Preserve the source elbow side, introducing the wrist-directed forearm
 # plane gently. Whole bone segments and their twist children move together.
 desired=(H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation)).normalized()
 natural=T-desired*l2-A;natural-=axis*natural.dot(axis)
 if natural.length>.0001 and pole.dot(natural)>0:pole=pole.normalized().lerp(natural.normalized(),.55*weight)
 pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist)
 E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 for n,position,direction,old_direction in [
  (un,A,E-A,old[fn].translation-old[un].translation),
  (fn,E,T-E,old[hn].translation-old[fn].translation)]:
  q=old_direction.normalized().rotation_difference(direction.normalized())@old[n].to_quaternion()
  if n==fn:
   # Let the forearm roll follow the upturned palm, keeping the complete Manny
   # segment and its helpers together rather than twisting only the wrist.
   hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
   rest_forearm=(rest[hn].translation-rest[fn].translation).normalized()
   aligned=hand_deform@rest_forearm
   palm_roll=aligned.rotation_difference(direction.normalized())@hand_deform@rest[fn].to_quaternion()
   q=q.slerp(palm_roll,weight)
  p[n]=Matrix.LocRotScale(position,q,old[n].to_scale())
 for parent in [un,fn]:
  for n in [parent.replace('_l','_twist_01_l'),parent.replace('_l','_twist_02_l')]:
   if n in p:p[n]=mix(p[parent]@old[parent].inverted()@old[n],p[parent]@rest[parent].inverted()@rest[n],weight)
 p[hn]=H

# The installed normal clip supplies the accepted individual finger shape.
bpy.ops.wm.open_mainfile(filepath=str(Path(manifest['base/drum_reload']['source'][0]).with_suffix('.blend')))
rig=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(208)
digit_names=[b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))]
donor={n:rig.pose.bones[n].matrix_basis.to_quaternion() for n in digit_names}
if 'finger_basis' in contact:donor={n:Quaternion(contact['finger_basis'][n]) for n in digit_names}
open_hand={n:Quaternion(contact.get('open_finger_basis',contact['finger_basis'])[n]) for n in digit_names}
report={}
selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for key,meta in manifest.items():
 variant,clip=key.split('/')
 if selected and variant not in selected:continue
 source=Path(meta['source'][0]).with_suffix('.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 old_action=r.animation_data.action;end=s.frame_end
 rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 lr={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
 arm=['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']
 names=arm+digit_names
 release_begin=220 if clip.endswith('empty') else 236
 release_end=256 if clip.endswith('empty') else 278
 samples=[];bases=[]
 for f in range(release_end+1):
  s.frame_set(f);samples.append({b.name:b.matrix.copy() for b in r.pose.bones});bases.append({n:r.pose.bones[n].matrix_basis.copy() for n in names})
 start=samples[12]['WPN_root'].inverted()@samples[12]['hand_l']
 pickup=samples[112]['WPN_root'].inverted()@samples[112]['WPN_SOCKET_Magazine']@grasp
 waypoint=mix(start,pickup,.30);waypoint.translation=Vector((max(.145,start.translation.x+.105),start.translation.y+.030,start.translation.z-.100))
 action=old_action.copy();action.name='A_AKM_'+('' if variant=='base' else variant+'_')+clip+'_'+contact['revision'];action.use_fake_user=True
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 output={};previous={}
 for f in range(13,release_end):
  old=samples[f];p={n:m.copy() for n,m in old.items()};base=bases[f];root=old['WPN_root']
  if f<36:H=root@mix(start,waypoint,smooth((f-12)/24))
  elif f<100:H=root@mix(waypoint,pickup,smooth((f-36)/64))
  elif f<112:H=mix(root@pickup,old['WPN_SOCKET_Magazine']@grasp,smooth((f-100)/12))
  else:H=old['WPN_SOCKET_Magazine']@grasp
  release_phase=max(0,min(1,(f-release_begin)/(release_end-release_begin)))
  release=smooth(release_phase)
  if release_phase>0:
   clear=H.copy();clear.translation+=old['WPN_SOCKET_Magazine'].to_3x3()@Vector((.095,.035,-.040))
   H=mix(H,clear,smooth(release_phase/.4)) if release_phase<.4 else mix(clear,old['hand_l'],smooth((release_phase-.4)/.6))
  weight=smooth((f-12)/24)*(1-release);solve_arm(p,H,weight)
  row={}
  for n in names:
   loc,q,scale=base[n].decompose()
   if n in digit_names:
    delay={'thumb':0,'index':3,'middle':5,'ring':7,'pinky':9}[n.split('_')[0]]
    q=bases[12][n].to_quaternion().slerp(open_hand[n],smooth((f-26-delay)/40))
    q=q.slerp(donor[n],smooth((f-76-delay)/27))
    # Release the curled fingers during initial withdrawal before returning
    # to this grip variant's original hand pose.
    q=q.slerp(open_hand[n],smooth(release_phase/.4))
    q=q.slerp(base[n].to_quaternion(),smooth((release_phase-.4)/.6))
   else:
    local=lr[n].inverted()@p[parents[n]].inverted()@p[n];q=local.to_quaternion()
    if n=='clavicle_l':loc=local.translation
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();row[n]=(loc,q,scale)
  output[f]=row
 curves={fc.data_path+'#'+str(fc.array_index):fc for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
 for n in names:
  for prop,index,count in [('rotation_quaternion',1,4)]+([('location',0,3)] if n=='clavicle_l' else []):
   for axis in range(count):
    fc=curves[f'pose.bones["{n}"].{prop}#{axis}']
    for k in fc.keyframe_points:
     f=round(k.co.x)
     if f in output:k.co.y=output[f][n][index][axis];k.interpolation='LINEAR'
    fc.update()
  # Keep quaternion signs continuous across the unchanged entry/exit keys too.
  qcurves=[curves[f'pose.bones["{n}"].rotation_quaternion#{axis}'] for axis in range(4)]
  preceding=None
  for index in range(len(qcurves[0].keyframe_points)):
   values=Quaternion(tuple(fc.keyframe_points[index].co.y for fc in qcurves))
   if preceding is not None and preceding.dot(values)<0:
    values.negate()
    for axis,fc in enumerate(qcurves):fc.keyframe_points[index].co.y=values[axis]
   preceding=values
  for fc in qcurves:fc.update()
 # Editable sources carry the current textured drum rather than the old shell.
 with bpy.data.libraries.load(str(O.parent/'LargeDrumUpgrade20260920/AKM/Drum_Integrated.blend'),link=False) as (src,dst):dst.objects=['SM_AKM_LargeDrum_Upgrade']
 model=dst.objects[0];preview=bpy.data.objects.get('SM_AKM_drum')
 if preview:
  preview.data=model.data.copy();preview.animation_data_clear()
  for f,hidden in [(0,False),(36,True),(112,False)]:
   preview.hide_render=hidden;preview.hide_viewport=hidden
   preview.keyframe_insert('hide_render',frame=f);preview.keyframe_insert('hide_viewport',frame=f)
 bpy.data.objects.remove(model,do_unlink=True)
 s.render.fps=120;s.frame_start=0;s.frame_end=end;s.frame_set(0)
 folder=O/variant;folder.mkdir(exist_ok=True);name='A_AKM_'+('' if variant=='base' else variant+'_')+clip
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'.blend')))
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(folder/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[key]={'source':str(source),'revision':contact.get('revision','FreeDropV1'),'asset':'/Game/Weapons/AKMDrumFreeDrop20260920/'+variant+'/'+name,'fbx':str(folder/(name+'.fbx')),'duration':end/120,'sample_rate':120,'free_drop_frame':36,'pickup_frame':112,'contact_release_frames':[release_begin,release_end],'preserved':'right arm, weapon/mechanical tracks, original return after contact release, bone lengths, scales, timing','game_tested':False}
 (O/'build_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('AKM_FREE_DROP_AUTHORED',key,flush=True)
print('AKM_FREE_DROP_AUTHORING_COMPLETE',len(report),flush=True)
