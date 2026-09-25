import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
source=json.loads((P.parent/'ArmsV2/author_skin_cause.json').read_text())['rest']
bpy.ops.wm.open_mainfile(filepath=str(P/'Bow_BareArmsV7_Actions.blend'))
rig=bpy.data.objects['Bow_V7_Native'];S=Matrix.Diagonal((1,-1,1))
for n in ['bow_root','upperarm_l','lowerarm_l','hand_l','index_01_l','index_02_l']:
    original=Matrix(source[n]);actual=S@rig.data.bones[n].matrix_local.to_3x3()@S
    delta=actual@original.to_3x3().transposed()
    print('AUTHOR_REST_BASIS',n,delta.to_quaternion().angle*180/math.pi)
