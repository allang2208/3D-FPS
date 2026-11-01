import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;data=json.loads((O/'ue_before.json').read_text());names=list(json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['rest'])
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'pack','exec'))
receipt={'profiles':{},'clips':{},'actors':[],'dirty_packages':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
def asset_hash(a):
 f=Path(u.Paths.project_content_dir())/(a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
 return hashlib.sha256(f.read_bytes()).hexdigest()
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name);data['profiles'][family]=packed(p,family)['clips'];receipt['profiles'][family]={'path':p.get_path_name(),'sha256':asset_hash(p)}
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9');receipt['mesh']={'path':mesh.get_path_name(),'sha256':asset_hash(mesh),'morph_count':len(mesh.get_editor_property('morph_targets'))}
def tr(t):
 p=t.translation;q=t.rotation;s=t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for role,desc in data['clips'].items():
 a=u.load_asset(desc['path']);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator;count=dm.get_number_of_keys()
 rows={str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(count)}
 data['clips'][role]={'path':desc['path'],'fps':fps,'keys':count,'poses':rows,'evaluation':'Sequence data model by time'}
 receipt['clips'][role]={'path':a.get_path_name(),'keys':count,'fps':fps,'duration':(count-1)/fps,'sha256':asset_hash(a)}
def prop(o,n):
 try:
  v=o.get_editor_property(n)
  return v.get_path_name() if isinstance(v,u.Object) else str(v)
 except:return None
try:
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
 if world:
  for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
   row={'path':actor.get_path_name(),'properties':{n:prop(actor,n) for n in ('active_inventory_weapon_definition','reload_duration','empty_reload_duration','reload_animation','reload_empty_animation','fire_animation','aim_fire_animation')}}
   vm=actor.get_editor_property('akm_viewmodel');row['viewmodel']={'mesh':prop(vm,'skeletal_mesh_asset'),'relative_transform':tr(vm.get_relative_transform()),'world_transform':tr(vm.get_world_transform())}
   anim=vm.get_anim_instance();row['anim']={n:prop(anim,n) for n in ('grip_profile','action_grip_profile','action_clip','action_time','action_alpha','idle_clip','aim_clip','aim_alpha')}
   receipt['actors'].append(row)
except Exception as e:receipt['live_actor_note']=str(e)
data['snapshot_origin']='Fresh UE assets and active profiles: M24 reload/bolt review 2026-10-28'
(O/'ue_before.json').write_text(json.dumps(data));(O/'read_receipt.json').write_text(json.dumps(receipt,indent=2));print('M24_RELOAD_BOLT_READ',json.dumps(receipt),flush=True)
