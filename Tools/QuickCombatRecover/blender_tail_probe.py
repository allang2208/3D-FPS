"""在作者源里量 A_RuneSword_PommelStrike 收势末段的逐帧角增量。

背景：UE 侧 480Hz 采样发现末段 ~20ms 处有一处整臂"脉冲"（手/前臂/上臂同步
再加速再刹停），需要判定它来自作者源烘焙还是导入环节。
"""
import bpy, math, json, sys
from mathutils import Quaternion

BLEND = r"D:\FPS3D\FPSGAME\SourceAssets\MeleePommelAttack20260916\AzureRunesword_PommelStrikeV46.blend"
OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\blender_tail.json"

bpy.ops.wm.open_mainfile(filepath=BLEND)
rig = bpy.data.objects.get('SK_RuneSword_Rig')
if rig is None:
    print("NO_RIG"); sys.exit(1)
act = rig.animation_data.action if rig.animation_data else None
print("ACTION", act.name if act else None, act.frame_range[:] if act else None)
scene = bpy.context.scene
print("SCENE_FPS", scene.render.fps, scene.render.fps_base)

N = int(act.frame_range[1])
FPS = scene.render.fps
bones = ['hand_r','hand_l','lowerarm_r','lowerarm_l','upperarm_r','upperarm_l']

res = {"action": act.name, "frames": [int(act.frame_range[0]), N], "fps": FPS, "bones": {}}
tail_frames = list(range(N-72, N+1))    # last 150 ms @480
for name in bones:
    pb = rig.pose.bones.get(name)
    if pb is None:
        continue
    local = []
    world = []
    prevq = None; prevm = None
    for f in tail_frames:
        scene.frame_set(f)
        q = pb.rotation_quaternion.copy()
        m = pb.matrix.copy()          # armature space
        if prevq is not None:
            local.append((f, round(math.degrees(q.rotation_difference(prevq).angle), 4)))
            wd = math.degrees(prevm.to_quaternion().rotation_difference(m.to_quaternion()).angle)
            world.append((f, round(wd, 4)))
        prevq = q; prevm = m
    res["bones"][name] = {"local": local, "armature": world}

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False)
print("BLENDER_TAIL_WROTE", OUT)
