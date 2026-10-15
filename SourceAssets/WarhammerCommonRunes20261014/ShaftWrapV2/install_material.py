"""Save a shaft-local cylindrical rune overlay while retaining shared artwork."""
import unreal as u, json
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT: raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor(): raise RuntimeError('PIE active; defer material save')
source = '/Game/Weapons/SteelWarhammer20261014/Runes/M_SilverRuneSurface_Warhammer'
folder = '/Game/Weapons/SteelWarhammer20261014/Runes/ShaftWrapV2'
name = 'M_SilverRuneSurface_WarhammerShaftV2'
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name()==folder+'/'+name: raise RuntimeError('Unsaved target material')
A = u.AssetToolsHelpers.get_asset_tools()
E = u.MaterialEditingLibrary
original = u.load_asset(source)
if not original: raise RuntimeError('Current hammer rune material unavailable')
material = u.load_asset(folder+'/'+name)
if not material: material = A.duplicate_asset(name,folder,original)
if not material: raise RuntimeError('Cannot create shaft material')
custom = next(n for n in E.get_material_expressions(material)
              if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
code = custom.get_editor_property('code')
marker = 'float2 texel = HaloRadiusTexels'
if marker not in code: raise RuntimeError('Unknown rune sampling layout')
snapshot = P/'source_shader.hlsl'
if not snapshot.exists(): snapshot.write_text(code,encoding='utf-8')
new_code = (P/'shaft_projection.hlsl').read_text(encoding='utf-8')+code[code.index(marker):]
material.modify(); custom.modify()
custom.set_editor_property('code',new_code)
custom.set_editor_property('description','Warhammer bare-shaft arc-length wrap; isotropic artwork scale')
material.set_editor_property('used_with_skeletal_mesh',False)
errors = list(E.recompile_material(material))
if errors: raise RuntimeError('Rune shader compilation failed: '+str(errors))
if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()],False):
    raise RuntimeError('Shaft rune material save failed')
(P/'warhammer_shaft_runes.hlsl').write_text(new_code,encoding='utf-8')
(P/'import_receipt.json').write_text(json.dumps({
    'complete':True,'source_material':source,'saved_material':material.get_path_name(),
    'module':'shaft','local_axial_range_cm':[-39.5,-2.0],'weapon_axial_range_cm':[42.5,80.0],
    'mapping':'surface arc length and source texture aspect; equal scale along both axes',
    'resonance_copies':1,'narrow_motif_copies':2,'new_masks':0,'new_icons':0,
    'existing_palette_and_fade_preserved':True,'game_tested':False
},indent=2),encoding='utf-8')
print('WARHAMMER_SHAFT_RUNE_MATERIAL_SAVED')
