"""Read-only material/asset check and export the existing movable sight heads."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;receipt=json.loads((O/'delivery.json').read_text());out={'saved_assets':{},'materials':{},'game_started':False}
for path,row in receipt['saved'].items():
 actual=hashlib.sha256((PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest();out['saved_assets'][path]={'matches_receipt':actual==row['sha256']}
 if actual!=row['sha256']:raise RuntimeError('Saved asset changed '+path)
for name,path in json.loads((O/'materials.json').read_text())['materials'].items():
 a=u.load_asset(path);node=M.get_material_property_input_node(a,u.MaterialProperty.MP_NORMAL);info={'two_sided':a.get_editor_property('two_sided'),'skeletal_usage':a.get_editor_property('used_with_skeletal_mesh'),'has_wetness':'WeaponWetness' in {str(n) for n in M.get_scalar_parameter_names(a)},'normal_node':node.get_class().get_name() if node else None}
 if node and isinstance(node,u.MaterialExpressionCustom):info['normal_code']=node.get_editor_property('code')
 out['materials'][name]=info
 if info['two_sided'] or not info['skeletal_usage'] or not info['has_wetness']:raise RuntimeError('Material contract changed '+name)
for key in ['FrontSight','RearSight']:
 a=u.load_asset('/Game/Weapons/LMG201/Production20260927/SM_LMG201_'+key)
 task=u.AssetExportTask();task.object=a;task.filename=str(O/'Exports'/('Current_'+key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export existing '+key)
(O/'asset_check.json').write_text(json.dumps(out,indent=2));print('H39_ASSET_CHECK',json.dumps(out),flush=True)
