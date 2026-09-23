"""Replace only SVD's four tactical actions in its existing UV-corrected source."""
import ast
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Quaternion

OUT = Path(__file__).resolve().parent
O = OUT.parent
D = O / 'Exports'
sys.path.insert(0, str(O))
from tactical_actions import author_actions

tree = ast.parse((O / 'author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in ('sample', 'select', 'bake')], type_ignores=[]),
             str(O / 'author_svd.py'), 'exec'))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(O / 'SVD_Complete_Editable.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
idle = sample(rig, bpy.data.actions['A_SVD_idle'], 0)
for key in ('sprint_enter', 'sprint_loop', 'sprint_exit', 'quick_melee'):
    old = bpy.data.actions.get('A_SVD_' + key)
    if old:
        bpy.data.actions.remove(old)
clips = author_actions(rig, idle, bake)
manifest = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
manifest['clips'].update(clips)
(O / 'authoring.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
sample(rig, bpy.data.actions['A_SVD_idle'], 0)
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 108
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'SVD_Complete_Editable.blend'))
print('SVD_TACTICAL_SOURCE_SAVED', flush=True)
