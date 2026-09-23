"""Read the actual SVD finish/assembly inputs needed for this production batch."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
P='/Game/Weapons/SVDDragunov20260922'
paths={'viewmodel':P+'/StockAdapter20260923/SK_SVD_ModularStock'}
for k,v in json.loads((S/'SVDAttachments20260923/authoring.json').read_text())['meshes'].items():
 paths[k]=P+'/Accessories20260923/Meshes/'+v['name']
for k in ['skeleton','core_stock','qr_performance','tactical_telescopic']:paths[k]=P+'/StockAdapter20260923/Meshes/SM_SVD_'+k
ref=u.load_asset('/Game/Weapons/A762/Refinement03/Materials/M_A762_UpperReceiver03')
color=L.get_material_default_vector_parameter_value(ref,'FinishColor')
out={'reference':{'asset':ref.get_path_name(),'color':[color.r,color.g,color.b],
 'metallic':L.get_material_default_scalar_parameter_value(ref,'Metallic'),
 'roughness':L.get_material_default_scalar_parameter_value(ref,'RoughnessCenter'),
 'texture':'/Game/Weapons/A762/Refinement03/Textures/T_A762_RebuiltFinish'},'meshes':{},'materials':{}}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing current SVD mesh '+path)
 skeletal=isinstance(mesh,u.SkeletalMesh);slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
 out['meshes'][key]={'asset':path,'skeletal':skeletal,'source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),
 'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 for s in slots:
  m=s.material_interface
  if not m or m.get_path_name() in out['materials']:continue
  base=m.get_base_material();custom=[];parameters={}
  for n in L.get_material_expressions(base):
   if isinstance(n,u.MaterialExpressionCustom):custom.append({'name':n.get_name(),'description':str(n.get_editor_property('description')),'inputs':[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]})
  for kind in ['scalar','vector','texture']:
   parameters[kind]={}
   for name in getattr(L,'get_'+kind+'_parameter_names')(base):
    v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name) if isinstance(m,u.MaterialInstanceConstant) else getattr(L,'get_material_default_'+kind+'_parameter_value')(base,name)
    parameters[kind][str(name)]=v.get_path_name() if kind=='texture' and v else [v.r,v.g,v.b,v.a] if kind=='vector' else v
  out['materials'][m.get_path_name()]={'base':base.get_path_name(),'blend':str(base.blend_mode),'custom':custom,'parameters':parameters}
table=u.load_asset(P+'/Accessories20260923/DA_SVD_AttachmentWetMaterials')
out['wet_materials']={str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v}
(O/'inputs.json').write_text(json.dumps(out,indent=2))
print('SVD_HAND_FINISH_INPUTS',len(out['meshes']),len(out['materials']),out['reference'],flush=True)
