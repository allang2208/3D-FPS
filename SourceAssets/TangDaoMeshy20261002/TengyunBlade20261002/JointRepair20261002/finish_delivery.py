"""Record production/save results after the completed background import."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
T = P.parent
m = json.loads((T/'blade_manifest.json').read_text(encoding='utf-8'))
r = json.loads((T/'import_receipt.json').read_text(encoding='utf-8'))
if not r.get('complete') or r.get('revision') != m['repair_revision']:
    raise RuntimeError('Keep the previous delivery state until this revision finishes saving')
joint = json.loads((P/'authored-joint.json').read_text(encoding='utf-8'))
delivery = {'date': '2026-10-02', 'revision': m['repair_revision'], 'weapon': m['weapon'],
    'option': m['id'], 'status': 'authored_imported_saved_and_catalogs_installed',
    'cause': 'factory blade retained between shared guard seat z=1.4cm and z=8cm',
    'root_transition_cm': m['root_transition_cm'], 'uv_z_cm': m['uv_z_cm'],
    'authored_joint': joint, 'mesh': m['mesh'], 'materials': m['materials'],
    'lod_triangles_authored': m['lod_triangles'], 'lod_triangles_saved': r['lod_triangles_saved'],
    'saved_assets': r['assets'], 'saved_asset_count': len(r['assets']),
    'import_log': 'import.log', 'import_receipt': '../import_receipt.json',
    'catalog_receipt': '../catalog_receipt.json', 'method': 'fresh_packages_background_commandlet',
    'old_loaded_editor_packages_overwritten': False,
    'editor_started_or_restarted': False, 'existing_play_session_stopped': False,
    'native_cpp_changed': False, 'native_build_required': False,
    'gameplay_stats_changed': False, 'cloud_rune_kill_recovery_ratio_retained': .15,
    'runtime_tested': False, 'game_or_pie_started': False, 'acceptance_rendered': False,
    'user_action': 'End the current play session and enter again to reload the saved module catalog'}
(P/'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
file = T/'delivery.json'
parent = json.loads(file.read_text(encoding='utf-8'))
parent.update(status=delivery['status'], mesh=m['mesh'], lod_triangles_authored=m['lod_triangles'],
    lod_triangles_saved=r['lod_triangles_saved'], assets_saved_count=len(r['assets']),
    joint_repair='JointRepair20261002/delivery.json', current_revision=m['repair_revision'])
parent['integration'] = {'method': 'fresh_packages_background_commandlet', 'result': 'saved',
    'exit_code': 0, 'log': 'JointRepair20261002/import.log',
    'native_rune_graph_retained': True, 'cloud_rune_graph_retained': True,
    'whirlwind_material_registered': True, 'holding_interface_changed': False,
    'gameplay_stats_changed': False, 'native_cpp_changed': False,
    'native_build_required': False, 'existing_play_session_stopped': False}
file.write_text(json.dumps(parent, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
with (P/'README.md').open('a', encoding='utf-8') as out:
    out.write('\n实际落盘：保存 '+str(len(r['assets']))+' 项新 UE 资产（3 张全长 PBR、2 个祥云兼容钢刃材质、1 个三档 LOD 网格）；模块及表面绑定已更新。三档 LOD 保存三角数为 '+
        '／'.join(str(n) for n in r['lod_triangles_saved'])+'。未修改当前游玩中的旧资产；游戏测试由用户完成。\n')
print('TENGYUN_JOINT_DELIVERED', json.dumps({'mesh': m['mesh'], 'saved_assets': len(r['assets']),
    'old_surface_faces': joint['old_surface_faces'], 'runtime_tested': False}, ensure_ascii=False), flush=True)
