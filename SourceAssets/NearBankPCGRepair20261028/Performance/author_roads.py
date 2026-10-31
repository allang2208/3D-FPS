from pathlib import Path
import runpy,shutil,json,unreal as u
R=Path(__file__).resolve().parent
if not (R/'collider_backup.json').exists():
    C=R.parents[2]/'Content';backup=R/'Backups/OriginalVehicleCollision';saved=[]
    for src in (C/'NativeNearBank20261028/Repair/Collision').glob('SM_VehicleEnvelope_*.uasset'):
        dst=backup/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);saved.append(str(src))
    (R/'collider_backup.json').write_text(json.dumps(dict(path=str(backup),files=saved),indent=2))
scope=runpy.run_path(str(R.parent/'Repair/author_meshes.py'))
scope['main'].__globals__['R']=R
scope['main']()
print('CONTINUOUS_ROAD_ASSETS_SAVED')
