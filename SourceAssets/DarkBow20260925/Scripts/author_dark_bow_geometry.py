"""Import the Fab dark bow at real scale, measure it, and read the Sparrow reference cadence.

Corrected against this engine build's recorded API surface (`Saved/bow_api_surface.json`):
in UE 5.8 `import_uniform_scale` / `auto_generate_collision` / `build_nanite` live on
`FbxStaticMeshImportData`, not on `FbxImportUI`; `USkeleton` exposes no bone-name methods to
Python, so this pass records clip lengths, skeletons and material slots only.

Every section is guarded: a failed probe must never lose an import that already succeeded, and
the whole receipt is written either way. No PIE, no playback, no screenshots.
"""

import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
CASE = ROOT / 'SourceAssets' / 'DarkBow20260925'
FBX = CASE / 'Source' / 'dark_bow.fbx'
DEST = '/Game/Weapons/DarkBow20260925'
MESH = DEST + '/SK_DarkBow'
SPARROW = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
# 参考口径：待机与拉弓是用户点名要参考的两个动作，发射节奏取三个技能射击做上下界。
CLIPS = {
    'idle': SPARROW + '/Animations/idle',
    'idle_relaxed': SPARROW + '/Animations/idle_relaxed',
    'travel_idle_bow_down': SPARROW + '/Animations/Travel_Mode_Idle_BowDown',
    'draw_back': SPARROW + '/Animations/RMB_Drawback',
    'aim_strafe_idle': SPARROW + '/Animations/Ability_StarShower',
    'fire_slow': SPARROW + '/Animations/R_Ability_Slow_Fire',
    'fire_medium': SPARROW + '/Animations/R_Ability_Med_Fire',
    'fire_fast': SPARROW + '/Animations/R_Ability_Fast_Fire',
}

report = {'runtime_tested': False, 'rendered': False, 'sections': {}}


def section(name, function):
    try:
        report['sections'][name] = function()
    except Exception as error:
        report['sections'][name] = {'error': str(error)[:400],
                                    'trace': traceback.format_exc(limit=4)}
    u.log('DARKBOW_SECTION ' + name + ' -> '
          + json.dumps(report['sections'][name], ensure_ascii=False)[:1500])


def do_import():
    if not FBX.exists():
        return {'error': 'missing ' + str(FBX)}
    u.EditorAssetLibrary.make_directory(DEST)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_materials = True          # 三个略有差异的黑色材质按原样进来
    options.import_textures = False
    options.import_animations = False
    data = options.static_mesh_import_data
    data.import_uniform_scale = 100.0        # Blender 米 -> UE 厘米
    data.auto_generate_collision = True
    data.build_nanite = False
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = DEST
    task.destination_name = 'SK_DarkBow'
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    out = {'errors': [str(e) for e in list(task.errors or [])]}
    mesh = u.load_asset(MESH)
    if mesh is None:
        out['asset_created'] = False
        return out
    out['asset_created'] = True
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    out['size_cm'] = [round(abs(extent.x) * 2, 2), round(abs(extent.y) * 2, 2), round(abs(extent.z) * 2, 2)]
    out['origin_cm'] = [round(bounds.origin.x, 2), round(bounds.origin.y, 2), round(bounds.origin.z, 2)]
    out['sphere_radius_cm'] = round(bounds.sphere_radius, 2)
    out['triangles'] = int(mesh.get_num_triangles(0))
    out['sections'] = int(mesh.get_num_sections(0))
    out['lods'] = int(mesh.get_num_lods())
    slots = []
    try:
        for entry in (mesh.get_editor_property('static_materials') or []):
            material = entry.get_editor_property('material_interface')
            slots.append([str(entry.get_editor_property('material_slot_name')),
                          material.get_path_name() if material else None])
    except Exception as error:
        slots = [{'error': str(error)[:200]}]
    out['material_slots'] = slots
    out['saved'] = bool(u.EditorAssetLibrary.save_loaded_asset(mesh))
    return out


def do_imported_materials():
    """Fab 包里的材质以导入结果为准；这里只登记名字与可编辑参数，不改接线。"""
    out = {'packages': [], 'assets': []}
    try:
        out['packages'] = [str(p) for p in (u.EditorAssetLibrary.list_assets(DEST, False, False) or [])]
    except Exception as error:
        out['list_error'] = str(error)[:200]
    for path in list(out['packages']):
        if not path.endswith(('_M', '_MI')) and 'Material' not in path and 'dark' not in path.lower():
            continue
        asset = u.load_asset(path)
        if asset is None or 'Material' not in asset.get_class().get_name():
            continue
        item = {'path': path, 'class': asset.get_class().get_name()}
        try:
            settings = asset.get_editor_property('editor_only_settings')
            item['scalar_parameters'] = [str(p.get_editor_property('name'))
                                         for p in (settings.get_editor_property('scalar_parameters') or [])]
            item['vector_parameters'] = [str(p.get_editor_property('name'))
                                         for p in (settings.get_editor_property('vector_parameters') or [])]
        except Exception as error:
            item['parameter_error'] = str(error)[:160]
        out['assets'].append(item)
    return out


def do_animations():
    out = {}
    for key, path in CLIPS.items():
        entry = {'path': path}
        asset = u.load_asset(path)
        if asset is None:
            entry['error'] = 'not found'
            out[key] = entry
            continue
        entry['class'] = asset.get_class().get_name()
        try:
            entry['play_seconds'] = round(float(asset.get_play_length()), 4)
        except Exception as error:
            entry['play_length_error'] = str(error)[:120]
        try:
            length = asset.get_editor_property('sequence_length')
            entry['sequence_length'] = [round(float(length.x), 4), round(float(length.y), 4),
                                        round(float(length.z), 4)]
        except Exception:
            pass
        try:
            skeleton = asset.get_skeleton()
            entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        except Exception as error:
            entry['skeleton_error'] = str(error)[:120]
        out[key] = entry
    return out


def do_arms_profile():
    """已认可裸手基准与 Sparrow 骨架的包名对照（骨名列表留给做 Bow profile 的那一轮）。"""
    out = {}
    for key, path in (('axe_arms', '/Game/Characters/ModularOutfit20260924/BarePalmV7/Axe/SK_Axe_BareArmsV7'),
                      ('m4_arms', '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7'),
                      ('sparrow_body', SPARROW + '/Meshes/Sparrow')):
        entry = {'path': path}
        mesh = u.load_asset(path)
        if mesh is None:
            entry['error'] = 'not found'
            out[key] = entry
            continue
        entry['class'] = mesh.get_class().get_name()
        try:
            skeleton = mesh.get_skeleton()
            entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        except Exception as error:
            entry['skeleton_error'] = str(error)[:120]
        out[key] = entry
    return out


section('import', do_import)
section('imported_materials', do_imported_materials)
section('animations', do_animations)
section('arms_profile', do_arms_profile)

CASE.mkdir(parents=True, exist_ok=True)
out_file = CASE / 'ue_readback.json'
out_file.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
u.log('DARKBOW_READBACK ' + str(out_file))
print('DARKBOW_READBACK_WRITTEN')
