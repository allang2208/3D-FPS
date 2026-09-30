"""Read-only export of reference-gun textures and meshes for offline measurement.

Exports (no asset is modified or saved):
  inspect/export/tex/<TextureName>.png   authored source pixels of every texture the
                                         runtime materials of M4/AKM/HK416/A762 sample
  inspect/export/mesh/<Key>.fbx          the runtime skeletal meshes (UV0 + slots)
  inspect/export/manifest.json           texture metadata and slot -> texture mapping
"""
import json
import unreal as u
from pathlib import Path

O = Path(__file__).parent
EXP = O / 'inspect' / 'export'
(EXP / 'tex').mkdir(parents=True, exist_ok=True)
(EXP / 'mesh').mkdir(parents=True, exist_ok=True)
L = u.MaterialEditingLibrary
MESHES = {
    'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    'AKM': '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
    'HK416': '/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny',
    'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
    'A762_RearSight': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_RearSight',
    'A762_FrontSight': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_FrontSight',
}
SKIP = ('BarePalmV7', '/Engine/', 'DefaultTexture', 'BaseFlattenLinearColor')


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def material_textures(mi):
    """Texture objects actually referenced by the material graph or instance overrides."""
    found = {}
    base = mi.get_base_material()
    for expr in L.get_material_expressions(base):
        tex = prop(expr, 'texture')
        if tex:
            found[tex.get_path_name()] = (tex, str(prop(expr, 'parameter_name') or expr.get_name()))
    if isinstance(mi, u.MaterialInstance):
        for name in L.get_texture_parameter_names(base):
            tex = L.get_material_instance_texture_parameter_value(mi, name)
            if tex:
                found[tex.get_path_name()] = (tex, str(name))
    return {k: v for k, v in found.items() if not any(s in k for s in SKIP)}


def export_texture(tex, name):
    for exporter, ext in [(u.TextureExporterPNG(), '.png'), (u.TextureExporterTGA(), '.tga')]:
        target = EXP / 'tex' / (name + ext)
        if target.exists():
            return target.name
        task = u.AssetExportTask()
        task.object = tex
        task.filename = str(target)
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = exporter
        if u.Exporter.run_asset_export_task(task) and target.exists():
            return target.name
    return None


manifest = {'meshes': {}, 'textures': {}, 'modified': False}
for key, path in MESHES.items():
    mesh = u.load_asset(path)
    if not mesh:
        continue
    slots = []
    for s in mesh.get_editor_property('materials' if isinstance(mesh, u.SkeletalMesh) else 'static_materials'):
        mi = s.material_interface
        entry = {'slot': str(s.material_slot_name), 'material': mi.get_path_name() if mi else None, 'textures': {}}
        if mi and not any(x in mi.get_path_name() for x in SKIP):
            for tpath, (tex, role) in material_textures(mi).items():
                name = tex.get_name()
                entry['textures'][role] = name
                if name not in manifest['textures']:
                    data = prop(tex, 'asset_import_data')
                    try:
                        source = data.get_first_filename() if data else ''
                    except Exception:
                        source = ''
                    manifest['textures'][name] = {
                        'path': tpath, 'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
                        'srgb': bool(prop(tex, 'srgb', False)),
                        'compression': str(prop(tex, 'compression_settings')),
                        'flip_green': bool(prop(tex, 'flip_green_channel', False)),
                        'source_file': source,
                        'export': export_texture(tex, name),
                    }
        slots.append(entry)
    manifest['meshes'][key] = {'path': mesh.get_path_name(), 'fbx': None, 'slots': slots}
(EXP / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')

# Skeletal FBX export needs render resources (run this script with -WithRHI).
for key, path in MESHES.items():
    mesh = u.load_asset(path)
    fbx = EXP / 'mesh' / (key + '.fbx')
    if mesh and not fbx.exists():
        task = u.AssetExportTask()
        task.object = mesh
        task.filename = str(fbx)
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = u.SkeletalMeshExporterFBX() if isinstance(mesh, u.SkeletalMesh) else u.StaticMeshExporterFBX()
        options = u.FbxExportOption()
        options.set_editor_property('level_of_detail', False)
        options.set_editor_property('collision', False)
        options.set_editor_property('bake_material_inputs', u.FbxMaterialBakeMode.DISABLED)
        task.options = options
        u.Exporter.run_asset_export_task(task)
    if key in manifest['meshes']:
        manifest['meshes'][key]['fbx'] = fbx.name if fbx.exists() else None

def function_graph(path):
    """Expressions and input edges of a material function (the M4 Phong conversion)."""
    fn = u.load_asset(path)
    if not fn:
        return None
    anchor = u.load_asset('/Game/Weapons/M4InfimaV3/Body_001').get_base_material()
    nodes = []
    for expr in L.get_material_function_expressions(fn):
        item = {'name': expr.get_name(), 'class': expr.get_class().get_name()}
        for key in ['input_name', 'output_name', 'const_a', 'const_b', 'const_exponent', 'min_default', 'max_default',
                    'parameter_name', 'default_value', 'sort_priority', 'preview_value']:
            value = prop(expr, key)
            if value is not None and not isinstance(value, (int, float, str, bool)):
                value = str(value)
            if value not in (None, '', 'None'):
                item[key] = value
        try:
            item['inputs'] = [[i, s.get_name()] for i, s in enumerate(L.get_inputs_for_material_expression(anchor, expr)) if s]
        except Exception as exc:
            item['inputs_error'] = str(exc)[:120]
        nodes.append(item)
    return nodes


manifest['phong_to_metal_roughness'] = function_graph('/InterchangeAssets/Functions/MF_PhongToMetalRoughness')
(EXP / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
print('WEAPON_SURFACE_EXPORT', json.dumps({'textures': len(manifest['textures']),
      'exported': sum(1 for t in manifest['textures'].values() if t['export']),
      'meshes': {k: v['fbx'] for k, v in manifest['meshes'].items()}}), flush=True)
