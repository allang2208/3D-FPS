"""Archive the two explicitly retired test maps, then remove their UE assets."""
from pathlib import Path
import hashlib,json,shutil
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if e and e.get_game_world():raise RuntimeError('PIE is running; keep the maps until the asset batch is free')
if not json.loads((ROOT/'Receipts/map.json').read_text(encoding='utf8'))['saved']:
    raise RuntimeError('Save the accepted hub before retiring its old destinations')
targets=['/Game/Clearwater/L_ClearwaterWater','/Game/GameMaps/L_GrassDeformDenseTest']
report={'retired':[],'shared_water_and_grass_assets_preserved':True,'hills_preserved':True,'tested':False}
for asset in targets:
    relative=Path('Content')/(asset.removeprefix('/Game/')+'.umap')
    source=(PROJECT/relative).resolve()
    dest=(PROJECT/'trash/godspace-layout-20260927/Retired'/relative).resolve()
    if not source.is_relative_to((PROJECT/'Content').resolve()) or not dest.is_relative_to((PROJECT/'trash/godspace-layout-20260927/Retired').resolve()):
        raise RuntimeError('Archive target is outside this task')
    if not source.exists():continue
    if any(p.get_path_name()==asset for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
        raise RuntimeError('Retired map has unsaved edits: '+asset)
    row={'asset':asset,'source':str(source),'archive':str(dest),'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reason':'User retired pool and grass test scenes; keep hills'}
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(source,dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Archive does not match the current map')
    if not u.EditorAssetLibrary.delete_asset(asset):raise RuntimeError('UE could not remove the archived map: '+asset)
    report['retired'].append(row)
    (ROOT/'Receipts/retired-maps.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('TEST_MAPS_RETIRED '+str(len(report['retired'])))
