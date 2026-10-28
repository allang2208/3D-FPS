"""Repair the shader-stage error revealed by the requested in-game HUD preview."""
import json
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/VolumeRefine/fix_vertex_interpolation.py').resolve().parent
BASE='/Game/Weapons/Kukri20261020/Berserker20261028/Materials/M_Berserker_'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
targets=[BASE+r['kind'] for r in json.loads((P/'projection-layouts.json').read_text())]
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in targets):raise RuntimeError('Preserve unsaved blade materials')
materials=[]
for path in targets:
    mat=u.load_asset(path);nodes=L.get_material_expressions(mat)
    projection=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='BerserkerLocalProjection')
    position=next(n for n in nodes if isinstance(n,u.MaterialExpressionPreSkinnedPosition))
    bridge=next((n for n in nodes if isinstance(n,u.MaterialExpressionVertexInterpolator) and str(n.get_editor_property('desc'))=='BerserkerLocalPositionToPixel'),None)
    if bridge is None:
        bridge=L.create_material_expression(mat,u.MaterialExpressionVertexInterpolator)
        bridge.set_editor_property('desc','BerserkerLocalPositionToPixel')
    if not L.connect_material_expressions(position,'',bridge,'VS'):raise RuntimeError('Cannot interpolate vertex position')
    if not L.connect_material_expressions(bridge,'PS',projection,'LocalPos'):raise RuntimeError('Cannot connect pixel local position')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(path+': '+str(errors))
    materials.append(mat)
saved=[]
for mat in materials:
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Save failed '+mat.get_path_name())
    saved.append(mat.get_path_name())
(P/'vertex-interpolation-receipt.json').write_text(json.dumps({'complete':True,'saved_assets':saved,
    'reason':'PreSkinnedPosition must cross a vertex interpolator before pixel shading'},indent=2),encoding='utf-8')
print('BERSERKER_VERTEX_INTERPOLATION_SAVED',len(saved))
