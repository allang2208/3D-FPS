"""Import and save the Azure Dragon V10.2 claw: the library Fab Dragon Claw rig, the V10.1 gesture
and its spirit material (Fab normal atlas + reference veins).

Reads, never modifies: the shared T_AzureDragonNormal (root install_ue.py) and the ClawV10 reference
textures T_AzureDragonClawVeins / T_AzureDragonClawSmoke (install_textures_ue.py). The V10.1 original claw
and CoherentV9 were retired to trash on 2026-10-07 (Docs/Publication/AzureDragon20261007).
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AzureDragon20261004/ClawFab'
TAG, REV = 'AzureDragonClawFabRevision', '10'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt = dict(complete=False, revision='10.14', saved_assets=[], runtime_tested=False, rendered=False,
               source_listing='https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a', source_author='CaptainHC')


def record():
    (ROOT / 'install-fab-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def dirty_now(path):
    return any(str(p.get_name()) == path.rsplit('.', 1)[0] for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())


# Packages that were already dirty before this batch touched anything are user state and are kept,
# unless this installer itself reimported the skeleton (marker below) and stopped before the anim.
ANIM_PATH = DEST + '/Animations/A_AzureDragonClawFabRakeV10'
SKELETON_MARKER = ROOT / 'install-fab-skeleton-dirtied.json'
ANIM_DIRTY_BEFORE = dirty_now(ANIM_PATH) and not SKELETON_MARKER.exists()


def owned(path, dirtied_by_batch=False):
    asset = u.load_asset(path) if E.does_asset_exist(path) else None
    dirty = dirty_now(path)
    # Reimporting the skeleton (new tip bone) dirties its own animation; that is this batch's change.
    if dirty and dirtied_by_batch and asset and E.get_metadata_tag(asset, TAG) == REV:
        dirty = False
    if dirty and (not asset or E.get_metadata_tag(asset, 'AzureDragonPending') != REV):
        raise RuntimeError('Preserve unsaved asset ' + path)
    if asset and E.get_metadata_tag(asset, TAG) != REV:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset


def pending(asset):
    E.set_metadata_tag(asset, TAG, REV)
    E.set_metadata_tag(asset, 'AzureDragonPending', REV)


def save(asset):
    pending(asset)
    E.set_metadata_tag(asset, 'AzureDragonPending', '')
    E.set_metadata_tag(asset, 'SourceAuthoring', 'AzureDragon20261004/ClawV10/author_fab_claw.py')
    E.set_metadata_tag(asset, 'SourceListing', receipt['source_listing'])
    if not E.save_loaded_asset(asset, False):
        E.set_metadata_tag(asset, 'AzureDragonPending', REV)
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


def imported(filename, folder, name, options, dirtied_by_batch=False):
    owned(DEST + '/' + folder + '/' + name, dirtied_by_batch)
    task = u.AssetImportTask()
    for key, value in dict(filename=str(filename), destination_path=DEST + '/' + folder, destination_name=name,
                           automated=True, replace_existing=True, save=False, options=options).items():
        task.set_editor_property(key, value)
    A.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + folder + '/' + name)
    if not asset:
        raise RuntimeError('Import failed ' + name)
    pending(asset)
    return asset


if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Stop the current PIE before importing/saving claw V10.2; editor preserved.')
record()
normal_tex = u.load_asset('/Game/Weapons/AzureDragon20261004/Textures/T_AzureDragonNormal')
veins_tex = u.load_asset('/Game/Weapons/AzureDragon20261004/ClawV10/Textures/T_AzureDragonClawVeins')
if not normal_tex or not veins_tex:
    raise RuntimeError('Shared Fab normal atlas or ClawV10 vein texture missing; run their installers first.')


def import_texture(name):
    """Authored tiling data texture from Export/ (linear, wrapped)."""
    path = DEST + '/Textures/' + name
    owned(path)
    task = u.AssetImportTask()
    for key, value in dict(filename=str(ROOT / 'Export' / (name + '.png')), destination_path=DEST + '/Textures',
                           destination_name=name, automated=True, replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    A.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Import failed ' + name)
    pending(tex)
    for key, value in dict(srgb=False, compression_settings=u.TextureCompressionSettings.TC_BC7,
                           lod_group=u.TextureGroup.TEXTUREGROUP_EFFECTS, never_stream=True,
                           address_x=u.TextureAddress.TA_WRAP, address_y=u.TextureAddress.TA_WRAP).items():
        tex.set_editor_property(key, value)
    save(tex)
    return tex


# V10.10 pebble-scale detail height (author_scale_detail.py).
detail_tex = import_texture('T_AzureDragonClawScaleDetail')

# ---- material --------------------------------------------------------------------------------
name = 'M_AzureDragonClawFabV10'
mat = owned(DEST + '/Materials/' + name) or A.create_asset(name, DEST + '/Materials', u.Material, u.MaterialFactoryNew())
pending(mat)
for expression in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, expression)
# Two-sided again (V10.6): with the two-sided follower depth only the nearest face survives, so thin
# or open parts fill instead of showing holes, and nothing behind it shows through.
for key, value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT, shading_model=u.MaterialShadingModel.MSM_UNLIT,
                       two_sided=True, disable_depth_test=True, used_with_skeletal_mesh=True,
                       translucency_pass=u.MaterialTranslucencyPass.MTP_AFTER_DOF).items():
    mat.set_editor_property(key, value)
count = [0]


def node(cls, **props):
    n = L.create_material_expression(mat, cls, -1600 + (count[0] % 6) * 250, (count[0] // 6) * 220)
    count[0] += 1
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(source, target, pin, output=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect ' + str(pin))


normal_sample = node(u.MaterialExpressionTextureSample, texture=normal_tex,
                     sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
normal_ws = node(u.MaterialExpressionTransform,
                 transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                 transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
wire(normal_sample, normal_ws, 0, 'RGB')
inputs = {'Normal': normal_ws,
          'CamVec': node(u.MaterialExpressionCameraVectorWS),
          'Attr': node(u.MaterialExpressionVertexColor),
          'RestXY': node(u.MaterialExpressionTextureCoordinate, coordinate_index=1),
          'RestZJoint': node(u.MaterialExpressionTextureCoordinate, coordinate_index=2),
          'RestN': node(u.MaterialExpressionTextureCoordinate, coordinate_index=3),
          'VeinTex': node(u.MaterialExpressionTextureObject, texture=veins_tex,
                          sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
          # Front-most surface test against the follower mesh's custom depth (stencil 214).
          'CustomDepth': node(u.MaterialExpressionSceneTexture, scene_texture_id=u.SceneTextureId.PPI_CUSTOM_DEPTH),
          'CustomStencil': node(u.MaterialExpressionSceneTexture, scene_texture_id=u.SceneTextureId.PPI_CUSTOM_STENCIL),
          'PixelDepth': node(u.MaterialExpressionPixelDepth),
          # V10.4 structure: smooth normal for cavity shading, view-relative key light from C++.
          'VNormal': node(u.MaterialExpressionVertexNormalWS),
          'KeyDir': node(u.MaterialExpressionVectorParameter, parameter_name='KeyDir',
                         default_value=u.LinearColor(0., 0., 1., 0.)),
          # V10.6: the sword / arms / near objects (opaque scene depth) stay in front of the claws.
          'SceneDepth': node(u.MaterialExpressionSceneTexture, scene_texture_id=u.SceneTextureId.PPI_SCENE_DEPTH)}
# ---- V10.10: pebble-scale detail, palm mask, anti-aliased front-surface taps -------------------
inputs['DetailTex'] = node(u.MaterialExpressionTextureObject, texture=detail_tex,
                           sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
world = node(u.MaterialExpressionWorldPosition)
try:  # camera-relative keeps the derivative bump precise far from the origin
    world.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE)
except Exception as error:
    print('AZURE_FAB_WORLDPOS absolute (' + str(error) + ')')
inputs['WorldPos'] = world
vertex_alpha = node(u.MaterialExpressionVertexColor)
alpha_names = [str(n) for n in L.get_material_expression_output_names(vertex_alpha)]
inputs['AttrA'] = (vertex_alpha, next((n for n in alpha_names if n.lower() in ('a', 'alpha')), alpha_names[-1]))
screen = node(u.MaterialExpressionScreenPosition)
view_size = node(u.MaterialExpressionViewSize)
for index, (ox, oy) in enumerate(((.6, .6), (-.6, .6), (.6, -.6), (-.6, -.6))):
    offset = node(u.MaterialExpressionDivide)
    wire(node(u.MaterialExpressionConstant2Vector, r=ox, g=oy), offset, 0)
    wire(view_size, offset, 1)
    uv = node(u.MaterialExpressionAdd)
    wire(screen, uv, 0)
    wire(offset, uv, 1)
    tap = node(u.MaterialExpressionSceneTexture, scene_texture_id=u.SceneTextureId.PPI_CUSTOM_DEPTH)
    wire(uv, tap, 0)
    inputs['CD%d' % (index + 1)] = tap
for key, value in [('Reveal', 1.), ('Age', 0.), ('Opacity', 1.), ('Impact', 0.), ('NearOcclusion', 350.),
                   ('DetailDepth', 2.5), ('Disintegrate', -1.)]:
    inputs[key] = node(u.MaterialExpressionScalarParameter, parameter_name=key, default_value=value)
# V10.14 expiry erosion front (camera-relative centre, axis pre-divided by the claw span; from C++).
for key in ('DisintegrateCenter', 'DisintegrateAxis'):
    inputs[key] = node(u.MaterialExpressionVectorParameter, parameter_name=key, default_value=u.LinearColor(0., 0., 0., 0.))
custom = node(u.MaterialExpressionCustom, code=(ROOT / 'AzureDragonClawFabV10.hlsl').read_text(encoding='utf-8'),
              output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, description=name)
pins = []
for key in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', key)
    pins.append(pin)
custom.set_editor_property('inputs', pins)
for key, expr in inputs.items():
    if isinstance(expr, tuple):
        wire(expr[0], custom, key, expr[1])
    else:
        wire(expr, custom, key)
rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
wire(custom, rgb, 0)
alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(custom, alpha, 0)
exposure = node(u.MaterialExpressionEyeAdaptationInverse)
wire(rgb, exposure, 0)
wire(node(u.MaterialExpressionConstant, r=1.), exposure, 1)
L.connect_material_property(exposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
L.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
errors = L.recompile_material(mat)
if errors:
    raise RuntimeError(name + ' compilation failed ' + str(errors))
save(mat)

# ---- talon flames (additive cards built in C++) ------------------------------------------------
smoke_tex = u.load_asset('/Game/Weapons/AzureDragon20261004/ClawV10/Textures/T_AzureDragonClawSmoke')
# V10.8 arm fire: real flame sequences from the owned Realistic Starter VFX Pack Vol2 (read only).
fire_mass = u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Fire_F')     # 6x6 rolling mass, RGB
fire_tongue = u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Fire_D')   # 8x4 rising tongues, RGBA
if not smoke_tex or not fire_mass or not fire_tongue:
    raise RuntimeError('ClawV10 smoke texture or Realistic Vol2 fire textures missing.')
COLOR = u.MaterialSamplerType.SAMPLERTYPE_COLOR            # sRGB pack textures
LINEAR = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR    # authored data textures


def build_overlay(asset_name, hlsl, textures, scalars=()):
    """Alpha-blended overlay cards (arm fire, rift scars; HLSL returns emissive + opacity): UV, textures
    {pin: (texture, sampler)}, Age/Fade/NearOcclusion (+ extra scalars), near-occluder depth test.
    V10.9: translucent instead of additive, which vanished against bright sky and floors."""
    out = owned(DEST + '/Materials/' + asset_name) or A.create_asset(asset_name, DEST + '/Materials', u.Material,
                                                                     u.MaterialFactoryNew())
    pending(out)
    for expression in list(L.get_material_expressions(out)):
        L.delete_material_expression(out, expression)
    for key, value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT, shading_model=u.MaterialShadingModel.MSM_UNLIT,
                           two_sided=True, disable_depth_test=True,
                           translucency_pass=u.MaterialTranslucencyPass.MTP_AFTER_DOF).items():
        out.set_editor_property(key, value)
    n_count = [0]

    def fnode(cls, **props):
        n = L.create_material_expression(out, cls, -1200 + (n_count[0] % 4) * 260, (n_count[0] // 4) * 220)
        n_count[0] += 1
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    finputs = {'UV': fnode(u.MaterialExpressionTextureCoordinate, coordinate_index=0),
               'SceneDepth': fnode(u.MaterialExpressionSceneTexture, scene_texture_id=u.SceneTextureId.PPI_SCENE_DEPTH),
               'PixelDepth': fnode(u.MaterialExpressionPixelDepth)}
    for pin_name, (texture, sampler) in textures.items():
        finputs[pin_name] = fnode(u.MaterialExpressionTextureObject, texture=texture, sampler_type=sampler)
    for key, value in [('Age', 0.), ('Fade', 1.), ('NearOcclusion', 350.)] + list(scalars):
        finputs[key] = fnode(u.MaterialExpressionScalarParameter, parameter_name=key, default_value=value)
    fcustom = fnode(u.MaterialExpressionCustom, code=(ROOT / hlsl).read_text(encoding='utf-8'),
                    output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, description=asset_name)
    fpins = []
    for key in finputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        fpins.append(pin)
    fcustom.set_editor_property('inputs', fpins)
    for key, expr in finputs.items():
        if not L.connect_material_expressions(expr, '', fcustom, key):
            raise RuntimeError('Cannot connect ' + asset_name + ' input ' + key)
    frgb = fnode(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    falpha = fnode(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    fexposure = fnode(u.MaterialExpressionEyeAdaptationInverse)
    wire(fcustom, frgb, 0)
    wire(fcustom, falpha, 0)
    wire(frgb, fexposure, 0)
    wire(fnode(u.MaterialExpressionConstant, r=1.), fexposure, 1)
    L.connect_material_property(fexposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(falpha, '', u.MaterialProperty.MP_OPACITY)
    errors = L.recompile_material(out)
    if errors:
        raise RuntimeError(asset_name + ' compilation failed ' + str(errors))
    save(out)


# One big arm-end flame (V10.8) and the five talon rift scars after Rift Slash V4.
build_overlay('M_AzureDragonClawFlameV10', 'AzureDragonClawFlameV10.hlsl',
              {'FireMass': (fire_mass, COLOR), 'FireTongue': (fire_tongue, COLOR)})
build_overlay('M_AzureDragonClawRiftV10', 'AzureDragonClawRiftV10.hlsl', {}, scalars=[('Dissolve', 0.)])
# V10.14 expiry motes: soft glowing grains on C++ camera-facing quads.
build_overlay('M_AzureDragonClawDustV10', 'AzureDragonClawDustV10.hlsl', {})

# ---- two-sided opaque depth for the unseen follower (custom depth only) -----------------------------
depth_name = 'M_AzureDragonClawDepthV10'
depth = owned(DEST + '/Materials/' + depth_name) or A.create_asset(depth_name, DEST + '/Materials', u.Material,
                                                                   u.MaterialFactoryNew())
pending(depth)
for expression in list(L.get_material_expressions(depth)):
    L.delete_material_expression(depth, expression)
for key, value in dict(blend_mode=u.BlendMode.BLEND_OPAQUE, shading_model=u.MaterialShadingModel.MSM_UNLIT,
                       two_sided=True, used_with_skeletal_mesh=True).items():
    depth.set_editor_property(key, value)
L.connect_material_property(L.create_material_expression(depth, u.MaterialExpressionConstant, -300, 0), '',
                            u.MaterialProperty.MP_EMISSIVE_COLOR)
errors = L.recompile_material(depth)
if errors:
    raise RuntimeError(depth_name + ' compilation failed ' + str(errors))
save(depth)

# ---- skeletal mesh + animation ----------------------------------------------------------------
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    rig = json.loads((ROOT / 'ExportFab' / 'rig.json').read_text(encoding='utf-8'))
    owned(DEST + '/Meshes/SK_AzureDragonClawFabV10_Skeleton')
    options = u.FbxImportUI()
    for key, value in dict(import_mesh=True, import_as_skeletal=True, import_animations=False,
                           mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH,
                           automated_import_should_detect_type=False, create_physics_asset=False,
                           import_materials=False, import_textures=False).items():
        options.set_editor_property(key, value)
    data = options.get_editor_property('skeletal_mesh_import_data')
    for key, value in dict(convert_scene=True, convert_scene_unit=False, import_uniform_scale=1.,
                           normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                           vertex_color_import_option=u.VertexColorImportOption.REPLACE,
                           use_t0_as_ref_pose=False, update_skeleton_reference_pose=False).items():
        data.set_editor_property(key, value)
    mesh = imported(rig['mesh'], 'Meshes', 'SK_AzureDragonClawFabV10', options)
    slots = mesh.get_editor_property('materials')
    for slot in slots:
        slot.material_interface = mat
    mesh.set_editor_property('materials', slots)
    skeleton = mesh.get_editor_property('skeleton')
    save(mesh)
    save(skeleton)
    SKELETON_MARKER.write_text(json.dumps(dict(reason='skeleton reimported; dependent animation dirtied by this installer',
                                               animation=ANIM_PATH)), encoding='utf-8')
    options = u.FbxImportUI()
    for key, value in dict(import_mesh=False, import_as_skeletal=True, import_animations=True,
                           mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION,
                           original_import_type=u.FBXImportType.FBXIT_ANIMATION,
                           automated_import_should_detect_type=False, skeleton=skeleton,
                           import_materials=False, import_textures=False).items():
        options.set_editor_property(key, value)
    data = options.get_editor_property('anim_sequence_import_data')
    for key, value in dict(convert_scene=True, convert_scene_unit=False,
                           animation_length=u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
                           import_bone_tracks=True, remove_redundant_keys=False,
                           use_default_sample_rate=False, custom_sample_rate=60).items():
        data.set_editor_property(key, value)
    animation = imported(rig['animation'], 'Animations', 'A_AzureDragonClawFabRakeV10', options,
                         dirtied_by_batch=not ANIM_DIRTY_BEFORE)
    animation.set_editor_property('enable_root_motion', False)
    save(animation)
    SKELETON_MARKER.unlink(missing_ok=True)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))
receipt['complete'] = True
record()
print('AZURE_DRAGON_CLAW_FAB_V10_SAVED assets=' + str(len(receipt['saved_assets'])) + ' runtime_tested=false rendered=false')
