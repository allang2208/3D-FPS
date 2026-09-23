"""SVD-specific rigid bindings, contacts and complete shared-Manny action set.
Source geometry retains UVs, normals, proportions and materials. All authoring
coordinates are metres in WPN_root space (-Y muzzle, +Z receiver up).
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Exports';D.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
ROOT='WPN_root';MAG='WPN_SOCKET_Magazine';BOLT='WPN_bolt'
PARTS=['Body','Magazine','Trigger','ChargingHandle','SafetyLever','ScopeBody','ScopeMount','ScopeLens']
# Source grip landmark -> shared Manny grip. Explicit axes avoid the previous
# double inverse and the source skeleton's 5-degree rest cant.
FIT=Matrix(((-1,0,0,.01865),(0,-1,0,-.26447),(0,0,1,.00817),(0,0,0,1)))

def sample(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
def smooth(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)
def mix(a,b,t):
 x,q,s=a.decompose();y,v,z=b.decompose();return Matrix.LocRotScale(x.lerp(y,t),q.slerp(v,t),s.lerp(z,t))
def shifted(m,v):
 m=m.copy();m.translation+=Vector(v);return m
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def bake(r,poses,key,fps):
 parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 lr={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
 a=bpy.data.actions.new('A_SVD_'+key);a.use_fake_user=True;r.animation_data.action=a
 for b in r.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
 for n in rest:
  rows=[];prev=None
  for p in poses:
   loc,q,z=(lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])).decompose()
   if prev and prev.dot(q)<0:q.negate()
   prev=q.copy();rows.append((loc,q,z))
  for prop,i,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(rows));c.keyframe_points.foreach_set('co',[v for j,row in enumerate(rows) for v in (j,row[i][axis])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 scene=bpy.context.scene;scene.render.fps=fps;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=len(poses)-1;scene.frame_set(0)
 select([r]);bpy.ops.export_scene.fbx(filepath=str(D/('A_SVD_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
 return a

def solve_arm(p,H,side):
 # Preserve all bone lengths; move shoulder only when the wrist is unreachable.
 old={n:m.copy() for n,m in p.items()};cn='clavicle_'+side;un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
 C=old[cn].translation.copy();A=old[un].translation.copy();E=old[fn].translation.copy();T=H.translation.copy();l1=(E-A).length;l2=(old[hn].translation-E).length
 if (T-A).length>l1+l2-.002:
  axis=(T-C).normalized();R=(A-C).length;dist=(T-C).length;co=max(-1,min(1,(R*R+dist*dist-(l1+l2-.002)**2)/(2*R*dist)));sidev=A-C-axis*(A-C).dot(axis)
  if sidev.length<1e-6:sidev=Vector((1,0,0))
  sidev.normalize();A=C+axis*(R*co)+sidev*(R*math.sqrt(max(0,1-co*co)))
  p[cn]=Matrix.LocRotScale(C,(old[un].translation-C).rotation_difference(A-C)@old[cn].to_quaternion(),old[cn].to_scale())
 axis=(T-A).normalized();dist=(T-A).length;pole=E-A-axis*(E-A).dot(axis)
 if pole.length<1e-6:pole=Vector((1,0,0))
 pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*max(dist,1e-6));Enew=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 for n,origin,oldtip,tip in [(un,A,old[fn].translation,Enew),(fn,Enew,old[hn].translation,T)]:
  p[n]=Matrix.LocRotScale(origin,(oldtip-old[n].translation).rotation_difference(tip-origin)@old[n].to_quaternion(),old[n].to_scale())
  for j in (1,2):
   twist=n.replace('_'+side,'_twist_0'+str(j)+'_'+side)
   if twist in p:p[twist]=p[n]@old[n].inverted()@old[twist]
 delta=H@old[hn].inverted();p[hn]=H
 for n in p:
  if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=delta@old[n]

# Work on the existing shared-arms export, preserving its mesh and skinning.
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDDragunov20260922/Authored/SK_SVD_Viewmodel.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');arms=bpy.data.objects['SK_Manny_Arms_Export'];scene=bpy.context.scene
for o in list(scene.objects):
 if o not in [r,arms]:bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(S/'AKMSoviet20260911/AKM_Soviet_Editable.blend')) as (a,b):b.actions=[n for n in a.actions if n.startswith('AKM_Native_') or n=='AKM_EquipCharge']
r.animation_data_create();idle=sample(r,bpy.data.actions['AKM_Native_idle'],0);W=idle[ROOT];rest={b.name:b.matrix_local.copy() for b in r.data.bones};geom={};objects=[]
for part in PARTS:
 before=set(scene.objects);bpy.ops.import_scene.fbx(filepath=str(S/f'SVDDragunov20260922/Authored/SM_SVD_{part}.fbx'))
 ob=next(o for o in scene.objects if o not in before and o.type=='MESH');ob.name='SM_SVD_'+part
 points=[FIT@ob.matrix_world@v.co for v in ob.data.vertices];geom[part]=points
 bone=MAG if part=='Magazine' else 'WPN_Trigger' if part=='Trigger' else BOLT if part=='ChargingHandle' else ROOT
 xf=rest[bone]@idle[bone].inverted()@W@FIT@ob.matrix_world
 ob.data.transform(xf);ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 for g in list(ob.vertex_groups):ob.vertex_groups.remove(g)
 ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1.,'REPLACE');ob.modifiers.new('SharedManny','ARMATURE').object=r;objects.append(ob)
 # Retain material slot identity; repair local source texture paths for editing.
 ts='pso' if part.startswith('Scope') else 'svd'
 for mat in ob.data.materials:
  if not mat:continue
  for node in mat.node_tree.nodes if mat.use_nodes else []:
   if node.type=='TEX_IMAGE' and node.image:
    stem=node.image.name.lower();role=next((k for k in ['normal','roughness','metallic','ao'] if k in stem),'basecolor');path=S/f'SVDDragunov20260922/Textures/T_SVD_{ts}_{role}{".png" if role=="normal" else ".jpg"}'
    if path.exists():node.image.filepath=str(path);node.image.reload()

# A separate carrier tongue behind the existing right-side handle. Its rigid
# bone is the same as the handle; no moving receiver, trigger or scope sections.
knob=sum(geom['ChargingHandle'],Vector())/len(geom['ChargingHandle'])
bpy.ops.mesh.primitive_cube_add(size=1);carrier=bpy.context.object;carrier.name='SM_SVD_BoltCarrier'
carrier.scale=(.012,.085,.013);carrier.location=(knob.x+.009,knob.y+.025,knob.z-.003);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bevel=carrier.modifiers.new('MachinedEdge','BEVEL');bevel.width=.001;bevel.segments=2;bpy.ops.object.modifier_apply(modifier=bevel.name)
carrier.data.transform(rest[BOLT]@idle[BOLT].inverted()@W@carrier.matrix_world);carrier.parent=r;carrier.matrix_parent_inverse=Matrix.Identity(4);carrier.matrix_basis=Matrix.Identity(4)
carrier.vertex_groups.new(name=BOLT).add(list(range(len(carrier.data.vertices))),1.,'REPLACE');carrier.modifiers.new('SharedManny','ARMATURE').object=r
mat=bpy.data.materials.new('M_SVD_BoltCarrier');mat.diffuse_color=(.035,.038,.044,1);carrier.data.materials.append(mat);objects.append(carrier)
# True source-space landmarks. Markers are authored in every action; runtime
# uses these tracks directly instead of inheriting the M4 socket positions.
body=geom['Body'];lens=geom['ScopeLens'];miny=min(v.y for v in body);muzzlepoints=[v for v in body if v.y<miny+.0015]
muzzle=Vector(((min(v[i] for v in muzzlepoints)+max(v[i] for v in muzzlepoints))*.5 for i in range(3)));muzzle.y=miny
rear=Vector(((min(v.x for v in lens)+max(v.x for v in lens))/2,max(v.y for v in lens),(min(v.z for v in lens)+max(v.z for v in lens))/2));front=rear.copy();front.y=min(v.y for v in lens)
eject=knob+Vector((.009,-.01,0));markers={'WPN_SOCKET_Muzzle':muzzle,'WPN_SOCKET_Eject':eject,'WPN_RearSight':rear,'WPN_FrontSight':front}
report={'fit':[list(x) for x in FIT],'markers_root_m':{n:list(v) for n,v in markers.items()},'charging_handle_root':list(knob),'parts':{n:{'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)]} for n,vs in geom.items()},'clips':{}}
print('SVD_GEOMETRY',json.dumps({k:report[k] for k in ['markers_root_m','charging_handle_root','parts']}),flush=True)
# Direct finger-group donor: reusable hook only, translated to the measured SVD knob.
refs=json.loads((S/'A762RightCharge20260922/reference_poses.json').read_text());don=refs['ASH12']['samples']['140.4'];fit=json.loads((S/'A762RightCharge20260922/fitted_contact.json').read_text());hook=Matrix(fit['hand_in_root']);hook.translation+=knob-Vector((-.0358,-.1694,.075))
hook_basis={n:Quaternion(q) for n,q in don['basis'].items() if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};lr={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
RH=shifted(W.inverted()@idle['hand_r'],(0,-.011,-.030));LH=shifted(W.inverted()@idle['hand_l'],(0,-.035,-.014));boltclosed=W.inverted()@idle[BOLT];handleclosed=W.inverted()@idle['WPN_ChargingHandle']
# Centre-based translation is only the initial placement of an already closed
# donor hand; contact frames below keep the entire group fixed to the magazine.
magcenter=(Vector(report['parts']['Magazine']['min'])+Vector(report['parts']['Magazine']['max']))*.5
with bpy.data.libraries.load(str(S/'AKMReloadPolish20260911/base/A_AKM_reload.blend')) as (a,b):b.actions=['A_AKM_reload_Polished']
with bpy.data.libraries.load(str(S/'AKMReloadPolish20260911/base/A_AKM_reload_empty.blend')) as (a,b):b.actions=['A_AKM_reload_empty_Polished']
contactfit=json.loads((O/'contact_fit.json').read_text());maggrip=Matrix(contactfit['hand_in_mag']);magfingers={n:Quaternion(q) for n,q in contactfit['finger_basis'].items()}
clips=[('idle','AKM_Native_idle',5),('aim','AKM_Native_aim',5),('fire','AKM_Native_fire',36),('aim_fire','AKM_Native_aim_fire',36),('reload','A_AKM_reload_Polished',400),('reload_empty','A_AKM_reload_empty_Polished',515),('equip','AKM_EquipCharge',204),('inspect','AKM_Native_inspect',745)]
# Save the editable rig before authoring, with all imported sources intact.
for key,source,end in clips:
 a=bpy.data.actions[source];poses=[]
 for f in range(end+1):
  p=sample(r,a,min(f,a.frame_range[1]));rt=p[ROOT];invr=rt.inverted();isreload=key.startswith('reload');empty=key=='reload_empty';equip=key=='equip';chargeweight=0.;magweight=0.
  # Steady grips follow the rifle; reload left hand follows the source magazine.
  hr=rt@RH;hl=rt@LH
  if isreload:
   # Keep the accepted M4 finger group wrapped around the short SVD magazine
   # from retrieval to seating; release first, then move around its outer wall.
   magweight=smooth((f-90)/38)*(1-smooth((f-244)/28))
   hold=p[MAG]@maggrip
   hl=mix(p['hand_l'],hold,magweight)
   if f>=240:
    w=smooth((f-240)/58);hl=mix(hold,rt@LH,w)
    hl.translation+=rt.to_3x3()@Vector((.055*math.sin(math.pi*w),.015*math.sin(math.pi*w),0))
   elif f<24:hl=mix(rt@LH,hl,smooth(f/24))
  if key=='inspect':
   # Preserve the inspect donor's release / regrip while applying grip offsets.
   hr=shifted(p['hand_r'],rt.to_3x3()@Vector((0,-.011,-.03)));hl=shifted(p['hand_l'],rt.to_3x3()@Vector((0,-.035,-.014)))
  start,contact,pulled,close,finish=(268,310,344,350,432) if empty else (20,64,94,100,176)
  if empty or equip:
   t=f;pull=smooth((t-contact)/(pulled-contact))*(1-smooth((t-pulled)/(close-pulled)))
   p[BOLT]=rt@shifted(boltclosed,(0,.075*pull,0));p['WPN_ChargingHandle']=rt@shifted(handleclosed,(0,.075*pull,0))
   hcontact=shifted(hook,(0,.075*pull,0));away=shifted(hook,(-.06,.025,.035));returned=RH
   if t<start:local=RH
   elif t<contact:local=mix(RH,hook,smooth((t-start)/(contact-start)))
   elif t<=pulled:local=hcontact
   elif t<close+16:local=mix(shifted(hook,(0,.075,0)),away,smooth((t-pulled)/(close+16-pulled)))
   else:local=mix(away,returned,smooth((t-close-16)/(finish-close-16)))
   hr=rt@local;chargeweight=smooth((t-start)/(contact-start))*(1-smooth((t-pulled)/(finish-pulled)))
  elif key in ('fire','aim_fire'):
   pull=smooth(f/4)*(1-smooth((f-4)/8));p[BOLT]=rt@shifted(boltclosed,(0,.075*pull,0));p['WPN_ChargingHandle']=rt@shifted(handleclosed,(0,.075*pull,0))
  else:p[BOLT]=rt@boltclosed;p['WPN_ChargingHandle']=rt@handleclosed
  solve_arm(p,hr,'r');solve_arm(p,hl,'l')
  if magweight:
   for n,q in magfingers.items():
    basis=lr[n].inverted()@p[parents[n]].inverted()@p[n];loc,oldq,z=basis.decompose();p[n]=p[parents[n]]@lr[n]@Matrix.LocRotScale(loc,oldq.slerp(q,magweight),z)
  if chargeweight:
   for n,q in hook_basis.items():
    if n not in p:continue
    basis=(lr[n].inverted()@p[parents[n]].inverted()@p[n]);loc,oldq,z=basis.decompose();p[n]=p[parents[n]]@lr[n]@Matrix.LocRotScale(loc,oldq.slerp(q,chargeweight),z)
  for n,point in markers.items():
   p[n]=rt@Matrix.Translation(point)
  poses.append(p)
 action=bake(r,poses,key,120);report['clips'][key]={'source':source,'frames':end,'fps':120,'duration':end/120}
 if key=='idle':idle_final=poses[0]
 print('SVD_AUTHORED',key,end/120,flush=True)
# Tactical actions use the accepted rifle methods fitted to this weapon's idle.
sys.path.insert(0,str(O))
from tactical_actions import author_actions
report['clips'].update(author_actions(r,idle_final,bake))
# Export the shared skin and rigid weapon as one viewmodel; skeleton rest is unchanged.
a=bpy.data.actions['A_SVD_idle'];sample(r,a,0);select(objects+[arms,r]);bpy.ops.export_scene.fbx(filepath=str(D/'SK_SVD_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
scene.render.fps=120;scene.frame_start=0;scene.frame_end=515;bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_Complete_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_AUTHORING_COMPLETE',flush=True)
