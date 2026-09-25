"""Measure the imported SK_DarkBow without re-importing: bounds, axis mapping, slots, parents.

The previous pass imported the mesh successfully but aborted before the numbers were recorded
(`AssetImportTask` exposes no `errors` attribute in this build). This pass only reads.
"""

import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
CASE = ROOT / 'SourceAssets' / 'DarkBow20260925'
MESH = '/Game/Weapons/DarkBow20260925/SK_DarkBow'
ARMS = ('/Game/Characters/ModularOutfit20260924/BarePalmV7/Axe/SK_Axe_BareArmsV7',
        '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7',
        '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Meshes/Sparrow')

report = {'runtime_tested': False, 'rendered': False, 'sections': {}}


def section(name, function):
    try:
        report['sections'][name] = function()
    except Exception as error:
        report['sections'][name] = {'error': str(error)[:300], 'trace': traceback.format_exc(limit=3)}
    u.log('DARKBOW_SECTION ' + name + ' -> '
          + json.dumps(report['sections'][name], ensure_ascii=False)[:1400])


def do_mesh():
    out = {}
    mesh = u.load_asset(MESH)
    if mesh is None:
        return {'error': 'not found: ' + MESH}
    out['class'] = mesh.get_class().get_name()
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    out['size_cm'] = [round(abs(extent.x) * 2, 3), round(abs(extent.y) * 2, 3), round(abs(extent.z) * 2, 3)]
    out['origin_cm'] = [round(bounds.origin.x, 3), round(bounds.origin.y, 3), round(bounds.origin.z, 3)]
    out['sphere_radius_cm'] = round(bounds.sphere_radius, 3)
    out['triangles'] = int(mesh.get_num_triangles(0))
    out['vertices'] = int(mesh.get_num_vertices(0))
    out['sections'] = int(mesh.get_num_sections(0))
    out['lods'] = int(mesh.get_num_lods())
    slots = []
    for entry in (mesh.get_editor_property('static_materials') or []):
        material = entry.get_editor_property('material_interface')
        parent = None
        if material is not None and material.get_class().get_name() == 'MaterialInstanceConstant':
            parent = material.get_editor_property('parent')
        slots.append({'slot': str(entry.get_editor_property('material_slot_name')),
                      'material': material.get_path_name() if material else None,
                      'class': material.get_class().get_name() if material else None,
                      'parent': parent.get_path_name() if parent else None})
    out['material_slots'] = slots
    out['saved'] = bool(u.EditorAssetLibrary.save_loaded_asset(mesh))
    return out


def do_mesh_tools():
    """这个构建里可用的网格侧 API 拼写，供之后加弓梢挂点时照抄。"""
    out = {}
    for name in ('get_socket_names' , 'add_socket', 'find_socket', 'get_sockets_by_tag'):
        out[name] = hasattr(u.StaticMesh, name)
    mesh = u.load_asset(MESH)
    try:
        out['sockets'] = [str(s) for s in mesh.get_sockets_by_tag('')] if hasattr(mesh, 'get_sockets_by_tag') else None
    except Exception as error:
        out['sockets_error'] = str(error)[:160]
    return out


def do_arms_skeletons():
    out = {}
    for path in ARMS:
        entry = {'path': path}
        mesh = u.load_asset(path)
        if mesh is None:
            entry['error'] = 'not found'
            out[path.rsplit('/', 1)[-1]] = entry
            continue
        skeleton = mesh.get_editor_property('skeleton')
        entry['skeleton'] = skeleton.get_path_name() if skeleton else None
        try:
            entry['skeleton_class'] = skeleton.get_class().get_name()
        except Exception:
            pass
        out[path.rsplit('/', 1)[-1]] = entry
    return out


section('mesh', do_mesh)
section('mesh_tools', do_mesh_tools)
section('arms_skeletons', do_arms_skeletons)

out_file = CASE / 'ue_mesh_readback.json'
out_file.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
u.log('DARKBOW_MESH_READBACK ' + str(out_file))
print('DARKBOW_MESH_READBACK_WRITTEN')
