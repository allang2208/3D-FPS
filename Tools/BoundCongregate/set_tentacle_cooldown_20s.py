"""Save the live monster's whip cooldown without rebuilding its native module."""
import unreal as u

path = '/Game/Monsters/BoundCongregate/BP_BoundCongregate'
bp = u.load_asset(path)
if not bp:
    raise RuntimeError('BoundCongregate blueprint is unavailable.')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty and not globals().get('BC_COOLDOWN_PENDING_SAVE', False):
    raise RuntimeError('Preserve the existing unsaved BoundCongregate blueprint changes.')
monster_class = bp.generated_class()
defaults = u.get_default_object(monster_class)
previous = defaults.get_editor_property('tentacle_cooldown')
defaults.set_editor_property('tentacle_cooldown', 20.0)
bp.modify()
BC_COOLDOWN_PENDING_SAVE = True

# A scalar tuning change is safe for existing PIE actors. Do not compile the
# blueprint, restart PIE, trigger attacks or change an attack already underway.
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
updated = 0
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, monster_class):
        actor.set_editor_property('tentacle_cooldown', 20.0)
        updated += 1
print(f'BOUND_WHIP_COOLDOWN_APPLIED previous={previous} seconds=20 live_actors_updated={updated}')
# Save the editor content package, never its PIE duplicate. The general asset
# library rejects all PIE calls, while the package-saving API supports saving
# editor content without rebuilding the class or replacing live actors.
if not u.EditorLoadingAndSavingUtils.save_packages([bp.get_outermost()], False):
    raise RuntimeError('Could not save the whip cooldown.')
BC_COOLDOWN_PENDING_SAVE = False
print('BOUND_WHIP_COOLDOWN_SAVED')
