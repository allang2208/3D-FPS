"""Read the retained pre-movement robe assets; never resave them."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';O=R/'ClothRollback20261019'
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
report={'variants':{},'saved_any_assets':False,'simulation_tested':False}
for revision in ('HipFit20261019','MovementFit20261019'):
 data=json.loads((R/revision/'saved_assets.json').read_text())
 for key,row in data['saved'].items():
  if not key.startswith('Body/'):continue
  path=row['asset'];disk=P/'Content'/(path.split('.')[0][6:]+'.uasset');raw=disk.read_bytes();mesh=u.load_asset(path)
  if not mesh:raise RuntimeError('Missing '+path)
  cloths=mesh.get_editor_property('mesh_clothing_assets');physics=mesh.get_editor_property('physics_asset')
  if len(cloths)!=1 or not physics:raise RuntimeError('Incomplete cloth '+path)
  cloth=cloths[0];shared=next(c for c in cloth.get_editor_property('cloth_configs').values() if c.get_class().get_name()=='ChaosClothSharedSimConfig')
  if cloth.get_editor_property('physics_asset')!=physics:raise RuntimeError('Pose/cloth collision differ '+path)
  report['variants'][revision+'/'+key]={'asset':path,'package_sha256':hashlib.sha256(raw).hexdigest(),'lod_count':S.get_lod_count(mesh),'cloth':cloth.get_path_name(),'physics':physics.get_path_name(),'substeps':shared.get_editor_property('SubdivisionCount'),'geometry_sha256':row['author_sha256'],'package_unchanged':disk.read_bytes()==raw}
  print('ROBE_ROLLBACK_READ',revision,key,'substeps',shared.get_editor_property('SubdivisionCount'),flush=True)
report['completed']=True
(O/'asset-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
