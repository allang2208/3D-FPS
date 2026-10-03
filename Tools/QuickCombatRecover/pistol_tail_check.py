"""Focused check of the pistol quick-combat tail at 480 Hz.

The earlier coarse sweep printed a possible burst near t=0.506 s of the 0.55 s
clip. Print every frame of the last 0.12 s for all arm bones so the shape is
unambiguous: a genuine re-acceleration shows as a sustained rise/decay, a
sampling artefact shows as a single-frame outlier.
"""
import unreal, json, math, os
DT = 1.0/480.0
OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\pistol_tail.json"
CLIPS = [
    ("pistol_715", "/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat"),
    ("pistol_1911", "/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat"),
    ("rifle_m4", "/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base"),
]
BONES = ["hand_r", "hand_l", "lowerarm_r", "lowerarm_l", "upperarm_r", "upperarm_l"]

def qd(a, b):
    d = abs(a.w*b.w + a.x*b.x + a.y*b.y + a.z*b.z)
    d = max(-1.0, min(1.0, d))
    return math.degrees(2.0*math.acos(d))

res = {}
for name, path in CLIPS:
    anim = unreal.load_asset(path)
    if not anim:
        res[name] = {"error": "missing"}
        continue
    L = float(anim.get_play_length())
    e = {"length": round(L, 4), "bones": {}}
    for b in BONES:
        rows = []
        prev = None
        t = max(0.0, L - 0.12)
        while t <= L + 1e-9:
            tt = min(t, L)
            p = unreal.AnimationLibrary.get_bone_pose_for_time(anim, b, tt, False)
            if p is None:
                break
            v = 0.0; step = 0.0
            if prev is not None:
                step = qd(prev.rotation, p.rotation)
                v = step/DT
            rows.append([round(tt, 5), round(step, 4), round(v, 1)])
            prev = p
            t += DT
        e["bones"][b] = rows
    res[name] = e
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
unreal.log("PISTOL_TAIL_DONE")
print("WROTE", OUT)
