"""Endpoint per-frame deltas at 480 Hz for the three quick-combat clips.

Prints frames so a late re-acceleration pulse is visible frame by frame, not as
an aggregate. Read-only.
"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\endpoint_compare.json"
CASES=[
 ("sword_pommel","/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
 ("pistol_715","/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat"),
 ("pistol_1911","/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat"),
 ("rifle_base","/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base"),
]
BONES=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l"]

def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def P(a,b,t): return unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)
def comp(a,bone,t):
    path=[str(n) for n in unreal.AnimationLibrary.find_bone_path_to_root(a,bone)]
    acc=None
    for n in reversed(path):
        p=P(a,n,t)
        if p is None: return None
        acc = p if acc is None else p.multiply(acc)
    return acc

res={}
for name,path in CASES:
    a=unreal.load_asset(path)
    if not a: res[name]={"error":"missing"}; continue
    L=float(a.get_play_length())
    e={"length":round(L,4),"bones":{}}
    for b in BONES:
        rows=[];prev=None
        t0=L-0.18
        t=t0
        while t<=L+1e-9:
            tt=min(t,L); c=comp(a,b,tt)
            if c is None: break
            d=0.0
            if prev is not None: d=qd(prev.rotation,c.rotation)
            rows.append([round(tt,4),round(d,3)])
            prev=c; t+=DT
        e["bones"][b]=rows
    res[name]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("ENDPOINT_COMPARE_DONE")
print("WROTE",OUT)
