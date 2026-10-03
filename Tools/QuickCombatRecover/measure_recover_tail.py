"""量快速近战各 clip 的收势（recover）段末帧与运行时 idle 的姿态差。

- 剑(配重锤):  /Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike vs A_RuneSword_Idle
- 手枪 715   :  .../Upgrade20260914/Animations/A_DW715_quickcombat vs A_DW715_idle
- 手枪 1911  :  .../M1911/QuickCombat20260919/Animations/A_M1911_quickcombat vs Contact20260913 idle
- 步枪 M4    :  .../M4StockMelee20260918/Base/A_M4_QuickCombat_Base vs M4 idle 路径未知，跳过 idle 对比

对每条 clip 量：
  a) 末帧每个骨相对其父的"局部"姿态 vs idle 首帧局部姿态（UE get_bone_pose_for_time(..., outer=False) 已是父级相对）；
  b) 末段 3 帧的逐骨角速度，判断收尾是否瞬时跳变。
"""
import unreal, json, math, os

OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\recover_tail.json"

CASES = [
    dict(name="sword_pommel",
         clip="/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",
         idle="/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"),
    dict(name="pistol_715",
         clip="/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat",
         idle="/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_idle"),
    dict(name="pistol_1911",
         clip="/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat",
         idle="/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_Contact_idle"),
    dict(name="rifle_base",
         clip="/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base",
         idle=None),
]

BONES = ["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l",
         "clavicle_r","clavicle_l","spine_03","spine_02","spine_01","pelvis",
         "index_01_l","index_02_l","index_03_l","middle_01_l","middle_02_l","middle_03_l",
         "pinky_01_l","pinky_02_l","pinky_03_l","ring_01_l","ring_02_l","ring_03_l",
         "thumb_01_l","thumb_02_l","thumb_03_l",
         "index_01_r","middle_01_r","thumb_01_r",
         "WPN_root","WPN_SOCKET_Muzzle"]

def qang(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z)
    d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))

def sample(anim, bone, t):
    try:
        p=unreal.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
        return p
    except Exception as e:
        return None

result={}
for c in CASES:
    e={"clip":c["clip"],"idle":c["idle"]}
    try:
        clip=unreal.load_asset(c["clip"])
        if not clip:
            e["error"]="clip missing";result[c["name"]]=e;continue
        e["length"]=round(float(clip.get_play_length()),4)
        bones=[]
        for b in BONES:
            if sample(clip,b,0.0) is not None: bones.append(b)
        e["bones_found"]=[b for b in bones]
        # a) end-of-clip vs idle frame 0 (local, parent-relative)
        if c["idle"]:
            idle=unreal.load_asset(c["idle"])
            if not idle:
                e["idle_error"]="idle missing"
            else:
                e["idle_length"]=round(float(idle.get_play_length()),4)
                rows=[]
                for b in bones:
                    pe=sample(clip,b,e["length"]); pi=sample(idle,b,0.0)
                    if pe is None or pi is None: continue
                    dloc=(pe.translation-pi.translation).length()*100.0
                    dang=qang(pe.rotation,pi.rotation)
                    rows.append((b,round(dloc,3),round(dang,3)))
                rows.sort(key=lambda r:max(r[1],r[2]*0.2),reverse=True)
                e["end_vs_idle"]=rows
                e["end_vs_idle_max_dpos_cm"]=max((r[1] for r in rows),default=0)
                e["end_vs_idle_max_drot_deg"]=max((r[2] for r in rows),default=0)
        # b) tail velocity: last 3 frames of clip, per-bone rotation delta
        rate = None
        try:
            rate = float(clip.get_editor_property("sampling_frame_rate").numeric_ratio) if False else None
        except Exception:
            pass
        tail=[]
        dt=1.0/120.0
        L=e["length"]
        for b in bones:
            p0=sample(clip,b,max(0.0,L-2*dt)); p1=sample(clip,b,max(0.0,L-dt)); p2=sample(clip,b,L)
            if p0 is None or p2 is None: continue
            a1=qang(p0.rotation,p1.rotation)/dt
            a2=qang(p1.rotation,p2.rotation)/dt
            tail.append((b,round(a1,1),round(a2,1)))
        tail.sort(key=lambda r:r[2],reverse=True)
        e["tail_deg_per_s"]=tail
        e["tail_max_deg_per_s"]=max((r[2] for r in tail),default=0)
    except Exception as ex:
        e["error"]=repr(ex)
    result[c["name"]]=e

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f:
    json.dump(result,f,ensure_ascii=False,indent=1)
unreal.log("QUICKCOMBAT_RECOVER_DONE2")
print("WROTE",OUT)
