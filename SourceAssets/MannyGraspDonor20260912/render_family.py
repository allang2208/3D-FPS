import bpy,json,sys
from pathlib import Path
O=Path(__file__).parent;OLD=O.parent/'VerticalGripFront20260911';sys.path.insert(0,str(OLD));import inspect_pose
inspect_pose.O=O
for weapon in ['m4','akm']:
 name=f'A_{weapon.upper()}_{"Vertical" if weapon=="m4" else "vertical"}_idle'
 bpy.ops.wm.open_mainfile(filepath=str(O/weapon/'vertical'/(name+'.blend')));bpy.context.scene.frame_set(0)
 fit=json.loads((O/'aligned_fit.json').read_text()) if weapon=='m4' else json.loads((OLD/'akm/fits.json').read_text())['vertical']
 inspect_pose.render(bpy.data.objects['SK_M4_Infima'],fit,'family_'+weapon)
