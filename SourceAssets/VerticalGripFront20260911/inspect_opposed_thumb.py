import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));from inspect_pose import render
v='vertical';fit=json.loads((O/'m4'/v/'fit_final.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'m4'/v/'Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])
for n in ['thumb_01_l','thumb_02_l','thumb_03_l','index_01_l','index_02_l','index_03_l']:
 b=r.pose.bones[n];print('OPPOSED_BONE',n,list(G.inverted()@b.head),flush=True)
render(r,fit,'opposed_'+v)
