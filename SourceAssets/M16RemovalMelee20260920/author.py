"""Reuse current M4 complete bone chains for removal and six melee profiles.

Only the reload head changes; the previous insertion/charging poses are input
and remain untouched. No finger solver, wrist-only IK or twist-bone reset.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;bpy.context.preferences.filepaths.save_version=0
PREVIEW='--preview' in sys.argv;STEP=.5;ROOT='WPN_root';MAG='WPN_SOCKET_Magazine'
def smooth(a,b,t):
 t=max(0.,min(1.,(t-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,w):
 if w<=0:return a.copy()
 if w>=1:return b.copy()
 p,q,s=a.decompose();p1,q1,s1=b.decompose();return Matrix.LocRotScale(p.lerp(p1,w),q.slerp(q1,w),s.lerp(s1,w))
def open_source(file,action=None):
 bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima']
 a=bpy.data.actions[action] if action else r.animation_data.action
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];return r,a
def sample(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def parent_info(r):
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest};return rest,parents,local
def blend_chain(old,new,parents,w):
 if w<=0:return {n:m.copy() for n,m in old.items()}
 if w>=1:return {n:m.copy() for n,m in new.items()}
 out={}
 for n in old:
  par=parents[n];a=old[par].inverted()@old[n] if par else old[n];b=new[par].inverted()@new[n] if par else new[n]
  out[n]=out[par]@mix(a,b,w) if par else mix(a,b,w)
 return out
receipt={'reload_preserved_from_frame':{'reload':43,'reload_empty':35},'quick_melee_reference':'Current M4QuickMeleeRefine20260919N, each matching grip profile','clips':{}}
def bake(r,poses,family,kind,end,source):
 rest,parents,local=parent_info(r);a=bpy.data.actions.new('M16_ChainPolish_'+family+'_'+kind);a.use_fake_user=True;r.animation_data.action=a
 for b in r.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for la in a.layers for st in la.strips for bag in st.channelbags for c in bag.fcurves}
 for n in rest:
  rows=[];prev=None
  for p in poses:
   m=local[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=m.decompose()
   if prev and prev.dot(q)<0:q.negate()
   prev=q.copy();rows.append((loc,q,scale))
  for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(rows));c.keyframe_points.foreach_set('co',[v for j,row in enumerate(rows) for v in [j*STEP,row[field][axis]]])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 name='A_M16_'+('' if family=='base' else family+'_')+kind;folder=O/('Candidate' if PREVIEW else 'Animations')/family;folder.mkdir(parents=True,exist_ok=True)
 s=bpy.context.scene;s.render.fps=60;s.render.fps_base=1;s.frame_start=0;s.frame_end=end;s.frame_set(0)
 if not PREVIEW:
  bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=STEP,bake_anim_simplify_factor=0)
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'.blend')))
 dest='/Game/Weapons/M16A2/'+('Gameplay20260919/Animations' if family=='base' else 'UniversalAttachments20260920/Animations/'+family)
 receipt['clips'][family+'/'+kind]={'name':name,'file':str(folder/(name+'.fbx')),'folder':dest,'duration':end/60,'source':str(source),'action':a.name}
 (O/('candidate.json' if PREVIEW else 'authoring.json')).write_text(json.dumps(receipt,indent=2));print('M16_CHAIN_AUTHORED',family,kind,flush=True)

# The insertion donor is also the current removal donor. Continue the same
# complete animation through the first stage instead of retaining HK416's head.
removal={}
for kind,end in [('reload',43),('reload_empty',35)]:
 r,a=open_source(S/'ExtMagContact20260919'/('A_M4_ExtContact_'+kind+'.blend'))
 removal[kind]=[sample(r,a,j*STEP) for j in range(int(end/STEP)+1)]
G=Matrix.Translation(Vector(json.loads((S/'M16M4Insert20260920/transplant.json').read_text())['registration_m']))
for family in (['base'] if PREVIEW else ['base','vertical','canted','prism','angled']):
 for kind,end,limit in [('reload',126,43),('reload_empty',162,35)]:
  source=S/'M16M4Insert20260920/Animations'/family/('A_M16_'+('' if family=='base' else family+'_')+kind+'.blend');r,a=open_source(source)
  rest,parents,local=parent_info(r);idle=sample(r,a,0);seat=idle[ROOT].inverted()@idle[MAG];di=removal[kind][0];source_seat=di[ROOT].inverted()@di[MAG];poses=[]
  for j in range(int(end/STEP)+1):
   f=j*STEP;old=sample(r,a,f)
   if f>=limit:poses.append(old);continue
   d=removal[kind][j];W=d[ROOT];p={}
   for n in rest:p[n]=W@old[ROOT].inverted()@old[n] if n.startswith('WPN_') else d[n].copy() if n in d else old[n].copy()
   p[ROOT]=W.copy();D=W.inverted()@d[MAG]@source_seat.inverted();p[MAG]=W@G@D@G.inverted()@seat
   poses.append(blend_chain(old,p,parents,smooth(0,10,f)))
  bake(r,poses,family,kind,end,source)

# Matching M4 N profiles already contain coherent shoulder/elbow/twist motion.
# M16's actual idle grip registration is translation only for all six profiles.
profiles=['base','vertical'] if PREVIEW else ['base','drum','angled','vertical','canted','prism']
registration=json.loads((O/'grip_registration.json').read_text())
for family in profiles:
 profile=family.title();r,a=open_source(S/'M4QuickMeleeRefine20260919N'/profile/f'M4_QuickCombat_{profile}_Editable.blend')
 donor=[sample(r,a,j) for j in range(109)]
 source=S/'M16Gameplay20260919/M16_Manny_Editable.blend' if family=='base' else S/'M16UniversalAttachments20260920'/f'M16_{family}_Animations_Editable.blend'
 kind='quick_melee' if family=='base' else 'QuickCombat';r,a=open_source(source,'M16_'+('' if family=='base' else family+'_')+kind)
 rest,parents,local=parent_info(r);idle=sample(r,bpy.data.actions['M16_idle' if family=='base' else f'M16_{family}_idle'],0)
 alignment=idle[ROOT]@donor[0][ROOT].inverted();reg={s:Matrix(registration[family][s]['matrix']) for s in ['r','l']};poses=[]
 for j in range(109):
  f=j*STEP;old=sample(r,a,f);d=donor[j];W=alignment@d[ROOT];p={}
  for n in rest:
   if n.startswith('WPN_'):p[n]=W@idle[ROOT].inverted()@idle[n]
   elif n.endswith(('_l','_r')) and n in d:p[n]=W@reg[n[-1]]@d[ROOT].inverted()@d[n]
   elif n in d:p[n]=alignment@d[n]
   else:p[n]=old[n].copy()
  p[ROOT]=W.copy();weight=smooth(0,4,f)*(1-smooth(44,54,f))
  poses.append(blend_chain(old,p,parents,weight))
 bake(r,poses,family,kind,54,source)
