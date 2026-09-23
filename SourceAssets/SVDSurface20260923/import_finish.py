"""Install the SVD surface bake through the existing seven runtime instances.

Run in the project's serialized bridge, or in a background commandlet while the
project editor is closed. Does not import meshes, run PIE, or render previews.
"""
import json
import shutil
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
CASE = ROOT / 'SourceAssets/SVDSurface20260923'
BASE = '/Game/Weapons/SVDDragunov20260922'
DEST = BASE + '/Surface20260923'
PARTS = {
    'Body': 'svd', 'Magazine': 'svd', 'Trigger': 'svd',
    'ChargingHandle': 'svd', 'SafetyLever': 'svd',
    'ScopeBody': 'pso', 'ScopeMount': 'pso',
}
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
manifest = json.loads((CASE / 'textures.json').read_text(encoding='utf-8'))
receipt_path = CASE / 'import_receipt.json'
receipt = {'status': 'importing', 'textures': {}, 'materials': {}, 'instances': {},
           'tests_run': False, 'renders_run': False}

if Path(u.Paths.project_dir()).resolve() != ROOT.resolve():
    raise RuntimeError('Wrong project; no assets changed')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the running play session')
targets = {BASE + '/Materials/MI_SVD_' + part for part in PARTS}
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = [p for p in dirty if p in targets or p.startswith(DEST + '/')]
if conflicts:
    raise RuntimeError('Unsaved target packages: ' + ', '.join(conflicts))


def record():
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())


def connect(source, output, target, input_name):
    if not L.connect_material_expressions(source, output, target, input_name):
        raise RuntimeError('Cannot connect material input: ' + input_name)


def output(node, channel, prop):
    if not L.connect_material_property(node, channel, prop):
        raise RuntimeError('Cannot connect material output: ' + str(prop))


instances = {}
before = CASE / 'Before/Materials'
before.mkdir(parents=True, exist_ok=True)
for part in PARTS:
    name = 'MI_SVD_' + part
    path = BASE + '/Materials/' + name
    mic = u.load_asset(path)
    if not isinstance(mic, u.MaterialInstanceConstant):
        raise RuntimeError('Missing runtime material instance: ' + path)
    source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = before / source.name
    if not backup.exists():
        shutil.copy2(source, backup)
    instances[part] = mic
    parent = mic.get_editor_property('parent')
    receipt['instances'][part] = {'asset': mic.get_path_name(),
                                 'parent_before': parent.get_path_name() if parent else None,
                                 'backup': str(backup)}
record()

