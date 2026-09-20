"""Reuse the currently installed M4 wrapped-magazine contact, not its retired fingers.
Only the M16 left reload chain is replaced. Charging-hand/mechanical clocks remain.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;bpy.context.preferences.filepaths.save_version=0
def smooth(a,b,t):
 x=max(0.,min(1.,(t-a)/(b-a)));return x*x*(3-2*x)
def sample(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
donors={};donorrest={}
for clip,end in [('reload',126),('reload_empty',162)]:
 bpy.ops.wm.open_mainfile(filepath=str(S/'ExtMagContact20260919'/('A_M4_ExtContact_'+clip+'.blend')),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];a=r.animation_data.action
 donors[clip]=[sample(r,a,k*.5) for k in range(end*2+1)]
 donorrest[clip]={b.name:b.matrix_local.copy() for b in r.data.bones}
shift=Vector(json.loads((S/'M16Gameplay20260919/build.json').read_text())['magazine_contact_shift_m']);report={}
for family in ['base','vertical','canted','prism','angled']:
 file=S/'M16Gameplay20260919/M16_Manny_Editable.blend' if family=='base' else S/'M16UniversalAttachments20260920'/('M16_'+family+'_Animations_Editable.blend')
 bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest};left=[n for n in rest if n.endswith('_l')]
 for clip,end in [('reload',126),('reload_empty',162)]:
  source=bpy.data.actions['M16_'+('' if family=='base' else family+'_')+clip];poses=[]
  for j in range(end*2+1):
   f=j*.5;p=sample(r,source,f);old={n:m.copy() for n,m in p.items()}
   begin,full,release,done=(30,43,95,108) if clip=='reload' else (25,35,80,100)
   w=smooth(begin,full,f)*(1-smooth(release,done,f))
   if w:
    # The empty M16 has already left M4's slap branch at frame 88.
    donor=donors[clip][j] if clip=='reload' or f<=88 else donors['reload'][round((98+(f-88)*28/23)*2)]
    sourceclip=clip if clip=='reload' or f<=88 else 'reload';dr=donorrest[sourceclip]
    # Magazine deformation, not the root: normal toss trajectories differ.
    binding=rest['WPN_root']@Matrix.Translation(shift)@dr['WPN_root'].inverted()
    delta=p['WPN_SOCKET_Magazine']@rest['WPN_SOCKET_Magazine'].inverted()@binding@dr['WPN_SOCKET_Magazine']@donor['WPN_SOCKET_Magazine'].inverted()
    target={n:delta@donor[n] for n in left}
    fingers=[n for n in left if n.startswith(('hand','index','middle','ring','pinky','thumb'))]
    hl,hq,hs=old['hand_l'].decompose();tl,tq,_=target['hand_l'].decompose();p['hand_l']=Matrix.LocRotScale(hl.lerp(tl,w),hq.slerp(tq,w),hs)
    for n in fingers:
     if n=='hand_l':continue
     parent=parents[n];a=old[parent].inverted()@old[n];b=(target[parent] if parent in target else old[parent]).inverted()@target[n]
     loc,rot,scale=a.decompose();dest,q,_=b.decompose()
     p[n]=p[parent]@Matrix.LocRotScale(loc,rot.slerp(q,w),scale)
    # Reuse M4 contact fitting: rotate full arm segments and their helper
    # bones together, keeping lengths and the donor's wrist/finger local pose.
    shoulder=old['upperarm_l'].translation;elbow=old['lowerarm_l'].translation;wrist=old['hand_l'].translation;goal=p['hand_l'].translation
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length
    def aimed(oldm,oldend,start,end):return Matrix.LocRotScale(start,(oldend-oldm.translation).rotation_difference(end-start)@oldm.to_quaternion(),oldm.to_scale())
    if (goal-shoulder).length>l1+l2-.004:
     clav=old['clavicle_l'];c=clav.translation;radius=(shoulder-c).length;distance=(goal-c).length;axis=(goal-c).normalized();cosine=max(-1,min(1,(radius*radius+distance*distance-(l1+l2-.004)**2)/(2*radius*distance)));side=shoulder-c-axis*(shoulder-c).dot(axis);side.normalize();newshoulder=c+axis*(radius*cosine)+side*radius*math.sqrt(max(0,1-cosine*cosine));p['clavicle_l']=aimed(clav,shoulder,c,newshoulder);shoulder=newshoulder
    axis=(goal-shoulder).normalized();distance=min((goal-shoulder).length,l1+l2-1e-6);pole=elbow-shoulder-axis*(elbow-shoulder).dot(axis);pole.normalize();reach=(l1*l1-l2*l2+distance*distance)/(2*distance);ne=shoulder+axis*reach+pole*math.sqrt(max(0,l1*l1-reach*reach))
    du=aimed(old['upperarm_l'],elbow,shoulder,ne)@old['upperarm_l'].inverted();dl=aimed(old['lowerarm_l'],wrist,ne,goal)@old['lowerarm_l'].inverted()
    for n in left:
     if n.startswith('upperarm'):p[n]=du@old[n]
     elif n.startswith('lowerarm'):p[n]=dl@old[n]
   poses.append(p)
  a=bpy.data.actions.new('M16_Refined_'+family+'_'+clip);a.use_fake_user=True;r.animation_data.action=a
  for b in r.pose.bones:
   b.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
  for n in rest:
   values=[];previous=None
   for p in poses:
    m=local[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=m.decompose()
    if previous and previous.dot(q)<0:q.negate()
    previous=q.copy();values.append((loc,q,scale))
   for prop,field,num in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(num):
     c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(poses));c.keyframe_points.foreach_set('co',[v for j,row in enumerate(values) for v in [j*.5,row[field][axis]]])
     for k in c.keyframe_points:k.interpolation='LINEAR'
     c.update()
  name='A_M16_'+('' if family=='base' else family+'_')+clip;folder=O/'Animations'/family;folder.mkdir(parents=True,exist_ok=True);fbx=folder/(name+'.fbx')
  scene.render.fps=60;scene.frame_start=0;scene.frame_end=end;scene.frame_set(76);bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
  dest='/Game/Weapons/M16A2/'+('Gameplay20260919/Animations' if family=='base' else 'UniversalAttachments20260920/Animations/'+family)
  report[family+'/'+clip]={'name':name,'file':str(fbx),'folder':dest,'duration':end/60,'action':a.name,'donor':'ExtMagContact20260919','contact_window':[begin,full,release,done]}
  bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'.blend')));print('M16_RELOAD_REPAIRED',family,clip,flush=True)
(O/'reloads.json').write_text(json.dumps(report,indent=2))
