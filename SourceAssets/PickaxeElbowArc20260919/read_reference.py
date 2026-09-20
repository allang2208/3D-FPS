"""Read existing authoring joint frames to guide the requested elbow refinement."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(r'D:\FPS3D\FPSGAME')
AUTHOR=ROOT/'SourceAssets/PickaxeNaturalArms20260919/author_attack.py'
scope={'__file__':str(AUTHOR)}
exec(compile(AUTHOR.read_text(encoding='utf-8').split('\nreport = ')[0],str(AUTHOR),'exec'),scope)
state={}; rows=[]
for frame in range(205):
    t=frame/300*.6/.24 if frame<=72 else .6+(frame/300-.24)*.56/.44
    pose=scope['pose_frame'](scope['swing_frame'](t),t,False,state)
    if frame in (14,29,43,56,63,67,72,94,119,153,183):
        rows.append({'seconds':round(t,4),'forearm_unwrapped_degrees':{k:round(v*180/3.14159265,1) for k,v in state.items() if k.endswith('_twist')}})
print(json.dumps(rows),flush=True)
(Path(__file__).parent/'reference_joint_frames.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
