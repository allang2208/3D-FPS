import bpy,json,sys
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O));from inspect_pose import render
variant=sys.argv[sys.argv.index('--')+1];D=O/'m4'/variant
bpy.ops.wm.open_mainfile(filepath=str(D/f'A_M4_{variant.title()}_idle.blend'));bpy.context.scene.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];render(r,json.loads((D/'fit_final.json').read_text()),'baked_'+variant)
