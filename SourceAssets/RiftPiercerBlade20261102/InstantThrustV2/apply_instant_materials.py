"""Patch only the two active spectral materials; preserve meshes and the held sword finish."""
from pathlib import Path
import unreal as u,json
P=Path(__file__).resolve().parent;SOURCE=P.parent
D='/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active: preserve materials')
targets={D+'/M_RiftPiercer_Phantom':'phantom.hlsl',D+'/M_RiftPiercer_Mote':'mote.hlsl'}
if any(p.get_path_name() in targets for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved Rift Piercer materials')
saved=[]
for path,source in targets.items():
    mat=E.load_asset(path)
    if not mat:raise RuntimeError('Missing '+path)
    expressions=L.get_material_expressions(mat)
    custom=[e for e in expressions if isinstance(e,u.MaterialExpressionCustom)]
    if len(custom)!=1:raise RuntimeError('Unexpected custom graph '+path)
    custom[0].set_editor_property('code',(SOURCE/source).read_text(encoding='utf8'))
    if not any(isinstance(e,u.MaterialExpressionTemporalResponsivenessOutput) for e in expressions):
        output=L.create_material_expression(mat,u.MaterialExpressionTemporalResponsivenessOutput)
        value=L.create_material_expression(mat,u.MaterialExpressionConstant);value.set_editor_property('r',1.)
        if not L.connect_material_expressions(value,'',output,''):raise RuntimeError('Temporal response connection failed')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    L.get_statistics(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Cannot save '+path)
    saved.append(mat.get_path_name())
(P/'import-receipt.json').write_text(json.dumps({'assets_saved':True,'assets':saved,'revision':'instant_full_length_thrust_v2','game_tested':False},indent=2),encoding='utf8')
u.log('RIFT_PIERCER_INSTANT_MATERIALS_SAVED')
