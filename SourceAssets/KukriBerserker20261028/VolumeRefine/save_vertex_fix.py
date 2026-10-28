"""Save exactly the six blade graphs repaired during this requested game preview."""
import unreal as u,json
from pathlib import Path
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/VolumeRefine/save_vertex_fix.py').resolve().parent
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Wait for preview to end before saving')
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
receipt={'complete':False,'saved_assets':[],'compile_errors':{},'reason':'PreSkinnedPosition needs a vertex interpolator before pixel shading'}
for layout in json.loads((P/'projection-layouts.json').read_text()):
    mat=u.load_asset('/Game/Weapons/Kukri20261020/Berserker20261028/Materials/M_Berserker_'+layout['kind'])
    bridge=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionVertexInterpolator)
        and str(n.get_editor_property('desc'))=='BerserkerLocalPositionToPixel'),None)
    if not bridge:raise RuntimeError('Expected authored repair is missing: '+layout['kind'])
    errors=list(L.recompile_material(mat));receipt['compile_errors'][layout['kind']]=errors
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Cannot save '+mat.get_path_name())
    receipt['saved_assets'].append(mat.get_path_name())
receipt['complete']=True
(P/'vertex-interpolation-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SIX_BLADE_INTERPOLATION_REPAIRS_COMPILED_AND_SAVED')
