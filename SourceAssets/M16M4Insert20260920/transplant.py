"""Transplant the current M4 insertion, including its magazine and whole arms.

Registration moves the complete left chain rigidly. No new finger poses, IK,
bone lengths or source insertion curves. M16 empty charging tail stays original.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;bpy.context.preferences.filepaths.save_version=0
PREVIEW='--preview' in sys.argv;STEP=.5
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,w):
 if w<=0:return a.copy()
 if w>=1:return b.copy()
 ap,aq,az=a.decompose();bp,bq,bz=b.decompose()
 return Matrix.LocRotScale(ap.lerp(bp,w),aq.slerp(bq,w),az.lerp(bz,w))
def sample(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
donors={};donorrest={}
for kind,end in [('reload',126),('reload_empty',162)]:
 bpy.ops.wm.open_mainfile(filepath=str(S/'ExtMagContact20260919'/('A_M4_ExtContact_'+kind+'.blend')),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];a=r.animation_data.action
 donors[kind]=[sample(r,a,j*STEP) for j in range(int(end/STEP)+1)]
 donorrest[kind]={b.name:b.matrix_local.copy() for b in r.data.bones}
def dp(kind,f):
 k=f/STEP;lo=int(k);hi=min(lo+1,len(donors[kind])-1);w=k-lo
 return {n:mix(m,donors[kind][hi][n],w) for n,m in donors[kind][lo].items()}
MAG='WPN_SOCKET_Magazine';ROOT='WPN_root'
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];idle=sample(r,bpy.data.actions['M16_idle'],0)
target_seat=idle[ROOT].inverted()@idle[MAG]
source_seat=donors['reload'][0][ROOT].inverted()@donors['reload'][0][MAG]
# Lateral centre and fore/aft shell match; keep M4's grip below the M16 well.
# This is a registration of the whole accepted arm, never per-finger offsets.
contact_shift=Vector((-.0120794035,-.0096143348,-.020))
G=Matrix.Translation(contact_shift)
report={'donor_normal':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload','donor_empty':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload_empty','registration_m':list(contact_shift),'seat_root_space':[list(row) for row in target_seat],'empty_preserved_from_frame':111,'clips':{}}
for family in (['base'] if PREVIEW else ['base','vertical','canted','prism','angled']):
 for kind,end in [('reload',126),('reload_empty',162)]:
  # Read the installed generation, including its established charging tail.
  src=S/'M16Refinement20260920/Animations'/family/('A_M16_'+('' if family=='base' else family+'_')+kind+'.blend')
  bpy.ops.wm.open_mainfile(filepath=str(src),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
  source=bpy.data.actions['M16_Refined_'+family+'_'+kind]
  rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
  poses=[]
  for j in range(int(end/STEP)+1):
   f=j*STEP;old=sample(r,source,f)
   if kind=='reload_empty' and f>=111:poses.append(old);continue
   if kind=='reload':
    d=dp(kind,f);weight=smooth(30,43,f)*(1-smooth(108,126,f));grip=smooth(43,61,f)*(1-smooth(95,108,f))
   else:
    weight=smooth(21,35,f)*(1-smooth(100,111,f));grip=smooth(35,43,f)*(1-smooth(80,100,f))
    if f<=88:d=dp(kind,f)
    else:
     # Reuse the normal M4 release/return; never import the M4 slap tail.
     nf=98+(f-88)*28/23;normal=dp('reload',nf);start=dp('reload',98);last=dp(kind,88)
     align=mix(last[ROOT]@start[ROOT].inverted(),Matrix.Identity(4),smooth(88,111,f))
     moving={n:align@m for n,m in normal.items()}
     d={n:mix(last[n],m,smooth(88,94,f)) for n,m in moving.items()}
     grip=(1-smooth(95,108,nf))
   if weight<=0:poses.append(old);continue
   W=d[ROOT];Wi=W.inverted();p={}
   for n in rest:
    if n.startswith('WPN_'):
     # Preserve M16-only pivots and mechanical timing in its receiver frame.
     p[n]=W@old[ROOT].inverted()@old[n]
    elif n in d:p[n]=d[n].copy()
    else:p[n]=old[n].copy()
   p[ROOT]=W.copy()
   # Register source displacement at the actual M16 seat. In particular, the
   # aligned/insert/seat frames retain the M4's vertical-only magazine travel.
   D=Wi@d[MAG]@source_seat.inverted()
   p[MAG]=W@G@D@G.inverted()@target_seat
   shift=W.to_3x3()@(contact_shift*grip)
   for n in rest:
    if n.endswith('_l'):p[n].translation+=shift
   # Short source-to-source handoffs; blend complete local chains, not wrists.
   result={}
   for n in rest:
    parent=parents[n]
    a=old[parent].inverted()@old[n] if parent else old[n]
    b=p[parent].inverted()@p[n] if parent else p[n]
    result[n]=result[parent]@mix(a,b,weight) if parent else mix(a,b,weight)
   # No inherited rocking or creep after seating, including the source handoff.
   if f>= (95 if kind=='reload' else 80):result[MAG]=result[ROOT]@target_seat
   poses.append(result)
  a=bpy.data.actions.new('M16_M4Insert_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
  for b in r.pose.bones:
   b.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
  curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
  for n in rest:
   vals=[];previous=None
   for p in poses:
    m=local[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=m.decompose()
    if previous and previous.dot(q)<0:q.negate()
    previous=q.copy();vals.append((loc,q,scale))
   for prop,col,num in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
    for axis in range(num):
     c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(poses));c.keyframe_points.foreach_set('co',[x for j,row in enumerate(vals) for x in [j*STEP,row[col][axis]]])
     for k in c.keyframe_points:k.interpolation='LINEAR'
     c.update()
  name='A_M16_'+('' if family=='base' else family+'_')+kind;folder=O/('Candidate' if PREVIEW else 'Animations')/family;folder.mkdir(parents=True,exist_ok=True)
  scene.render.fps=60;scene.frame_start=0;scene.frame_end=end;scene.frame_set(76 if kind=='reload' else 54)
  if not PREVIEW:
   bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
   bpy.ops.export_scene.fbx(filepath=str(folder/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=STEP,bake_anim_simplify_factor=0)
  bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'.blend')))
  dest='/Game/Weapons/M16A2/'+('Gameplay20260919/Animations' if family=='base' else 'UniversalAttachments20260920/Animations/'+family)
  report['clips'][family+'/'+kind]={'name':name,'file':str(folder/(name+'.fbx')),'folder':dest,'duration':end/60,'source':str(src),'action':a.name}
  (O/('candidate.json' if PREVIEW else 'transplant.json')).write_text(json.dumps(report,indent=2));print('M16_M4_INSERT_AUTHORED',family,kind,flush=True)
