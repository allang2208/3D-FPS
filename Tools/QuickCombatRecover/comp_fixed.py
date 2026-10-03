"""组件空间运动学（修正合成顺序）+ 末段波形。

Child_abs = Child_local.multiply(Parent_abs)（UE: A.multiply(B) 里 B 是父级）。
路径顺序为 [bone..root]，因此从 root 往回合成：acc = local(b).multiply(acc)。
输出：每条 clip 各关键骨在末段的角速度(deg/s) 与手/肘的组件空间轨迹(cm)。
"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\comp_fixed.json"
BONES=["hand_r","lowerarm_r","upperarm_r","hand_l","lowerarm_l","upperarm_l"]
CASES=[
 ("pommel","/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",1.60),
 ("slash1","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1",None),
 ("thrust","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Thrust",None),
 ("pistol_715","/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat",None),
 ("pistol_1911","/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat",None),
 ("rifle_base","/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base",None),
 ("idle","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle",None),
]
def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def L(a,b,t):
    p=unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)
    return p
def comp(a,bone,t):
    path=[str(n) for n in unreal.AnimationLibrary.find_bone_path_to_root(a,bone)]
    acc=None
    for n in reversed(path):     # root -> bone
        p=L(a,n,t)
        if p is None: return None
        acc = p if acc is None else p.multiply(acc)
    return acc

res={}
for name,path,defwin in CASES:
    a=unreal.load_asset(path)
    if not a: res[name]={"error":"missing"}; continue
    Lng=float(a.get_play_length()); e={"length":round(Lng,4),"bones":{}}
    win=defwin or Lng
    t0=max(0.0,win-0.45)
    for b in BONES:
        rows=[];prev=None
        t=t0
        while t<=win+1e-9:
            tt=min(t,win); c=comp(a,b,tt)
            if c is None: break
            w=0.0
            if prev is not None: w=qd(prev.rotation,c.rotation)/DT
            rows.append({"t":round(tt,4),"w":round(w,0),
                         "p":[round(x*100,2) for x in (c.translation.x,c.translation.y,c.translation.z)]})
            prev=c; t+=DT
        if rows:
            ws=[r["w"] for r in rows]
            e["bones"][b]={"end_w":ws[-1],"peak_w":max(ws),"peak_at":rows[ws.index(max(ws))]["t"],
                           "end_p":rows[-1]["p"],"rows":rows}
    res[name]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("COMP_FIXED_DONE")
print("WROTE",OUT)
