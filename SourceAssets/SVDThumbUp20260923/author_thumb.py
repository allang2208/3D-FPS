"""Raise only the left thumb; preserve all other animation channels verbatim."""
import ast,json,math
from pathlib import Path
import bpy
from mathutils import Quaternion,Vector

O=Path(__file__).parent;S=O.parent;P=S/'SVDFrontHalfGrip20260923'
D=O/'Animations';D.mkdir(exist_ok=True)
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select']],type_ignores=[]),'<source helpers>','exec'))
previous=json.loads((P/'authoring.json').read_text())
thumb=['thumb_01_l','thumb_02_l','thumb_03_l']

def rotation(axis,angle):return Quaternion(Vector(axis),math.radians(angle))
def ease(x):
 x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def curves(action):
 return {(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}

# Real rest-local axes: let the CMC rise close to rest, slightly outward and
# forward; MCP/IP remain gently flexed. No folded-in or rear-reaching thumb.
raised={
 'thumb_01_l':rotation((0,0,1),-8)@rotation((0,1,0),-12),
 'thumb_02_l':rotation((0,0,1),4),
 'thumb_03_l':rotation((0,0,1),3),
}
opened={**raised,'thumb_02_l':rotation((0,0,1),2),'thumb_03_l':rotation((0,0,1),1)}
fit=json.loads((P/'grasp_fit.json').read_text())
for key,qs in [('finger_basis',raised),('open_basis',opened)]:
 for n,q in qs.items():fit[key][n]=list(q)
# Previous geometric fit measurements describe the superseded thumb pose.
for key in ['parameters','optimizer_success','optimizer_message','minimum_clearance_mm','pad_means_mm','palm_mean_mm','pad_centers_mag_mm','front_half_margin_mm']:
 fit.pop(key,None)
fit.update({'source':str(P/'grasp_fit.json'),'modified_bones':thumb,
 'method':'Thumb only: CMC rest-local Y -12 and Z -8 degrees, MCP 4 degrees, IP 3 degrees. Extend upward with mild natural bend. Preserve palm, other fingers and complete arm channels.',
 'game_tested':False})
(O/'grasp_fit.json').write_text(json.dumps(fit,indent=2))
bpy.context.preferences.filepaths.save_version=0;report={}

for family in ['base','vertical','canted','prism','angled']:
 source=P/f'SVD_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['SK_M4_Infima']
 for clip in ['reload','reload_empty']:
  key=family+'/'+clip;info=previous[key];name=info['name'];old=bpy.data.actions[name]
  original=curves(old);a=old.copy();old.name='REFERENCE_BEFORE_THUMB_UP_'+name;a.name=name;a.use_fake_user=True
  target=curves(a)
  for n in thumb:
   path=f'pose.bones["{n}"].rotation_quaternion'
   def original_q(f):
    q=Quaternion([original[(path,j)].evaluate(f) for j in range(4)]);q.normalize();return q
   entry=original_q(18);rows=[];last=None
   for f in range(info['frames']+1):
    q=original_q(f)
    if 18<f<=34:q=entry.slerp(raised[n],ease((f-18)/16))
    elif 34<f<=244:q=raised[n].copy()
    elif 244<f<=284:q=raised[n].slerp(opened[n],ease((f-244)/12))
    elif 284<f<302:q=opened[n].slerp(q,ease((f-284)/18))
    if last and last.dot(q)<0:q.negate()
    rows.append(q.copy());last=q.copy()
   for j in range(4):
    c=target[(path,j)];c.keyframe_points.clear();c.keyframe_points.add(len(rows))
    c.keyframe_points.foreach_set('co',[v for f,q in enumerate(rows) for v in (f,q[j])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
  rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
  scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=info['frames'];scene.frame_set(0)
  select([rig])
  bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
  report[key]={**info,'source':str(D/(name+'.fbx')),'blend':str(O/f'SVD_{family}_Editable.blend'),'previous_blend':str(source),
   'changed':'Only left thumb rotation channels: upward relaxed extension, no palm fold. Other source channels copied unchanged.',
   'modified_bones':thumb,'grasp_fit':str(O/'grasp_fit.json'),'game_tested':False}
  (O/'authoring.json').write_text(json.dumps(report,indent=2))
  print('SVD_THUMB_UP_AUTHORED',key,flush=True)
 sample(rig,bpy.data.actions[previous[family+'/reload']['name']],220)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_THUMB_UP_COMPLETE',len(report),flush=True)
