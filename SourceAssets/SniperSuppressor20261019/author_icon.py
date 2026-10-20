"""Production attachment icon from the actual game mesh, no acceptance render."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SniperHeavySuppressor_Editable.blend'))
ob=bpy.data.objects['SM_SniperHeavySuppressor']
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
scene.world=bpy.data.worlds.new('ProductionIconWorld');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');worldout=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
bg.inputs['Color'].default_value=(.12,.12,.12,1);bg.inputs['Strength'].default_value=.35
scene.world.node_tree.links.new(bg.outputs['Background'],worldout.inputs['Surface'])
# Reuse the current metal frame, corner rivets and circular rim authoring recipe.
source=(O.parent/'CommonHammerHeads20261014/author_icons.py').read_text(encoding='utf-8')
frame=source[source.index('def metal('):source.index('for row,obj in zip(rows,modules):')]
exec(compile(frame,'shared_modification_icon_frame','exec'),globals())
scale=1.22/math.hypot(.317,.0532)
ob.scale=(scale,scale,scale);ob.rotation_euler.z=math.pi
ob.location=(.317*.5*scale,-.20,0)
scene.render.filepath=str(O/'muzzle_sniper_heavy_suppressor.png')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'SniperHeavySuppressor_Icon.blend'))
bpy.ops.render.render(write_still=True)
(O/'icon_authoring.json').write_text(json.dumps({'image':scene.render.filepath,'source':'SniperHeavySuppressor_Editable.blend','forward':'image left','style':'shared grayscale metal frame, four rivets, inner ring','production_asset':True,'runtime_tested':False},indent=2))
print('SNIPER_SUPPRESSOR_ICON_AUTHORED',flush=True)
