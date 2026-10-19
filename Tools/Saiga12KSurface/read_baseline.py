import unreal as u,json,hashlib,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018';L=u.MaterialEditingLibrary
prior=json.loads((P/'SourceAssets/Saiga12KRefine20261017/Receipts/assets.json').read_text());root='/Game/Weapons/Saiga12K/Refined20261017'
paths={'native':root+'/SK_Saiga12K_Manny','ext12':'/Game/Weapons/Saiga12K/ExtendedMagazine20261017/SM_Saiga12K_Ext12'}
paths.update({k:root+'/Attachments/SM_Saiga12K_'+k for k in prior['bindings'] if k!='native'})
R={'assets':{},'materials':{}}
for key,path in paths.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing current asset '+path)
 slots=a.materials if key=='native' else a.static_materials;R['assets'][key]={'path':a.get_path_name(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 for s in slots:
  m=s.material_interface
  if not m or m.get_path_name() in R['materials']:continue
  row={'base':m.get_base_material().get_path_name(),'blend_mode':str(m.get_base_material().blend_mode)};R['materials'][m.get_path_name()]=row
  row['scalars']={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
  row['vectors']={str(n):[getattr(L.get_material_instance_vector_parameter_value(m,n),c) for c in 'rgba'] for n in L.get_vector_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
  row['textures']={str(n):(L.get_material_instance_texture_parameter_value(m,n).get_path_name() if L.get_material_instance_texture_parameter_value(m,n) else None) for n in L.get_texture_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {}
sys.path.insert(0,str(P/'Tools/Saiga12KSurface'));from mesh_contract import arm_contract
R['arms']=arm_contract(u.load_asset(paths['native']))
(O/'Reports/baseline.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_SURFACE_BASELINE',len(paths),len(R['materials']))
