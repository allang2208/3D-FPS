"""Wind responses for the hills' existing foliage materials and Bracken wind skeletons."""
import runpy
from pathlib import Path

import unreal as u


ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
BASE = '/Game/WorldGeneration/TemperateHills'
SHRUB = BASE + '/Atmosphere20261110/M_ForestShrubWind'
UNDERFOOT = BASE + '/WetForest/Underfoot/'
FERN_SOURCE = '/Game/Megaplant_Library/Plant_Bracken_Fern/Plant_Bracken_Fern_01/Plant_Bracken_Fern_01_'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary

SHRUB_SWAY = '''
float3 upVector = UpWorld - RootWorld;
float3 up = upVector / max(length(upVector), 0.0001);
float3 downwind = float3(Wind.xy, 0);
downwind -= up * dot(downwind, up);
float windLength = length(downwind);
if (windLength < .0001) return float3(0, 0, 0);
float3 axis = cross(up, downwind / windLength);
// All vertices, including the wood and the leaves, use the same instance pivot and angle.
float phase = dot(RootWorld.xy, float2(.0017, .0011));
float swayWeight = .67 + .33 * sin(Time * .57 + phase);
float angle = radians(clamp(Strength, 0, .65)) * clamp(Wind.z, 0, 1.1) * swayWeight;
float s, c;
sincos(angle, s, c);
float3 relative = WorldPos - RootWorld;
return relative * (c - 1) + cross(axis, relative) * s + axis * dot(axis, relative) * (1 - c);
'''

BLADE_SWAY = '''
float height = max(Local.z - .6, 0);
float lever = min(2.15, height * .065) * smoothstep(0, 12, height);
float ripple = .69 + .31 * sin(T * 1.8 + dot(P.xy, float2(.006, .009)));
return float3(W.xy * (clamp(W.z, 0, 1.1) * lever * ripple), 0);
'''

LEAF_SWAY = '''
float h = saturate(Local.z / 60);
float ripple = .74 + .26 * sin(T * 1.12 + dot(P.xy, float2(.003, .004)));
return float3(W.xy * (clamp(W.z, 0, 1.1) * 1.9 * h * h * ripple), 0);
'''


def apply_blade(wet, mat):
    # The three grasses share a material. Local rest height gives the taller
    # sedge more travel, and works with all three authored LODs.
    node = lambda cls, key: wet.node(mat, cls, key)
    wind = node(u.MaterialExpressionCollectionParameter, 'BladeWind')
    wind.set_editor_property('collection', u.load_asset(wet.MPC))
    wind.set_editor_property('parameter_name', 'ForestWind')
    position = node(u.MaterialExpressionWorldPosition, 'WorldPosition')
    position.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    sway = wet.custom(mat, 'BladeSway', BLADE_SWAY, {
        'Local': node(u.MaterialExpressionPreSkinnedPosition, 'BladeLocal'),
        'W': wind, 'P': position, 'T': node(u.MaterialExpressionTime, 'BladeTime')}, 3)
    wet.connect(mat, 'WORLD_POSITION_OFFSET', sway)


def fern_profile(mesh):
    prefix = 'SK_BrackenFern_'
    variant = mesh.get_name().removeprefix(prefix)
    if variant not in ('A', 'B', 'C', 'D') or mesh.get_name() != prefix + variant:
        raise RuntimeError('Unrecognised hills fern: ' + mesh.get_path_name())

    def wind_data(asset):
        return next(data for data in asset.get_editor_property('asset_user_data')
                    if data and data.get_class().get_name() == 'DynamicWindSkeletalData')

    source = wind_data(u.load_asset(FERN_SOURCE + variant))
    target = wind_data(mesh)
    groups = list(source.get_editor_property('SimulationGroups'))
    # Use the original import every time. Preserve group membership, zero weights
    # and the authored difference between single and dual influence.
    for group in groups:
        factor = .24 if group.get_editor_property('bIsTrunkGroup') else .35
        for field in ('Influence', 'MinInfluence', 'MaxInfluence'):
            group.set_editor_property(field, group.get_editor_property(field) * factor)
    target.set_editor_property('SimulationGroups', groups)
    target.set_editor_property('bIsEnabled', True)
    target.set_editor_property('bIsGroundCover', True)
    target.set_editor_property('GustAttenuation', .94)


def update_material(path, tag, code):
    mat = u.load_asset(path)
    nodes = [n for n in L.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom)
             and str(n.get_editor_property('desc')) == tag]
    if len(nodes) != 1:
        raise RuntimeError(f'Expected one active wind expression in {path}, found {len(nodes)}')
    nodes[0].set_editor_property('code', code)
    return mat


def main():
    import types

    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if commandlet:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        for setting in ('Editor.AsyncSkinnedAssetCompilation 0', 'Editor.AsyncStaticMeshCompilation 0', 'gc.AllowParallelGC 0'):
            u.SystemLibrary.execute_console_command(world, setting)
    fern_paths = [BASE + '/ForestSpecies20261110/Meshes/SK_BrackenFern_' + v for v in 'ABCD']
    targets = [SHRUB, UNDERFOOT + 'M_FoldedForestBlade', UNDERFOOT + 'M_JungleGinger']
    packages = set(targets + fern_paths)
    if any(p.get_path_name() in packages for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('An understory target has unsaved edits')
    if not commandlet and u.EditorLevelLibrary.get_pie_worlds(False):
        raise RuntimeError('Understory targets are in use by PIE')
    wet = types.SimpleNamespace(**runpy.run_path(str(ROOT / 'Tools/WorldGeneration/forest_wet_materials.py')))
    u.log('HILLS_UNDERSTORY_WIND authoring material expressions')
    shrub = update_material(SHRUB, 'ForestAtmosphere20261110V1', SHRUB_SWAY)
    grass = u.load_asset(targets[1])
    apply_blade(wet, grass)
    herb = update_material(targets[2], wet.TAG + 'LeafSway', LEAF_SWAY)
    for mat in (shrub, grass, herb):
        # A wind-only change leaves the texture UVs and streaming data intact.
        # Notify the material to update its expression cache and shader StateId
        # without the editor utility's unrelated UV-density bake / global GC.
        bound = mat.get_editor_property('max_world_position_offset_displacement')
        mat.set_editor_property('max_world_position_offset_displacement', bound, u.PropertyAccessChangeNotifyMode.ALWAYS)
        if not E.save_loaded_asset(mat, False):
            raise RuntimeError('Unable to save ' + mat.get_path_name())
    for path in fern_paths:
        u.log('HILLS_UNDERSTORY_WIND authoring ' + path)
        mesh = u.load_asset(path)
        fern_profile(mesh)
        if not E.save_loaded_asset(mesh, False):
            raise RuntimeError('Unable to save ' + path)
    u.log(f'HILLS_UNDERSTORY_WIND_SAVED materials=3 ferns={len(fern_paths)}')


if __name__ == '__main__':
    main()
