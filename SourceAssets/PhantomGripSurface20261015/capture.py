"""Read the current phantom grip variants and their effective material inputs."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];X=O/'Input';X.mkdir(exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=P:raise RuntimeError('Unexpected project')
paths={k:f'/Game/Weapons/RearGripFinish20260913/{k}/phantom/SM_PhantomRearGrip' for k in ['M4','AKM','QBZ191']}
paths.update({k:f'/Game/Weapons/{folder}/Meshes/SM_{k}_phantom_reargrip' for k,folder in {'M16':'M16A2/UniversalAttachments20260920','HK416':'HK416/CommonAttachments20260930','A762':'A762/Accessories05','PKM':'PKMLowpoly20260922/Accessories14','LMG201':'LMG201/Accessories22','Super90':'Super90/RearGrips20261012'}.items()})
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils
R={'assets':{},'materials':{},'textures':{},'runtime_components':[],'gameplay_tested':False}
# Reuse the material graph walk already exercised by the preceding stock audit.
helper=(P/'SourceAssets/TelescopicAllGunsAudit20261015/capture.py').read_text(encoding='utf-8')
exec(compile(helper[helper.index('def record():'):helper.index('sms=')],'<material_graph_helpers>','exec'))
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
R['pie']=editor.is_in_play_in_editor() if editor else False;R['dirty_targets']=[p for p in paths.values() if p in dirty]
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 row={'path':path,'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),'slots':[]}
 for slot in mesh.static_materials:row['slots'].append({'name':str(slot.material_slot_name),'material':material(slot.material_interface) if slot.material_interface else None})
 lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL);mats,indices,names,status=G.get_section_material_list_from_static_mesh(mesh,lod)
 row['sections']=[{'slot':int(i),'name':str(n),'material':m.get_path_name() if m else None} for m,i,n in zip(mats,indices,names)]
 settings=sms.get_lod_build_settings(mesh,0);row['build_settings']={k:settings.get_editor_property(k) for k in ['recompute_normals','recompute_tangents','use_full_precision_u_vs','use_high_precision_tangent_basis','remove_degenerates']}
 task=u.AssetExportTask();task.object=mesh;task.filename=str(X/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
 row['export']=task.filename;R['assets'][key]=row;record();print('PHANTOM_CAPTURED',key,flush=True)
for comp in u.ObjectIterator(u.StaticMeshComponent):
 mesh=comp.get_editor_property('static_mesh')
 if not mesh or mesh.get_path_name().split('.')[0] not in paths.values():continue
 R['runtime_components'].append({'component':comp.get_path_name(),'mesh':mesh.get_path_name(),'materials':[comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]})
for path,mat in R['materials'].items():mat['sha256']=hashlib.sha256(disk(path).read_bytes()).hexdigest()
R['complete']=True;record();print('PHANTOM_CAPTURE_COMPLETE',len(R['assets']),flush=True)
