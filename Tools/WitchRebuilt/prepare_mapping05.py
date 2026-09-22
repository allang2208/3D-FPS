"""Keep the original accepted visible mesh and existing proxies for bounded rebinding."""
import bpy,sys
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
sys.path.insert(0,str(Path(__file__).parent));import author_drape04
bpy.ops.wm.open_mainfile(filepath=str(root/'Spike20260922/Before/WitchRebuilt_Master.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
author_drape04.export(rig);rig.data.pose_position='POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'Authoring/WitchRebuilt_Master.blend'))
print('Original mesh/proxies preserved. Drape05 changes their engine binding only.')
