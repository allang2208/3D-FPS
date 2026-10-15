"""Clone the current shared rune material and fit it to the actual hammer seat."""
import unreal as u,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; defer without stopping play')
source='/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2'
folder='/Game/Weapons/SteelWarhammer20261014/Runes';name='M_SilverRuneSurface_Warhammer'
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name()==folder+'/'+name:raise RuntimeError('Unsaved hammer rune material')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
original=u.load_asset(source)
if not original:raise RuntimeError('Current shared rune material missing')
material=u.load_asset(folder+'/'+name)
if not material:material=A.duplicate_asset(name,folder,original)
if not material:raise RuntimeError('Cannot create hammer material')
nodes=list(E.get_material_expressions(material))
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
code=custom.get_editor_property('code')
if 'uint texWidth' not in code:raise RuntimeError('Unexpected current shared rune shader layout')
snapshot=P/'source_shader.hlsl'
if not snapshot.exists():snapshot.write_text(code,encoding='utf-8')
header=(P/'hammer_projection.hlsl').read_text(encoding='utf-8')
new_code=header+code[code.index('uint texWidth'):]
custom.set_editor_property('code',new_code)
custom.set_editor_property('description','Shared semantic runes fitted to warhammer central-seat faces')
material.set_editor_property('used_with_skeletal_mesh',False)
errors=list(E.recompile_material(material))
if errors:raise RuntimeError('Hammer rune material compilation failed: '+str(errors))
if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()],False):raise RuntimeError('Hammer rune material save failed')
(P/'warhammer_runes.hlsl').write_text(new_code,encoding='utf-8')
runpy.run_path(str(P/'register_runes.py'),run_name='__main__')
(P/'import_receipt.json').write_text(json.dumps({'complete':True,'source_material':source,'saved_material':material.get_path_name(),
    'options_source':'melee-gunsmith.json / blade_2','options':['haste_rune','resonance_rune','erosion_rune','conduction_rune'],
    'icon_source':'existing shared blade_2_<id> keys','new_textures':0,'new_icons':0,'game_tested':False},indent=2),encoding='utf-8')
print('WARHAMMER_COMMON_RUNE_MATERIAL_SAVED')
