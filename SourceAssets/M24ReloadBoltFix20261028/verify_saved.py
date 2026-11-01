"""Fresh-process readback of active assets, not the authoring inputs."""
import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;tree=ast.parse((O/'install.py').read_text())
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'pack','exec'))
snapshot=json.loads((O/'ue_before.json').read_text());report={'fresh_process_readback':True,'profiles':{}}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name);got=packed(p,family);expected=json.loads((O/(family+'_profile.json')).read_text())
 if got!=expected:raise RuntimeError('Profile disk readback differs '+family)
 (O/(family+'_saved.json')).write_text(json.dumps(got))
 normal=next(c for c in got['clips'] if c['base'].endswith('A_M24_reload.A_M24_reload'));old=next(c for c in snapshot['profiles'][family] if c['base']==normal['base'])
 if normal!=old:raise RuntimeError('Normal reload refinement changed unexpectedly')
 report['profiles'][family]={'disk_matches_written':True,'normal_reload_refinement_preserved':True,'family':str(p.get_editor_property('family'))}
m=json.loads((O/'morph_install_receipt.json').read_text());mesh=u.load_asset(m['path']);names=[x.get_name() for x in mesh.get_editor_property('morph_targets')]
if any(n not in names for n in m['added_morphs']):raise RuntimeError('Saved elbow corrective missing')
task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'m24_after.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX()
opt=u.FbxExportOption();opt.set_editor_property('export_morph_targets',True);opt.set_editor_property('level_of_detail',False);task.options=opt
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Saved mesh export failed')
report['morph_count']=len(names);report['mesh_path']=mesh.get_path_name();(O/'saved_readback.json').write_text(json.dumps(report,indent=2));print('M24_SAVED_READBACK',json.dumps(report),flush=True)
