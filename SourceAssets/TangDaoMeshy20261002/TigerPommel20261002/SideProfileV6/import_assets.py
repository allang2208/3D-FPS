"""Save the V6 geometry and actual-model menu card, then install this revision."""
import json
import shutil
import unreal as u
from pathlib import Path

P = Path(__file__).resolve().parent
BASE = P.parent
ROOT = P.parents[3]
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Wrong project for tiger V6 import')
commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
editor = None if commandlet else u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():
    raise RuntimeError('Preserved current PIE session; import V6 outside PIE')

m = json.loads((P / 'pommel_manifest.json').read_text(encoding='utf-8'))
A = u.AssetToolsHelpers.get_asset_tools()
receipt_path = P / 'import_receipt.json'
previous = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
owned = set(previous.get('assets', []))
receipt = {'revision': m['revision'], 'assets': [], 'complete': False,
           'runtime_tested': False, 'visual_acceptance': False,
           'materials': m['materials'], 'material_families_reused': 5}

def record():
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Failed to save ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    owned.add(asset.get_path_name())
    record()
    return asset

def import_one(source, target, options=None, existing_icon=False):
    old = u.load_asset(target)
    if old:
        if not existing_icon and old.get_path_name() not in owned:
            raise RuntimeError('Preserved existing unowned V6 asset ' + target)
        dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if old.get_outermost().get_name() in dirty:
            raise RuntimeError('Preserved unsaved edits to ' + target)
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path, task.destination_name = target.rsplit('/', 1)
    task.automated = True
    task.replace_existing = bool(old)
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    asset = u.load_asset(target)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('Import did not create ' + target)
    return asset

record()
# The side mane has new geometry-matched PBR; all other families reuse their
# existing packages. Save the temporal counterpart with the same new textures.
E = u.MaterialEditingLibrary
D = m['ue_root']
old_m = json.loads((BASE / 'pommel_manifest.json').read_text(encoding='utf-8'))
temporal_mapping = {}
for family in ('BronzeFace','ChasedBody'):
    textures = {}
    for key in ('BaseColor', 'ORM', 'Normal'):
        name = 'T_TangDao_TigerPommel_' + family + '_ProfileV6_' + key
        tex = import_one(P / 'Textures' / ('TangDao_TigerPommel_' + family + '_' + key + '.png'), D + '/Textures/' + name)
        tex.set_editor_property('srgb', key == 'BaseColor')
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal'
                                else u.TextureCompressionSettings.TC_MASKS if key == 'ORM' else u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('never_stream', False)
        if key == 'Normal':
            tex.set_editor_property('flip_green_channel', True)
        textures[key] = save(tex)
    slot='M_TangDaoTigerPommel_'+family
    donor_path = old_m['materials'][slot].split('.')[0]
    new_material_path = m['materials'][slot].split('.')[0]
    for suffix in ('', '_Whirlwind'):
        target = new_material_path + suffix
        mat = u.load_asset(target)
        if mat and mat.get_path_name() not in owned:
            raise RuntimeError('Preserved unowned V6 material ' + target)
        if mat is None:
            donor = u.load_asset(donor_path + suffix)
            folder, name = target.rsplit('/', 1)
            mat = A.duplicate_asset(name, folder, donor)
        if mat is None:
            raise RuntimeError('Could not create profile material ' + target)
        for expr in E.get_material_expressions(mat):
            if isinstance(expr, u.MaterialExpressionTextureSample):
                old_texture = expr.get_editor_property('texture')
                for key, texture in textures.items():
                    if old_texture and old_texture.get_name().endswith('_' + key):
                        expr.set_editor_property('texture', texture)
        mat.set_editor_property('used_with_skeletal_mesh', False)
        errors = list(E.recompile_material(mat) or [])
        if errors:
            raise RuntimeError('Profile material build failed: ' + str(errors))
        save(mat)
        if suffix:
            temporal_mapping[m['materials'][slot]] = mat.get_path_name()

materials = {name: u.load_asset(path) for name, path in m['materials'].items()}
if any(mat is None for mat in materials.values()):
    raise RuntimeError('V6 requires all seven declared material slots')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.import_animations = False
options.lod_number = 3
options.auto_compute_lod_distances = True
data = options.static_mesh_import_data
data.combine_meshes = False
data.import_mesh_lods = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.build_nanite = False  # preserve this first-person attachment's existing LOD route
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh = import_one(P / 'Export' / (m['mesh_name'] + '.fbx'), m['mesh'].split('.')[0], options)
for i, slot in enumerate(mesh.static_materials):
    mesh.set_material(i, materials[str(slot.material_slot_name)])
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = False
nanite.explicit_tangents = True
nanite.fallback_relative_error = 0.
mesh.set_editor_property('nanite_settings', nanite)
save(mesh)

icon_name = 'ue_tang_dao_pommel_tiger_mountain'
icon_dir = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913'
for suffix in ('.png', '.uasset'):
    src = icon_dir / (icon_name + suffix)
    backup = P / 'Before' / src.name
    if src.exists() and not backup.exists():
        shutil.copy2(src, backup)
icon = import_one(P / 'Icons' / (icon_name + '.png'),
                  '/Game/ColdSteelData/AttachmentIcons20260913/' + icon_name, existing_icon=True)
icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('never_stream', True)
icon.set_editor_property('srgb', True)
save(icon)
shutil.copy2(P / 'Icons' / (icon_name + '.png'), icon_dir / (icon_name + '.png'))

# Merge the currently loaded files only after both new assets have been saved.
# Preserve all stats, effects, other options, and the shared material bindings.
def install_json(path, merge):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    backup = P / 'Before' / path.name
    if not backup.exists():
        shutil.copy2(path, backup)
    merge(value)
    temp = path.with_suffix(path.suffix + '.tiger-v6.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def module(value):
    row = value['slots']['pommel']['tiger_mountain']
    row['mesh'] = m['mesh']
    row['appearance'] = m['appearance']
    row['materials'] = m['materials'].copy()
    value['tiger_pommel_revision'] = m['revision']

def description(value):
    column = next(c for c in value['columns'] if c['key'] == 'pommel')
    row = next(o for o in column['options'] if o['id'] == 'tiger_mountain')
    row['description'] = '唐刀专属柄尾。' + m['appearance']

install_json(ROOT / 'Content/ColdSteelData/tang-dao-modules.json', module)
install_json(ROOT / 'Content/ColdSteelData/melee-gunsmith.json', description)
install_json(ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json', lambda value: value.update(temporal_mapping))
install_json(BASE.parent / 'SurfaceV2/bindings.json', lambda value: value['slots']['pommel'].update({'tiger_mountain': m['materials'].copy()}))
receipt.update(complete=True, mesh=mesh.get_path_name(), icon=icon.get_path_name(),
               catalogs=['Content/ColdSteelData/tang-dao-modules.json', 'Content/ColdSteelData/melee-gunsmith.json',
                         'Content/ColdSteelData/whirlwind-temporal-materials.json', 'SourceAssets/TangDaoMeshy20261002/SurfaceV2/bindings.json'],
               new_side_material=m['materials']['M_TangDaoTigerPommel_ChasedBody'],
               existing_interface_and_stats_preserved=True)
record()
(BASE / 'active_revision.json').write_text(json.dumps({'source_revision': 'SideProfileV6',
    'manifest': 'SideProfileV6/pommel_manifest.json', 'receipt': 'SideProfileV6/import_receipt.json'},
    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('TIGER_V6_SAVED_AND_INSTALLED ' + mesh.get_path_name(), flush=True)
