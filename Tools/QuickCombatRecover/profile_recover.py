"""快速近战与近战武器的 recover 段逐帧速度剖面。

对每条 clip 以 1/120s 密采样，输出关键骨（双臂 + 手）的角速度(deg/s)时间序列，
用于找"突然形变/切换不自然"的跳变点；并输出末帧相对 idle 首帧的姿态差。
"""
import unreal, json, math, os

OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\profiles.json"
HZ = 120.0
DT = 1.0/HZ

KEY = ["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l",
       "clavicle_r","clavicle_l","index_01_l","thumb_01_l","WPN_root"]

CASES = [
    dict(name="sword_pommel",
         clip="/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",
         idle="/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"),
    dict(name="pistol_715",
         clip="/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat",
         idle="/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_idle"),
    dict(name="pistol_1911",
         clip="/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat",
         idle="/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_idle"),
    dict(name="rifle_base",
         clip="/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base",
         idle=None),
    dict(name="axe_idle2h",
         clip="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle",
         idle=None),
    dict(name="axe_swing",
         clip="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Swing",
         idle="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle"),
    dict(name="axe_hitrecover",
         clip="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_HitRecover",
         idle="/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle"),
]

def qang(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z)
    d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))

def sample(anim,bone,t):
    try:
        return unreal.AnimationLibrary.get_bone_pose_for_time(anim,bone,t,False)
    except Exception:
        return None

def exists(anim,bone):
    return sample(anim,bone,0.0) is not None

out={}
for c in CASES:
    e={"clip":c["clip"]}
    clip=unreal.load_asset(c["clip"])
    if not clip:
        e["error"]="clip missing"; out[c["name"]]=e; continue
    L=float(clip.get_play_length()); e["length"]=round(L,4)
    bones=[b for b in KEY if exists(clip,b)]
    e["bones"]=bones
    T=[]; 
    t=0.0
    while t <= L+1e-6:
        T.append(round(min(t,L),5)); t+=DT
    series={}
    for b in bones:
        prev=None; row=[]
        for tt in T:
            p=sample(clip,b,tt)
            if prev is not None:
                row.append(round(qang(prev.rotation,p.rotation)/DT,1))
            else:
                row.append(0.0)
            prev=p
        series[b]=row
    e["times"]=T
    e["vel"]=series
    # find biggest single-step jumps (accel spikes) in last 60% of clip
    spikes=[]
    for b in bones:
        v=series[b]
        for i in range(2,len(v)):
            if T[i] < L*0.35: continue
            dv=v[i]-v[i-1]
            if abs(dv) > 600:
                spikes.append((b,round(T[i],3),v[i-1],v[i],round(dv,1)))
    e["spikes_gt600"]=spikes[:40]
    # end vs idle
    if c["idle"]:
        idle=unreal.load_asset(c["idle"])
        if idle:
            rows=[]
            for b in bones:
                pe=sample(clip,b,L); pi=sample(idle,b,0.0)
                if pe is None or pi is None: continue
                rows.append({"bone":b,
                             "dpos_cm":round((pe.translation-pi.translation).length()*100,3),
                             "drot_deg":round(qang(pe.rotation,pi.rotation),3)})
            e["end_vs_idle"]=rows
            e["end_vs_idle_max_dpos_cm"]=max((r["dpos_cm"] for r in rows),default=0)
            e["end_vs_idle_max_drot_deg"]=max((r["drot_deg"] for r in rows),default=0)
        else:
            e["idle_error"]="idle missing"
    out[c["name"]]=e

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=1)
unreal.log("QUICKCOMBAT_PROFILE_DONE")
print("WROTE",OUT)
