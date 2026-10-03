import bpy,json,ast,math,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
family=sys.argv[-1] if sys.argv[-1] in ['base','vertical','canted','prism','angled'] else 'base'
info=json.loads((O/'authoring.json').read_text())[family+'/reload_empty']
bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions[info['action']];s=bpy.context.scene;ob=bpy.data.objects['SK_Manny_Arms_Export']
code=(O/'prepare.py').read_text().split('# Requested before views',1)[1];code='# Requested before views'+code
code=code.replace("f'before_fp_",f"f'after_{family}_fp_").replace("'before_grasp_330.png'",f"'after_{family}_grasp_330.png'")
exec(compile(code,'<same review cameras>','exec'))
cam.location=target+Vector((-.25,.20,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.32
s.render.filepath=str(out/f'after_{family}_grasp_back_330.png');bpy.ops.render.render(write_still=True)
