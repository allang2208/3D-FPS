from pathlib import Path
from datetime import datetime
import json,shutil,hashlib,runpy,unreal as u
R=Path(__file__).resolve().parent;P=R.parent;PROJECT=P.parents[1];C=PROJECT/'Content';L=PROJECT/'SourceAssets/CyberpunkNearBank20261028'
MAP='/Game/GameMaps/L_CyberpunkApartment'
def main():
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('Game must finish before publication')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    marker=R/'repair_backup.json'
    if not marker.exists():
        backup=P/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/'RoadRepair';files=[C/'GameMaps/L_CyberpunkApartment.umap']+list((C/'NativeNearBank20261028').rglob('*.uasset'))
        files+=list((C/'Props/CyberpunkNearBank20261028/Blueprints').glob('BP_NB_Cell_*.uasset'))
        files+=[C/'Props/CyberpunkNearBank20261028/Textures/T_NB_CityReflection.uasset',C/'Props/CyberpunkNearBank20261028/Materials/MI_NB_BayWater.uasset']
        known={x['path']:x['sha256'].lower() for x in json.loads((P/'Audit/snapshot.json').read_text())['files']}
        for f in files:
            rel=f.relative_to(C)
            if rel.as_posix() in known and hashlib.sha256(f.read_bytes()).hexdigest()!=known[rel.as_posix()]:raise RuntimeError('Audited source changed '+str(rel))
            dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
        marker.write_text(json.dumps(dict(backup=str(backup),files=[str(f.relative_to(C)) for f in files]),indent=2))
    runpy.run_path(str(R/'author_meshes.py'),run_name='__main__')
    shutil.copy2(R/'repaired_manifest.json',P/'publish_manifest.json')
    shutil.copy2(R/'legacy_layout.json',L/'layout.json')
    runpy.run_path(str(P/'build_publish_assets.py'),run_name='__main__')
    legacy=runpy.run_path(str(L/'build_assets.py'));legacy['assemblies']()
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    installer=runpy.run_path(str(P/'install_level.py'));result=installer['apply_upgrade'](world)
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    old_assets=json.loads((L/'assets_saved.json').read_text());cells=[]
    for name,row in old_assets['blueprints'].items():
        if not name.startswith('BP_NB_Cell_'):continue
        label='NB28_Cell_'+name.rsplit('_',1)[-1];old=actors.get(label)
        if old and not old.actor_has_tag('CyberpunkApartment.NearBank20261028'):raise RuntimeError('Unowned legacy cell '+label)
        if old:aa.destroy_actor(old)
        a=aa.spawn_actor_from_class(u.EditorAssetLibrary.load_blueprint_class(row['path'].split('.')[0]),u.Vector(*[v*100 for v in row['origin']]))
        a.set_actor_label(label);a.set_folder_path('Apartment20261022/NearBank20261028');a.set_editor_property('tags',[u.Name('CyberpunkApartment.NearBank20261028')]);a.set_actor_tick_enabled(False);cells.append(label)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save formal map')
    result.update(stage='formal_map_saved',legacy_cells=cells,repair='20261028-v1',saved_at=datetime.now().astimezone().isoformat(),backup=json.loads(marker.read_text())['backup'])
    (P/'installed.json').write_text(json.dumps(result,indent=2));(R/'published.json').write_text(json.dumps(result,indent=2))
    print('ROAD_REPAIR_FORMAL_MAP_SAVED',len(result['blocks']),len(cells),result['instances'],flush=True)
if __name__=='__main__':main()