textures = {}
materials = {}
for atlas, info in manifest.items():
    textures[atlas] = {}
    for kind, filename in info['textures'].items():
        name = Path(filename).stem
        task = u.AssetImportTask()
        task.filename = filename
        task.destination_path = DEST + '/Textures'
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        A.import_asset_tasks([task])
        tex = u.load_asset(DEST + '/Textures/' + name)
        if not isinstance(tex, u.Texture2D):
            raise RuntimeError('Texture import failed: ' + name)
        tex.set_editor_property('srgb', kind == 'BaseColor')
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('lod_bias', 0)
        tex.set_editor_property('max_texture_size', 4096)
        save(tex)
        textures[atlas][kind] = tex
        receipt['textures'][name] = {'asset': tex.get_path_name(), 'saved': True,
                                     'srgb': tex.get_editor_property('srgb'),
                                     'compression': str(tex.get_editor_property('compression_settings'))}
        record()

    normal = u.load_asset(BASE + '/Textures/T_SVD_' + atlas + '_normal')
    if not isinstance(normal, u.Texture2D):
        raise RuntimeError('Missing original structural normal: ' + atlas)
    textures[atlas]['Normal'] = normal
    name = 'M_SVD_Surface_' + atlas
    path = DEST + '/Materials/' + name
    mat = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(
        name, DEST + '/Materials', u.Material, u.MaterialFactoryNew())
    if not isinstance(mat, u.Material):
        raise RuntimeError('Material creation failed: ' + name)
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided', False)
    L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    samples = {}
    for i, (kind, parameter, sampler) in enumerate([
        ('BaseColor', 'Tex_basecolor', u.MaterialSamplerType.SAMPLERTYPE_COLOR),
        ('ORM', 'Tex_orm', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
        ('Normal', 'Tex_normal', u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
    ]):
        node = L.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D, -700, i * 270)
        node.set_editor_property('parameter_name', parameter)
        node.set_editor_property('texture', textures[atlas][kind])
        node.set_editor_property('sampler_type', sampler)
        samples[kind] = node
    tint = L.create_material_expression(mat, u.MaterialExpressionVectorParameter, -700, -200)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', u.LinearColor(1, 1, 1, 1))
    color = L.create_material_expression(mat, u.MaterialExpressionMultiply, -350, 0)
    connect(samples['BaseColor'], 'RGB', color, 'A')
    connect(tint, '', color, 'B')
    output(color, '', u.MaterialProperty.MP_BASE_COLOR)
    scale = L.create_material_expression(mat, u.MaterialExpressionScalarParameter, -700, 840)
    scale.set_editor_property('parameter_name', 'RoughnessScale')
    scale.set_editor_property('default_value', 1.0)
    rough = L.create_material_expression(mat, u.MaterialExpressionMultiply, -350, 270)
    connect(samples['ORM'], 'G', rough, 'A')
    connect(scale, '', rough, 'B')
    output(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    output(samples['ORM'], 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(samples['ORM'], 'B', u.MaterialProperty.MP_METALLIC)
    output(samples['Normal'], 'RGB', u.MaterialProperty.MP_NORMAL)
    L.recompile_material(mat)
    save(mat)
    materials[atlas] = mat
    receipt['materials'][atlas] = {'asset': mat.get_path_name(), 'saved': True,
                                    'normal': normal.get_path_name(),
                                    'normal_flip_green': normal.get_editor_property('flip_green_channel'),
                                    'normal_strength': 1.0, 'ao_multiplies_basecolor': False}
    record()
    u.log('SVD_SURFACE_MATERIAL_SAVED ' + atlas)

for part, atlas in PARTS.items():
    mic = instances[part]
    L.set_material_instance_parent(mic, materials[atlas])
    # Explicit overrides replace any old texture overrides on the stable MI path.
    # UE 5.8 setters may return false after a successful write; record actual values.
    for parameter, kind in [('Tex_basecolor', 'BaseColor'), ('Tex_orm', 'ORM'), ('Tex_normal', 'Normal')]:
        L.set_material_instance_texture_parameter_value(mic, parameter, textures[atlas][kind])
    L.set_material_instance_vector_parameter_value(mic, 'Tint', u.LinearColor(1, 1, 1, 1))
    L.set_material_instance_scalar_parameter_value(mic, 'RoughnessScale', 1.0)
    L.update_material_instance(mic)
    save(mic)
    entry = receipt['instances'][part]
    entry['parent_after'] = mic.get_editor_property('parent').get_path_name()
    entry['textures'] = {
        parameter: L.get_material_instance_texture_parameter_value(mic, parameter).get_path_name()
        for parameter in ['Tex_basecolor', 'Tex_orm', 'Tex_normal']
    }
    entry['saved'] = True
    record()

# Record current bindings as part of the integration receipt. No mesh is changed.
mesh = u.load_asset(BASE + '/Complete20260923/SK_SVD_Manny')
receipt['runtime_mesh'] = mesh.get_path_name()
receipt['runtime_slots'] = {str(s.material_slot_name): s.material_interface.get_path_name()
                            for s in mesh.get_editor_property('materials')}
receipt['status'] = 'Four textures, two masters and seven existing instances saved; no runtime or visual test'
record()
u.log('SVD_SURFACE_IMPORT_COMPLETE')
