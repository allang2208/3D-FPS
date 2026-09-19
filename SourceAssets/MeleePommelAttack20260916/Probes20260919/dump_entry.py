import bpy, math, json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'AzureRunesword_PommelStrikeV46.blend'))
rig=bpy.data.objects['SK_RuneSword_Rig']; scene=bpy.context.scene
def dd(a,b):
    x=math.degrees(a.rotation_difference(b).angle)
    return 360.0-x if x>180.0 else x
out={}
prev={}
for f in range(120,180):
    scene.frame_set(f)
    row={}
    for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r'):
        q=rig.pose.bones[n].matrix.to_quaternion()
        row[n]=round(dd(prev[n],q),3) if n in prev else 0.0
        prev[n]=q.copy()
    out[f]=row
for f,row in out.items():
    print(f, ' '.join(f'{k}={v:.2f}' for k,v in row.items()))
