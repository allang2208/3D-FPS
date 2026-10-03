"""Record the finished author/export/import results without running the game."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
T = P.parent
m = json.loads((T/'blade_manifest.json').read_text(encoding='utf-8'))
r = json.loads((T/'import_receipt.json').read_text(encoding='utf-8'))
if not r.get('complete') or r.get('revision') != 'TangDaoTengyunPlanarSolidV4_20261002':
    raise RuntimeError('The new planar blade is not saved yet')
shape = json.loads((P/'authored-geometry.json').read_text(encoding='utf-8'))
delivery = {'date':'2026-10-02','revision':m['repair_revision'],'weapon':m['weapon'],
    'option':m['id'],'status':'authored_imported_saved_and_catalogs_installed',
    'mesh':m['mesh'],'body_thickness_mm':m['body_thickness_mm'],
    'original_root_geometry_retained':False,'root_perimeter_interpolation_removed':True,
    'main_faces_parallel':True,'dragon_detail':'existing baked PBR and normal maps',
    'source_geometry':shape,'lod_triangles_authored':m['lod_triangles'],
    'lod_triangles_saved':r['lod_triangles_saved'],'saved_assets':r['assets'],
    'surface_assets_reused_without_writes':r['surface_assets_reused_without_writes'],
    'saved_asset_count':len(r['assets']),'integration_method':'new_mesh_background_commandlet',
    'import_log':'import.log','existing_editor_asset_packages_overwritten':False,
    'editor_started_or_restarted':False,'existing_play_session_stopped':False,
    'native_cpp_changed':False,'native_build_required':False,'gameplay_stats_changed':False,
    'runtime_tested':False,'acceptance_rendered':False,
    'user_action':'End current play session and enter again to reload the model catalog'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
file = T/'delivery.json'
previous = json.loads(file.read_text(encoding='utf-8'))
previous.update(status=delivery['status'],mesh=m['mesh'],current_revision=m['repair_revision'],
    planar_repair='PlanarRepair20261002/delivery.json',
    lod_triangles_authored=m['lod_triangles'],lod_triangles_saved=r['lod_triangles_saved'],
    assets_saved_count=len(r['assets']),body_thickness_mm=m['body_thickness_mm'])
previous['integration'] = {'method':'new_mesh_background_commandlet','result':'saved','exit_code':0,
    'log':'PlanarRepair20261002/import.log','existing_play_session_stopped':False,
    'surface_assets_reused_without_writes':True,'native_rune_graph_retained':True,
    'native_cpp_changed':False,'native_build_required':False,'gameplay_stats_changed':False}
file.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (P/'README.md').open('a',encoding='utf-8') as out:
    out.write('\n实际落盘：新网格已导入保存，三档 LOD 保存三角数为 '+
        '／'.join(str(n) for n in r['lod_triangles_saved'])+'；已更新模块目录与绑定，继续引用现有符文兼容材质。没有游戏测试或验收渲染。\n')
print('TENGYUN_PLANAR_DELIVERED',json.dumps({'mesh':m['mesh'],'saved_assets':len(r['assets']),
    'body_thickness_mm':m['body_thickness_mm'],'runtime_tested':False}),flush=True)
