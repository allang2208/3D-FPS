"""recover 段精细运动学：480Hz 采样末段逐帧角度增量，找速度/加速度不连续点。

输出：每条 clip 在 recover 窗口内关键骨的逐帧角速度(deg/s)，以及交接瞬间
（clip 末帧 → idle 首帧）的速度差。
"""
import unreal, json, math, os

OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\tail_kinematics.json"
HZ=480.0; DT=1.0/HZ

CASES=[
    dict(name="sword_pommel",
         clip="/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",
         idle="/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle",
         bones=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l"],
         window=(0.90,1.60), idle_window=(0.0,0.10)),
    dict(name="pistol_715",
         clip="/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat",
         idle="/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_idle",
         bones=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r"],
         window=(0.30,0.55), idle_window=(0.0,0.10)),
    dict(name="rifle_base",
         clip="/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base",
         idle=None,
         bones=["hand_r","hand_l","lowerarm_r","lowerarm_l","WPN_root"],
         window=(0.55,0.90), idle_window=None),
    dict(name="axe_hitrecover",
         clip="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_HitRecover",
         idle="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle",
         bones=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_l","WPN_root"],
         window=(0.0,0.44), idle_window=(0.0,0.10)),
]

def qang(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z)
    d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))

def sample(anim,bone,t):
    try: return unreal.AnimationLibrary.get_bone_pose_for_time(anim,bone,t,False)
    except Exception: return None

def profile(anim,bone,t0,t1):
    T=[]; t=t0
    while t<=t1+1e-6:
        T.append(min(t,t1)); t+=DT
    out=[]
    prev=None
    for tt in T:
        p=sample(anim,bone,tt)
        if p is None: continue
        v=0.0
        if prev is not None:
            v=qang(prev.rotation,p.rotation)/DT
        out.append([round(tt,5),round(v,1)])
        prev=p
    return out

res={}
for c in CASES:
    e={"clip":c["clip"]}
    clip=unreal.load_asset(c["clip"])
    if not clip: e["error"]="missing"; res[c["name"]]=e; continue
    L=float(clip.get_play_length())
    e["length"]=round(L,4)
    e["recover"]={}
    for b in c["bones"]:
        e["recover"][b]=profile(clip,b,c["window"][0],min(c["window"][1],L))
    if c.get("idle"):
        idle=unreal.load_asset(c["idle"])
        if idle:
            e["idle_start"]={}
            for b in c["bones"]:
                e["idle_start"][b]=profile(idle,b,c["idle_window"][0],c["idle_window"][1])
    res[c["name"]]=e

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f: json.dump(res,f,ensure_ascii=False)
unreal.log("TAIL_KIN_DONE")
print("WROTE",OUT)
