"""Build the Clearwater candidate with native UE optics and the shared water FX contract.

Run through mcp_call_codex.ps1 -PythonScript while the editor is open, or the usual
Python commandlet when closed. The commandlet loads the candidate map for package
edits only; it does not start PIE, draw frames, or test anything.
Existing stable MIs are reparented only after the new masters have been saved.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir())
DATA = ROOT / 'SourceAssets/ClearwaterNative20260926'
DEST = '/Game/Clearwater'
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = []
META = json.loads((DATA / 'production.json').read_text(encoding='utf-8'))


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())


def compile_and_save(mat):
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed: ' + mat.get_path_name() + ' ' + str(errors))
    print('CLEARWATER_MATERIAL_COMPILED ' + mat.get_path_name())
    save(mat)


def node(mat, cls):
    return LIB.create_material_expression(mat, cls)


def wire(source, target, pin):
    source, output = source if isinstance(source, tuple) else (source, '')
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect ' + target.get_class().get_name() + '.' + pin)


def prop(mat, source, name):
    if not LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Cannot connect property ' + name)


def scalar(mat, name, value):
    n = node(mat, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', float(value))
    return n


def vector(mat, name, value):
    n = node(mat, u.MaterialExpressionVectorParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', u.LinearColor(*value))
    return n


def custom(mat, code, inputs, width, label):
    n = node(mat, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('description', label)
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, n, name)
    return n


def world_position(mat):
    n = node(mat, u.MaterialExpressionWorldPosition)
    n.set_editor_property('world_position_shader_offset',
                          u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    return n


def material(name):
    path = DEST + '/' + name
    mat = u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, DEST, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Cannot create ' + path)
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('tangent_space_normal', False)
    return mat


def build_surface():
    mat = material('M_ClearwaterWater_Native')
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    pos = world_position(mat)
    clock = node(mat, u.MaterialExpressionTime)
    wave = custom(mat, (DATA / 'WaveField.hlsl').read_text(encoding='utf-8'),
                  {'Position': pos, 'Clock': clock,
                   'WaveHeightScale': scalar(mat, 'WaveHeightScale', 1)}, 3, 'Clearwater spectrum, Z up')
    prop(mat, custom(mat, 'return float3(0,0,Wave.x);', {'Wave': wave}, 3, 'Resolved wave height cm'),
         'WORLD_POSITION_OFFSET')

    # Exact existing hit layout: xy world cm, z absolute game time, w strength.
    # RGBA is mandatory here: the default VectorParameter output drops its fourth channel.
    inputs = {'Position': pos, 'Clock': clock, 'Pilot': scalar(mat, 'WaterImpactEnabled', 1),
              'Depth': scalar(mat, 'WaterImpactDepth', 12),
              'Flow': (vector(mat, 'WaterImpactFlow', (.5, .5, 0, 1)), 'RGBA')}
    for i in range(8):
        inputs['Hit' + str(i)] = (vector(mat, 'WaterHit' + str(i), (0, 0, -10000, 0)), 'RGBA')
        inputs['Meta' + str(i)] = (vector(mat, 'WaterHitMeta' + str(i), (0, 1, 1, 0)), 'RGBA')
    for i in range(4):
        inputs['Wake' + str(i)] = (vector(mat, 'WaterWake' + str(i), (0, 0, 0, 0)), 'RGBA')
        inputs['WakeMotion' + str(i)] = (vector(mat, 'WaterWakeMotion' + str(i), (1, 0, 0, -10000)), 'RGBA')
    field = custom(mat, (ROOT / 'SourceAssets/RiverPilot20260923/RippleField.hlsl').read_text(),
                   inputs, 3, 'Shared water impacts and wakes')
    normal = custom(mat, 'return normalize(float3(-Wave.yz + Field.xy, 1));',
                    {'Wave': wave, 'Field': field}, 3, 'World normal, shared impact slopes')
    prop(mat, normal, 'NORMAL')
    prop(mat, custom(mat, 'return float3(.55,.63,.60)*Field.z;', {'Field': field}, 3, 'Foam albedo'), 'BASE_COLOR')
    prop(mat, custom(mat, 'return saturate(.02 + Field.z * .85);', {'Field': field}, 1, 'Foam BRDF weight'), 'OPACITY')
    camera = node(mat, u.MaterialExpressionCameraPositionWS)
    prop(mat, custom(mat, 'return lerp(.075 + .055*smoothstep(1500,14000,length(P-Cam)), .34, Field.z);',
                    {'P': pos, 'Cam': camera, 'Field': field}, 1, 'Distance-filtered water roughness'), 'ROUGHNESS')
    prop(mat, scalar(mat, 'WaterSpecular', .255), 'SPECULAR')
    volume = node(mat, u.MaterialExpressionSingleLayerWaterMaterialOutput)
    # Clearwater uses 1/metre; UE's output explicitly requires 1/centimetre.
    wire(vector(mat, 'ScatteringPerCm', (.00028, .00052, .00068, 0)), volume, 'ScatteringCoefficients')
    wire(vector(mat, 'AbsorptionPerCm', (.004, .00074, .00088, 0)), volume, 'AbsorptionCoefficients')
    wire(scalar(mat, 'WaterPhaseG', .8), volume, 'PhaseG')
    wire(scalar(mat, 'BehindWaterScale', 1), volume, 'ColorScaleBehindWater')
    compile_and_save(mat)
    return mat


def import_atlas():
    task = u.AssetImportTask()
    task.set_editor_property('filename', str(DATA / META['atlas']))
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('destination_name', 'T_ClearwaterCausticsAtlas')
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', False)
    TOOLS.import_asset_tasks([task])
    texture = u.load_asset(DEST + '/T_ClearwaterCausticsAtlas')
    if not texture:
        raise RuntimeError('Caustic atlas import failed')
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
    texture.set_editor_property('max_texture_size', META['width'])
    # The atlas uses explicit LOD0 with wrapped gutters; omitting cross-frame mips avoids
    # their bleed. One compressed 4096x2048 RGB atlas is a bounded ~4 MiB GPU allocation.
    texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(texture)
    return texture


def build_seabed(atlas):
    mat = material('M_ClearwaterSeabed_Native')
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NANITE, True)
    pos = world_position(mat)
    clock = node(mat, u.MaterialExpressionTime)
    tex = node(mat, u.MaterialExpressionTextureObject)
    tex.set_editor_property('texture', atlas)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    # TextureObject passes a real Texture2D + sampler, unlike a sampled float4 output.
    caus = custom(mat, '''
float depth = max(WaterLevel - Position.z, 0);
float3 sun = normalize(SunDirection + float3(0,0,1e-5));
float3 ray = refract(-sun, float3(0,0,1), 1.0/1.3335);
float2 uv = frac((Position.xy - ray.xy*depth/max(-ray.z,.1))/PatchCm);
float f = frac(Clock/LoopSeconds)*32;
float a = floor(f), b = fmod(a+1,32);
float2 inner = (4.5 + uv*503.0)/512.0;
float2 ua = (float2(fmod(a,8),floor(a/8))+inner)/float2(8,4);
float2 ub = (float2(fmod(b,8),floor(b/8))+inner)/float2(8,4);
float3 ca = Texture2DSampleLevel(Atlas,AtlasSampler,ua,0).rgb;
float3 cb = Texture2DSampleLevel(Atlas,AtlasSampler,ub,0).rgb;
float3 web = lerp(ca,cb,frac(f));
float submerged = smoothstep(0,8,depth);
float rangeFade = 1-smoothstep(2500,9000,length(Position-Camera));
float weight = Strength*Daylight*submerged*exp(-depth*.0015)*rangeFade;
return 1 + web*weight*3.0;
''', {'Position': pos, 'Camera': node(mat, u.MaterialExpressionCameraPositionWS), 'Clock': clock,
      'Atlas': tex, 'WaterLevel': scalar(mat, 'WaterLevelCm', 0),
      'SunDirection': vector(mat, 'SunDirection', (.8525, .0896, .5150, 0)),
      'PatchCm': scalar(mat, 'CausticPatchCm', META['patch_cm']),
      'LoopSeconds': scalar(mat, 'CausticLoopSeconds', META['loop_seconds']),
      'Strength': scalar(mat, 'CausticStrength', .8),
      'Daylight': scalar(mat, 'CausticDaylight', 1)}, 3, '32-frame interpolated seabed caustics')
    # Preserve a neutral lit seabed: caustics modulate reflected light, never emissive.
    base = custom(mat, '''
float2 p=Position.xy*.01;
float n=.5+.25*sin(p.x*1.1+sin(p.y*.7))+.25*sin(p.y*1.9-p.x*.4);
return float3(.30,.265,.20)*lerp(.65,1.1,n)*Caustic;
''', {'Position': pos, 'Caustic': caus}, 3, 'Lit sand and baked focusing')
    prop(mat, base, 'BASE_COLOR')
    prop(mat, scalar(mat, 'BedRoughness', .78), 'ROUGHNESS')
    compile_and_save(mat)
    return mat


def build_underwater():
    mat = material('M_ClearwaterUnderwater_Native')
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location', u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    scene = node(mat, u.MaterialExpressionSceneTexture)
    scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    pos = node(mat, u.MaterialExpressionWorldPosition)
    cam = node(mat, u.MaterialExpressionCameraPositionWS)
    fog = custom(mat, '''
float3 delta=PixelPos-Camera;
float distanceCm=length(delta);
// Rays leaving the water attenuate only to the waterline, not to the sky's far plane.
float exitT=delta.z>0 ? saturate((WaterLevel-Camera.z)/max(delta.z,.001)) : 1;
float metres=min(distanceCm*exitT,8000)*.01;
float3 transmission=exp(-float3(.428,.126,.156)*metres);
float3 water=float3(.035,.14,.13)*lerp(.025,1,saturate(Daylight));
float3 fogged=Scene.rgb*transmission + water*(1-transmission);
return lerp(Scene.rgb,fogged,saturate(Amount));
''', {'Scene': scene, 'PixelPos': pos, 'Camera': cam,
      'WaterLevel': scalar(mat, 'WaterLevelCm', 0),
      'Daylight': scalar(mat, 'WaterDaylight', 1),
      'Amount': scalar(mat, 'UnderwaterAmount', 0)}, 3, 'Water column, clipped to surface')
    prop(mat, fog, 'EMISSIVE_COLOR')
    compile_and_save(mat)
    return mat


def reparent(name, parent):
    path = DEST + '/' + name
    mi = u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(mi, parent)
    # Only parameters owned by this revision are set; unrelated instance data is preserved.
    if name == 'MI_ClearwaterWater':
        LIB.set_material_instance_scalar_parameter_value(mi, 'WaveHeightScale', 1)
        LIB.set_material_instance_scalar_parameter_value(mi, 'WaterImpactEnabled', 1)
        for i in range(8):
            LIB.set_material_instance_vector_parameter_value(mi, 'WaterHit' + str(i), u.LinearColor(0,0,-10000,0))
    save(mi)
    return mi


def bind_candidate_content(water, bed):
    plane = u.load_asset(DEST + '/SM_ClearwaterPlane')
    if not plane:
        raise RuntimeError('Missing existing candidate plane; restore the Clearwater geometry first')
    plane.set_material(0, water)
    save(plane)
    # Loading a UWorld object alone does not initialize the actor iteration state.
    # The background commandlet can load this one map without touching a live editor.
    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    world = (u.EditorLoadingAndSavingUtils.load_map(DEST + '/L_ClearwaterWater') if commandlet
             else u.load_object(None, DEST + '/L_ClearwaterWater.L_ClearwaterWater'))
    if not world:
        raise RuntimeError('Missing Clearwater candidate map')
    changed = False
    seabeds = 0
    lights_adjusted = 0
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
        if actor.actor_has_tag('ClearwaterSeabed'):
            actor.get_component_by_class(u.StaticMeshComponent).set_material(0, bed)
            changed = True
            seabeds += 1
    if not seabeds:
        raise RuntimeError('No candidate seabed available for binding; use the closed-editor commandlet')
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.DirectionalLight):
        r = actor.get_actor_rotation()
        # Correct only the known legacy authoring transform. Preserve any edited sun.
        if actor.get_actor_label() == 'ClearwaterSun' and abs(r.pitch - 31) < .01 and abs(r.yaw - 6) < .01:
            actor.set_actor_rotation(u.Rotator(pitch=-31, yaw=186, roll=0), False)
            changed = True
            lights_adjusted += 1
    if changed:
        save(world)
    return dict(seabeds_bound=seabeds, lights_adjusted=lights_adjusted)


def author():
    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Asset production requires PIE stopped; no game was stopped by this script')
    # Startup-loaded expressions can be rooted in a commandlet. UE 5.8's
    # DeleteAllMaterialExpressions then asserts inside MarkAsGarbage. Stop before
    # any package writes; the explicit resume entry uses the already saved graphs.
    if commandlet:
        existing = [n for n in ('M_ClearwaterWater_Native', 'M_ClearwaterSeabed_Native',
                               'M_ClearwaterUnderwater_Native') if EAL.does_asset_exist(DEST + '/' + n)]
        if existing:
            raise RuntimeError('Native masters already saved: ' + ', '.join(existing) +
                               '; finish installation with -ClearwaterBindingsOnly. '
                               'Rebuild existing graphs through a live editor asset batch.')
    targets = {DEST + '/' + n for n in (
        'M_ClearwaterWater_Native', 'M_ClearwaterSeabed_Native', 'M_ClearwaterUnderwater_Native',
        'T_ClearwaterCausticsAtlas', 'MI_ClearwaterWater', 'MI_ClearwaterSeabed', 'MI_ClearwaterUnderwater',
        'SM_ClearwaterPlane', 'L_ClearwaterWater')}
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict = sorted(targets & dirty)
    if conflict:
        raise RuntimeError('Preserve unsaved target assets: ' + ', '.join(conflict))
    EAL.make_directory(DEST)
    # Make a recoverable asset copy before reparenting the three stable runtime references.
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    disk_backup = DATA / ('BeforeNative_' + stamp)
    for path in sorted(targets):
        relative = Path(path.removeprefix('/Game/') + ('.umap' if path.endswith('/L_ClearwaterWater') else '.uasset'))
        source = ROOT / 'Content' / relative
        if source.exists():
            destination = disk_backup / 'Content' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    backup_dir = DEST + '/History/BeforeNative_' + stamp
    EAL.make_directory(backup_dir)
    for name in ('MI_ClearwaterWater', 'MI_ClearwaterSeabed', 'MI_ClearwaterUnderwater'):
        if EAL.does_asset_exist(DEST + '/' + name):
            backup = EAL.duplicate_asset(DEST + '/' + name, backup_dir + '/' + name)
            if not backup:
                raise RuntimeError('Cannot preserve ' + name)
            save(backup)
    atlas = import_atlas()
    water, bed, underwater = build_surface(), build_seabed(atlas), build_underwater()
    instances = {}
    for name, parent in [('MI_ClearwaterWater', water), ('MI_ClearwaterSeabed', bed),
                         ('MI_ClearwaterUnderwater', underwater)]:
        instances[name] = reparent(name, parent)
    bindings = bind_candidate_content(instances['MI_ClearwaterWater'], instances['MI_ClearwaterSeabed'])
    receipt = dict(revision='clearwater-native-20260926', saved=SAVED, backup=backup_dir,
                   disk_backup=str(disk_backup),
                   optics='UE SingleLayerWater', waves=48, shared_hits=8, shared_wakes=4,
                   caustic_frames=32, bindings=bindings, runtime_tested=False, native_build_required=True)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / ('assets-saved-' + stamp + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('CLEARWATER_NATIVE_SAVED ' + json.dumps(receipt))


def finish_saved_bindings():
    """Resume after graph packages were saved, without deleting loaded expressions."""
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        raise RuntimeError('Binding resume requires the closed-editor commandlet')
    for name in ('M_ClearwaterWater_Native', 'M_ClearwaterSeabed_Native', 'M_ClearwaterUnderwater_Native'):
        mat = u.load_asset(DEST + '/' + name)
        if not mat:
            raise RuntimeError('Missing saved native master: ' + name)
        compile_and_save(mat)
    water = u.load_asset(DEST + '/MI_ClearwaterWater')
    bed = u.load_asset(DEST + '/MI_ClearwaterSeabed')
    if not water or not bed:
        raise RuntimeError('Missing saved candidate material instances')
    bindings = bind_candidate_content(water, bed)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    receipt = dict(revision='clearwater-native-20260926', phase='saved-materials-and-map-bindings',
                   saved=SAVED, bindings=bindings, runtime_tested=False)
    (DATA / ('bindings-saved-' + stamp + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('CLEARWATER_BINDINGS_SAVED ' + json.dumps(receipt))


def main():
    if '-clearwaterbindingsonly' in u.SystemLibrary.get_command_line().lower():
        finish_saved_bindings()
    else:
        author()


if __name__ == '__main__':
    main()
