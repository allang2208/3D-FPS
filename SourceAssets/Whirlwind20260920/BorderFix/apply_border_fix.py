"""Remove the whirlwind blur's colored screen rim; build/save only, no PIE."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).parent
path='/Game/Skills/Whirlwind20260920/M_WhirlwindFocus'
mat=u.load_asset(path)
if not mat:raise RuntimeError('Missing whirlwind focus material')
nodes=[e for e in u.MaterialEditingLibrary.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom)]
if len(nodes)!=1:raise RuntimeError('Unexpected focus graph; preserve the material')
node=nodes[0]
before=json.loads((P/'material-before.json').read_text(encoding='utf-8'))
old=next(row['code'] for row in before if 'code' in row)
if node.get_editor_property('code')!=old:
    raise RuntimeError('Focus shader changed since it was read; preserve concurrent edits')
code=(P.parent/'WindupV2/focus_blur.hlsl').read_text(encoding='utf-8')
node.set_editor_property('code',code)
node.set_editor_property('description','Background yaw blur; foreground protected, screen border unchanged')
errors=u.MaterialEditingLibrary.recompile_material(mat)
if errors:raise RuntimeError('\n'.join(errors))
# Finish this material's required shader compilation before saving it.
u.MaterialEditingLibrary.get_statistics(mat)
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):
    raise RuntimeError('Focus material save failed')
(P/'apply-receipt.json').write_text(json.dumps({'asset':mat.get_path_name(),'saved':True,'shader_build_finished':True,'screen_rim_passthrough':0.025,'full_blur_from':0.075,'game_tested':False},indent=2),encoding='utf-8')
print('WHIRLWIND_BORDER_FIX_SAVED '+mat.get_path_name())
