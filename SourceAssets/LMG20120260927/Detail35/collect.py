"""Read the active 201 geometry, interfaces and materials for local refinement."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;(O/'Inputs').mkdir(exist_ok=True)
P=O.parents[2];E=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
out={'pie':bool(editor.get_game_world()),'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'assets':{}}
paths={'Body':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','FrontSight':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_FrontSight','RearSight':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_RearSight'}
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for key,path in paths.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError(path)
 row={'asset':a.get_path_name(),'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'metadata':{str(k):str(v) for k,v in E.get_metadata_tag_values(a).items()},'materials':[]}
 slots=a.materials if key=='Body' else a.static_materials
 for s in slots:row['materials'].append({'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None})
 if key=='Body':
  dm,res=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
  row['bones']={str(b.name):{'parent':b.parent_index,'index':b.index,'world':tr(b.world_transform)} for b in bones}
 ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Inputs'/(key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=False;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export '+key)
 out['assets'][key]=row
(O/'inputs.json').write_text(json.dumps(out,indent=2));print('DETAIL35_INPUTS',json.dumps({'pie':out['pie'],'dirty':out['dirty'],'assets':{k:v['sha256'] for k,v in out['assets'].items()}}),flush=True)
