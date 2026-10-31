"""Replace only the previous six near-bank buildings and simple road assembly."""
from pathlib import Path
from datetime import datetime
import json,shutil,unreal as u
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
MAP='/Game/GameMaps/L_CyberpunkApartment';OWNER='CyberpunkApartment.NearBankNativePCG20261028'

def apply_upgrade(world):
    if not world or world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong formal world')
    assets=json.loads((R/'publish_assets.json').read_text())
    if assets['stage']!='blocks_saved':raise RuntimeError('Native blocks not saved')
    classes={b['path']:E.load_blueprint_class(b['path'].split('.')[0]) for b in assets['blocks']}
    if not all(classes.values()):raise RuntimeError('Selected blocks unresolved')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    placed=[]
    for row in assets['blocks']:
        label=row['label'];a=actors.get(label)
        if a and not a.actor_has_tag(OWNER):raise RuntimeError('Preserve unowned actor '+label)
        if a:aa.destroy_actor(a);a=None
        if not a:a=aa.spawn_actor_from_class(classes[row['path']],u.Vector(*row['origin']))
        a.modify();a.set_actor_label(label);a.set_folder_path('Apartment20261022/NativeNearBank20261028')
        a.set_editor_property('tags',[u.Name(OWNER)]);a.set_actor_tick_enabled(False)
        placed.append(label)
    retired=[]
    legacy={'NB28_Neighborhood_Streets'}|{f'NB28_N1_{i:02d}' for i in range(1,7)}
    for label,a in actors.items():
        if label in placed:continue
        if label in legacy:
            if not a.actor_has_tag('CyberpunkApartment.NearBank20261028'):raise RuntimeError('Legacy ownership changed '+label)
            aa.destroy_actor(a);retired.append(label)
        elif a.actor_has_tag(OWNER) and label not in placed:aa.destroy_actor(a)
    return dict(map=MAP,blocks=placed,instances=assets['instances'],retired=retired,opposite_bank_modified=False,game_run=False,tests_run=False)

E=u.EditorAssetLibrary
def main():
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('Preserve running game')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP);result=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save formal apartment')
    result.update(stage='formal_map_saved',backup=str(backup),saved_at=datetime.now().astimezone().isoformat())
    (R/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('NATIVE_NEAR_BANK_INSTALLED',len(result['blocks']),result['instances'],flush=True)
if __name__=='__main__':main()
