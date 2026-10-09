"""Scoped readback requested for clothing repairs; does not start gameplay."""
import unreal as u,json,math
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
r=json.loads((ROOT/'ue_delivery.json').read_text());source=json.loads((ROOT/'live_source.json').read_text());expected=json.loads((ROOT/'corrective_curves.json').read_text())
if r['stage']!='saved':raise RuntimeError('V04 not fully saved')
mesh=u.load_asset(r['meshes']['outfit']);cloth=u.load_asset(r['meshes']['clothes']);skeleton=mesh.skeleton
report={'kind':'saved_asset_and_clothing_curve_check','runtime_tested':False,'mesh':mesh.get_path_name(),'morph_count':len(mesh.get_editor_property('morph_targets')),'clips':{},'material_paths':[s.material_interface.get_path_name() for s in mesh.materials]}
actual={m.get_name() for m in mesh.get_editor_property('morph_targets')};clothing={m.get_name() for m in cloth.get_editor_property('morph_targets')}
if not set(r['morph_names'].values()).issubset(actual):raise RuntimeError('Saved mesh lost morph targets')
report['independent_clothing_matching_names']=set(r['morph_names'].values()).issubset(clothing)
for role,path in r['clips'].items():
 clip=u.load_asset(path);duration=clip.get_play_length();old=source['clips'][role]['duration']
 if abs(duration-old)>1e-5:raise RuntimeError('Bone clip duration changed '+role)
 count=round(duration*30)+1;sums=[0.]*count;max_error=0.
 for requested,values in expected[role].items():
  name=r['morph_names'][requested]
  if not u.AnimationLibrary.get_curve_meta_data_morph_target(skeleton,name):raise RuntimeError('Curve is not marked for morph evaluation '+name)
  times,got=u.AnimationLibrary.get_float_keys(clip,name)
  if len(got)!=count:raise RuntimeError('Incorrect curve sample count '+name+' '+str(len(got)))
  for i,value in enumerate(got):
   max_error=max(max_error,abs(float(value)-values[i]));sums[i]+=float(value)
 if max_error>1e-5 or max(abs(v-1) for v in sums)>1e-5:raise RuntimeError('Corrective curve data mismatch '+role)
 report['clips'][role]={'duration_seconds':duration,'curve_count':len(expected[role]),'samples_checked':count,'maximum_value_error':max_error,'morph_metadata':True,'partition_of_unity':True}
bp=u.load_asset(r['blueprint']);cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh')!=mesh:raise RuntimeError('Existing F6 Blueprint did not retain V04 mesh')
report['blueprint_reference_saved']=True
(ROOT/'asset_readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('V04_TARGETED_READBACK '+json.dumps(report,ensure_ascii=False))
