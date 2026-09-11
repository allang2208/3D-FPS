import unreal,json,hashlib,shutil
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/MonsterFeedback20260911';backup=out/'before';backup.mkdir(exist_ok=True)
lib=unreal.EditorAssetLibrary
bp=unreal.load_asset('/Game/Monsters/HandBrain/BP_HandBrain');cdo=unreal.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh');assert mesh
old=mesh.get_editor_property('physics_asset');record={'mesh':mesh.get_path_name(),'old_physics':old.get_path_name(),'backups':[]}
for asset in [mesh,bp]:
 p=root/'Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset');b=backup/p.name
 if not b.exists():shutil.copy2(p,b)
 record['backups'].append({'path':str(b),'sha256':hashlib.sha256(b.read_bytes()).hexdigest()})
pa=unreal.HandBrainMonster.create_physics_asset(mesh);assert pa
cdo.mesh.set_physics_asset(pa,True)
for asset in [pa,mesh,bp]:assert lib.save_loaded_asset(asset,False)
record['physics']=pa.get_path_name();record['saved']=True
(out/'handbrain-physics.json').write_text(json.dumps(record,indent=2))
unreal.log('HANDBRAIN_ACTIVE_PHYSICS_SAVED '+json.dumps(record))
