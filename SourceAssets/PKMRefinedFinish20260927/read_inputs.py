"""Read current material authoring inputs only; no scene or test execution."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
out={'materials':{},'meshes':{},'references':{},'wet_materials':{}}
def describe(mat):
 base=mat.get_base_material()
 nodes=[]
 for n in L.get_material_expressions(base):
  if isinstance(n,u.MaterialExpressionCustom):
   nodes.append({'description':str(n.get_editor_property('description')),'code':str(n.get_editor_property('code')),'inputs':[str(p.get_editor_property('input_name')) for p in n.get_editor_property('inputs')]})
 params={}
 for kind in ['scalar','vector','texture']:
  params[kind]={}
  for name in getattr(L,'get_'+kind+'_parameter_names')(base):
   v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(mat,name) if isinstance(mat,u.MaterialInstanceConstant) else getattr(L,'get_material_default_'+kind+'_parameter_value')(base,name)
   params[kind][str(name)]=v.get_path_name() if kind=='texture' and v else [v.r,v.g,v.b,v.a] if kind=='vector' else v
 return {'base':base.get_path_name(),'category':str(E.get_metadata_tag(base,'PKM20_Category')),'source':str(E.get_metadata_tag(base,'PKM20_Source')),'custom':nodes,'parameters':params}
paths=[P+'/Accessories14/SK_PKM_Manny_Modular',P+'/OpticMount23/SM_PKM_optic_rail']
paths+=list(E.list_assets(P+'/Bipod26',recursive=False,include_folder=False))
paths+=list(E.list_assets(P+'/Accessories14/Meshes',recursive=False,include_folder=False))
for path in paths:
 mesh=u.load_asset(path)
 if not isinstance(mesh,(u.SkeletalMesh,u.StaticMesh)):continue
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 out['meshes'][mesh.get_path_name()]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]
 for s in slots:
  m=s.material_interface
  if m and m.get_path_name().startswith(P+'/') and m.get_path_name() not in out['materials']:
   out['materials'][m.get_path_name()]=describe(m)
table=u.load_asset(P+'/Finish20/DA_PKM_WetMaterials')
for k,v in table.get_editor_property('wet_materials').items():
 if v:
  out['wet_materials'][str(k)]=v.get_path_name()
  if str(k) in out['materials']:out['materials'][v.get_path_name()]=describe(v)
ref_receipt=json.loads((O.parent/'SVDRefinedFinish20260923/finish_receipt.json').read_text())
ref_path=next(v['dry'] for k,v in ref_receipt['materials'].items() if 'InterfaceSteel' in k)
ref=u.load_asset(ref_path);out['references']['SVD']=dict(path=ref_path,**describe(ref))
(O/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('PKM_FINISH_INPUTS',json.dumps({'meshes':len(out['meshes']),'materials':len(out['materials']),'svd':ref_path}),flush=True)
