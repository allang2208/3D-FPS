"""Correct inherited polymer wet-response on the seven newly authored body finishes."""
import json, shutil, hashlib, unreal as u
from pathlib import Path
O=Path(__file__).resolve().parent
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
data=json.loads((O/'inputs.json').read_text(encoding='utf-8'))
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report={'complete':False,'saved':[],'runtime_weather_test':False}
targets=[]
for path,row in data['materials'].items():
    if '/StockMetalFinish20261031/' not in path:continue
    disk=Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    if path.split('.')[0] in dirty or hashlib.sha256(disk.read_bytes()).hexdigest()!=row['sha256']:
        raise RuntimeError('Concurrent material changes retained '+path)
    targets.append((path,row,disk))
for path,row,disk in targets:
    backup=O/'BeforeWeatherRepair'/disk.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(disk,backup)
    material=u.load_asset(path)
    response=1. if row['parameters']['scalar']['Metallic']>.5 else 2.
    L.set_material_instance_scalar_parameter_value(material,'RainSurfaceResponse',response)
    L.update_material_instance(material)
    if not E.save_loaded_asset(material,False):raise RuntimeError('Save failed '+path)
    report['saved'].append({'material':path,'before':row['parameters']['scalar'].get('RainSurfaceResponse'),
                            'after':L.get_material_instance_scalar_parameter_value(material,'RainSurfaceResponse')})
report['complete']=True
(O/'weather_repair_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
exec(compile((O/'read_inputs.py').read_text(encoding='utf-8'),str(O/'read_inputs.py'),'exec'),{'__file__':str(O/'read_inputs.py'),'__name__':'__main__'})
