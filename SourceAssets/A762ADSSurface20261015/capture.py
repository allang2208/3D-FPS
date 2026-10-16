"""Read the current A762 surface inputs; no asset or world changes."""
import unreal as u, json, hashlib
from pathlib import Path
O=Path(__file__).parent; P=O.parents[1]; X=O/'Input'; X.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary; E=u.EditorAssetLibrary
R={'assets':{},'materials':{},'textures':{},'runtime_components':[],'read_only':True}
helper=(P/'SourceAssets/TelescopicAllGunsAudit20261015/capture.py').read_text(encoding='utf-8')
exec(compile(helper[helper.index('def record():'):helper.index('sms=')],'<graph_helpers>','exec'))
paths=['/Game/Weapons/A762/Integrated20260920/SK_A762_Manny']
paths += ['/Game/'+str(p.relative_to(P/'Content').with_suffix('')).replace('\\','/') for p in (P/'Content/Weapons/A762/Accessories05/Meshes').glob('*.uasset')]
for path in paths:
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
 R['assets'][path]={'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'material':material(s.material_interface) if s.material_interface else None} for s in slots]}
 record()
for path,row in R['materials'].items():
 m=u.load_asset(path); base=m.get_base_material()
 row['sha256']=hashlib.sha256(disk(path).read_bytes()).hexdigest()
 row['vectors']={str(n):[v.r,v.g,v.b,v.a] for n in L.get_vector_parameter_names(base) for v in [L.get_material_instance_vector_parameter_value(m,n)]} if isinstance(m,u.MaterialInstanceConstant) else {}
 row['blend_mode']=str(base.blend_mode)
for cls in (u.StaticMeshComponent,u.SkeletalMeshComponent):
 for comp in u.ObjectIterator(cls):
  mesh=comp.static_mesh if cls==u.StaticMeshComponent else comp.get_skinned_asset()
  if not mesh or mesh.get_path_name().split('.')[0] not in paths:continue
  R['runtime_components'].append({'path':comp.get_path_name(),'mesh':mesh.get_path_name(),'materials':[comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]})
R['dirty_packages']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
R['complete']=True;record()
print('A762_ADS_INPUTS',len(R['assets']),len(R['materials']),flush=True)
