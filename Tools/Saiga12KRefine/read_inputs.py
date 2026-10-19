import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KRefine20261017'
L=u.MaterialEditingLibrary
sources=json.loads((P/'SourceAssets/Saiga12KCommon20261017/Receipts/assets.json').read_text())['parts']
paths={'native':'/Game/Weapons/Saiga12K/Integrated20261017/SK_Saiga12K_Manny'}
paths.update({k:v['path'] for k,v in sources.items()})
R={'assets':{},'materials':{}}
for key,path in paths.items():
 obj=u.load_asset(path)
 if not obj:raise RuntimeError(path)
 slots=obj.materials if key=='native' else obj.static_materials
 R['assets'][key]={'path':obj.get_path_name(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 if key=='native':
  dm,st=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(obj,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
  R['assets'][key]['uv_sets']=u.GeometryScript_MeshQueries.get_num_uv_sets(dm)
 for s in slots:
  m=s.material_interface
  if not m or m.get_path_name() in R['materials']:continue
  row={'class':m.get_class().get_name(),'base':m.get_base_material().get_path_name()};R['materials'][m.get_path_name()]=row
  row['blend_mode']=str(m.get_base_material().get_editor_property('blend_mode'))
  row['literal_textures']=[]
  for expression in L.get_material_expressions(m.get_base_material()):
   try:
    texture=expression.get_editor_property('texture')
    if texture and texture.get_path_name() not in row['literal_textures']:row['literal_textures'].append(texture.get_path_name())
   except Exception:pass
  row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
  row['vectors']={str(n):[getattr(L.get_material_instance_vector_parameter_value(m,n),c) for c in 'rgba'] for n in L.get_vector_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
  row['textures']={str(n):(L.get_material_instance_texture_parameter_value(m,n).get_path_name() if L.get_material_instance_texture_parameter_value(m,n) else None) for n in L.get_texture_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
 (O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('SAIGA_REFINEMENT_INPUTS',len(R['assets']),len(R['materials']))
