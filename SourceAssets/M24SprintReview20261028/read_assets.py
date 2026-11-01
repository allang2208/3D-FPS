import unreal as u,json,ast
from pathlib import Path
O=Path(__file__).resolve().parent;old=O.parent/'M24SprintSupport20261028'
data=json.loads((old/'ue_before.json').read_text());names=list(json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['rest'])
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
tree=ast.parse((old/'install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed');exec(compile(ast.unparse(fn),'pack','exec'))
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 data['profiles'][family]=packed(u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name),family)['clips']
def tr(t):
 p=t.translation;q=t.rotation;s=t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
raw={};summary={}
for role in ('idle','sprint_enter','sprint_loop','sprint_exit'):
 desc=data['clips'][role];a=u.load_asset(desc['path']);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();duration=(dm.get_number_of_keys()-1)/(rate.numerator/rate.denominator)
 times=[0.] if role=='idle' else [i/120 for i in range(round(duration*120)+1)]
 rows={};rawrows={}
 for mode,target in ((u.AnimDataEvalType.COMPRESSED,rows),(u.AnimDataEvalType.RAW,rawrows)):
  options=u.AnimPoseEvaluationOptions();options.set_editor_property('evaluation_type',mode);options.set_editor_property('optional_skeletal_mesh',mesh)
  for i,t in enumerate(times):
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
   if not u.AnimPoseExtensions.is_valid(pose):raise RuntimeError('Invalid pose '+role)
   target[str(i)]=[tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
 data['clips'][role]={'path':desc['path'],'fps':120,'keys':len(times),'poses':rows,'evaluation':'UE compressed','source_fps':rate.numerator/rate.denominator,'duration':duration}
 raw[role]=rawrows;summary[role]={'samples':len(times),'duration':duration}
data['snapshot_origin']='Fresh UE compressed pose and live profile readback'
(O/'ue_before.json').write_text(json.dumps(data));(O/'ue_raw.json').write_text(json.dumps(raw));(O/'read_receipt.json').write_text(json.dumps(summary,indent=2))
print('M24_SPRINT_COMPRESSED_READBACK',json.dumps(summary),flush=True)
