"""Install one assembly, retain its placement, and remove the replaced loose scene actors."""
from pathlib import Path
from datetime import datetime
import json,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
CFG=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text());BPS=json.loads((ROOT/'Receipts/blueprints.json').read_text());SRC=json.loads((ROOT/'Config/sources.json').read_text())
if BPS['stage']!='blueprints_saved':raise RuntimeError('Blueprint build incomplete')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if globals().get('WORKBENCH_MAP_WAS_CLEAN',False):dirty=[p for p in dirty if p.get_name()!=TARGET]
allowed_external=set(globals().get('WORKBENCH_DIRTY_EXTERNAL_PACKAGES',[]))
dirty=[p for p in dirty if p.get_name() not in allowed_external]
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()};placement=CFG['placement'];old=actors.get(placement['actor_label'])
full_rebuild=globals().get('WORKBENCH_FULL_REBUILD',False)
if old and '/WorkbenchKit/Blueprints/BP_Workbench_' not in old.get_class().get_path_name():raise RuntimeError('Preserve actor with different ownership '+placement['actor_label'])
inputs=json.loads((ROOT/'Sources/original-scene-inputs.json').read_text());snapshot={r['label']:r for r in inputs['actors']}
owned={e['old_actor']:e for e in MAN['components'] if e.get('old_actor')}
for label,e in owned.items():
    a=actors.get(label)
    if not a:
        if old or full_rebuild:continue
        raise RuntimeError('Required original component missing '+label)
    c=a.get_component_by_class(u.StaticMeshComponent)
    # The current revision is already declared in the single source selection, never silently replace another revision.
    if not full_rebuild and (not c or not c.static_mesh or c.static_mesh.get_path_name()!=e['expected_mesh']):raise RuntimeError('Preserve different component revision '+label)
backup=ROOT/'Sources/L_Dungeon_Prototype_before_kit.umap'
if not backup.exists():shutil.copy2(ROOT.parents[1]/'Content/GameMaps/L_Dungeon_Prototype.umap',backup)
bp=u.load_asset(BPS['blueprints'][placement['variant']]);cls=bp.generated_class();new=old
if old and old.get_class()!=cls:
    new=AA.spawn_actor_from_class(cls,old.get_actor_location(),old.get_actor_rotation());new.set_actor_scale3d(old.get_actor_scale3d());AA.destroy_actor(old)
elif not old:new=AA.spawn_actor_from_class(cls,u.Vector(*CFG['root']['world_location']),u.Rotator(roll=CFG['root']['world_rotation'][0],pitch=CFG['root']['world_rotation'][1],yaw=CFG['root']['world_rotation'][2]))
if not new:raise RuntimeError('Assembly spawn failed')
new.modify();new.set_actor_label(placement['actor_label']);new.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/WorkbenchKit')
new.set_editor_property('tags',[u.Name('WorkbenchKit'),u.Name('Variant_'+placement['variant']),u.Name('LayoutLocked' if placement['locked'] else 'LayoutEditable')])
removed=[]
for label in list(owned)+[SRC['legacy_cable'],SRC['legacy_light']]:
    a=actors.get(label)
    if a:
        a.modify()
        if not AA.destroy_actor(a):raise RuntimeError('Cannot replace original actor '+label)
        removed.append(label)
# Hidden previous revisions remain hidden; no source assets are deleted.
receipt=dict(stage='placing',actor=placement['actor_label'],variant=placement['variant'],blueprint=bp.get_path_name(),removed_loose_actors=removed,tests_run=False,screenshots_taken=False)
(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if not ED.save_current_level():raise RuntimeError('Map save failed; preserve live changes')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat());(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WORKBENCH_KIT_MAP_SAVED '+json.dumps(receipt))
