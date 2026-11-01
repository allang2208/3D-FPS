"""Use the recognized M24 chassis master without changing its effective dry finish."""
import unreal as u, json, shutil
from pathlib import Path
O=Path(__file__).resolve().parent
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
data=json.loads((O/'inputs.json').read_text(encoding='utf-8'))
parent=u.load_asset('/Game/Weapons/M24/AdvancedAction20261029/Materials/M_M24AdvancedSurface')
if not parent:raise RuntimeError('Missing active chassis master')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report={'complete':False,'saved':[],'change':'Restore weather-recognized M24 parent; preserve all effective finish inputs'}
for path,row in data['materials'].items():
    if '/StockMetalFinish20261031/' not in path or 'M_M24MetalSurface' not in row['master']:continue
    if path.split('.')[0] in dirty:raise RuntimeError('Unsaved material retained '+path)
    if abs(row['parameters']['scalar'].get('ContinuityNormalStrength',0)-1)>1e-6:
        raise RuntimeError('Normal modifier is not identity; retain current graph')
    # The old private master duplicates this master plus a final normal scale.
    baseline=next(v for v in data['materials'].values() if v['master']==parent.get_path_name())
    old_codes={x['description']:x['code'] for x in row['codes'] if x['description']!='M24 restrained source normals'}
    if old_codes!={x['description']:x['code'] for x in baseline['codes']}:
        raise RuntimeError('Parent graphs no longer share the expected finish code')
    material=u.load_asset(path)
    disk=Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    backup=O/'BeforeRepair'/disk.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(disk,backup)
    L.set_material_instance_parent(material,parent)
    for kind,values in row['parameters'].items():
        for name,value in values.items():
            if name=='ContinuityNormalStrength':continue
            if kind=='vector':value=u.LinearColor(*value)
            elif kind=='texture':value=u.load_asset(value) if value else None
            if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(material,name,value)
    L.update_material_instance(material)
    if not E.save_loaded_asset(material,False):raise RuntimeError('Save failed '+path)
    report['saved'].append({'material':path,'parent':material.get_editor_property('parent').get_path_name()})
report['complete']=True
(O/'repair_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_MASTER_REPAIR_SAVED',len(report['saved']),flush=True)
