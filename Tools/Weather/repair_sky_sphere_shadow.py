"""Persist the known sky-backdrop shadow fix via PythonScript commandlet or an existing editor.

Only a component default changes; do not compile/reinstance the Blueprint,
start/stop PIE, change materials or save unrelated packages.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

project = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
target = '/Game/Lighting/BP_FPS_DayNightManager'
mesh_path = '/Engine/EngineSky/SM_SkySphere.SM_SkySphere'
out = project / 'Saved/VsmOverflow20261016'
out.mkdir(parents=True, exist_ok=True)
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if target in dirty:
    raise RuntimeError('Sky Blueprint has unsaved edits; preserve them without saving this package.')

bp = u.load_asset(target)
subsystem = u.get_engine_subsystem(u.SubobjectDataSubsystem)
functions = u.SubobjectDataBlueprintFunctionLibrary
candidates = {}
for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
    component = functions.get_object_for_blueprint(functions.get_data(handle), bp)
    if (isinstance(component, u.StaticMeshComponent) and component.static_mesh
            and component.static_mesh.get_path_name() == mesh_path
            and component.get_name() == 'SM_SkySphere_GEN_VARIABLE'
            and component.get_path_name().startswith(target + '.')):
        candidates[component.get_path_name()] = component
print('SKY_TEMPLATE_CANDIDATES ' + json.dumps(list(candidates)))
generated = {path:component for path,component in candidates.items() if component.get_outer() == bp.generated_class()}
if generated:
    candidates = generated
if len(candidates) != 1:
    raise RuntimeError('Expected one generated sky sphere template; found ' + json.dumps(list(candidates)))

component = next(iter(candidates.values()))
source = project / 'Content/Lighting/BP_FPS_DayNightManager.uasset'
before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
backup = out / ('BP_FPS_DayNightManager-before-' + before_hash[:12] + '.uasset')
if not backup.exists():
    shutil.copy2(source, backup)
receipt = {'utc':datetime.now(timezone.utc).isoformat(), 'asset':target,
           'component_template':component.get_path_name(), 'backup':str(backup),
           'before_sha256':before_hash, 'cast_shadow_before':bool(component.cast_shadow),
           'saved':False, 'runtime_instances_updated':[], 'runtime_tested':False}
component.set_editor_property('cast_shadow', False)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save the sky Blueprint; source backup retained.')
receipt['saved'] = True
receipt['cast_shadow_after'] = bool(component.cast_shadow)
receipt['after_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()

# Apply that same correction to existing gameplay instances. No map is saved,
# no scene is loaded and no test or recording is initiated.
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world() if editor else None
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, bp.generated_class()):
        for instance in actor.get_components_by_class(u.StaticMeshComponent):
            if (instance.get_name() == 'SM_SkySphere' and instance.static_mesh
                    and instance.static_mesh.get_path_name() == mesh_path):
                instance.set_cast_shadow(False)
                receipt['runtime_instances_updated'].append(instance.get_path_name())
(out / 'sky-shadow-install.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print(json.dumps(receipt))
