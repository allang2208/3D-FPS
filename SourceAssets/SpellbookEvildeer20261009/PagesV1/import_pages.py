"""Import and save the new page mesh, materials and animations in a sibling folder."""
import json
from pathlib import Path
import unreal as u

HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/SpellbookEvildeer20261009/PagesV1')
DEST = '/Game/Weapons/SpellbookEvildeer20261009/PagesV1'
ORIGINAL = '/Game/Weapons/SpellbookEvildeer20261009'
manifest = json.loads((HERE/'manifest.json').read_text())
A, E, L = u.AssetToolsHelpers.get_asset_tools(), u.EditorAssetLibrary, u.MaterialEditingLibrary
receipt = {'complete': False, 'saved_assets': [], 'illustrated_faces': 16, 'moving_leaves': 7, 'runtime_tested': False}

def record():
    (HERE/'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')

def save(asset):
    if not E.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Unable to save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()

def imp(file, name, destination, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+name)
    if not asset:
        raise RuntimeError('Import failed: '+name)
    return asset

record()
materials = {name: u.load_asset(ORIGINAL+'/Materials/'+name) for name in ('M_BookCover', 'M_BookPages')}
for group in manifest['paper_groups']:
    name = 'T_SpellbookPages_'+group
    tex = imp(HERE/'Textures'/(name+'.png'), name, DEST+'/Textures')
    tex.set_editor_property('srgb', True)
    # Let the import pipeline build mip levels while preserving normalized page UVs.
    tex.set_editor_property('power_of_two_mode', u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
    tex.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
    tex.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    save(tex)
    name = 'M_SpellbookPages_'+group
    mat = u.load_asset(DEST+'/Materials/'+name) if E.does_asset_exist(DEST+'/Materials/'+name) else A.create_asset(name, DEST+'/Materials', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_skeletal_mesh', True)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided', False)
    sample = L.create_material_expression(mat, u.MaterialExpressionTextureSample)
    sample.texture = tex
    sample.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    L.connect_material_property(sample, 'RGB', u.MaterialProperty.MP_BASE_COLOR)
    roughness = L.create_material_expression(mat, u.MaterialExpressionConstant)
    roughness.set_editor_property('r', .88)
    L.connect_material_property(roughness, '', u.MaterialProperty.MP_ROUGHNESS)
    metallic = L.create_material_expression(mat, u.MaterialExpressionConstant)
    metallic.set_editor_property('r', 0.)
    L.connect_material_property(metallic, '', u.MaterialProperty.MP_METALLIC)
    L.recompile_material(mat)
    E.set_metadata_tag(mat, 'PageArtwork', 'Generated with built-in image_gen, 2026-10-12')
    save(mat)
    materials[name] = mat

flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = False
    data.import_uniform_scale = 1.
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = imp(HERE/'Export'/(manifest['mesh']+'.fbx'), manifest['mesh'], DEST+'/Meshes', options)
    slots = list(mesh.get_editor_property('materials'))
    for slot in slots:
        name = str(slot.material_slot_name)
        if name not in materials or not materials[name]:
            raise RuntimeError('Missing page material: '+name)
        slot.set_editor_property('material_interface', materials[name])
    mesh.set_editor_property('materials', slots)
    save(mesh)
    skeleton = mesh.get_editor_property('skeleton')
    save(skeleton)
    receipt['mesh'] = mesh.get_path_name()
    receipt['skeleton'] = skeleton.get_path_name()
    for spec in manifest['animations']:
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.import_mesh = False
        opt.import_animations = True
        opt.import_materials = False
        opt.import_textures = False
        opt.create_physics_asset = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.skeleton = skeleton
        data = opt.anim_sequence_import_data
        data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('use_default_sample_rate', False)
        data.set_editor_property('custom_sample_rate', 60)
        anim = imp(HERE/'Export'/(spec['name']+'.fbx'), spec['name'], DEST+'/Animations', opt)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(anim):
            raise RuntimeError('Animation compilation did not complete: '+spec['name'])
        save(anim)
    receipt['complete'] = True
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))
    record()
print('SPELLBOOK_16PAGES_SAVED '+json.dumps(receipt))
