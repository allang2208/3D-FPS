"""recover 段"视觉量级"测量：组件空间(画面同源)角速度 + clip→Idle 边界。

对每条剑类 clip：以 1/480s 采样末段，输出关键骨在
  (a) 父级相对局部空间  (b) 组件空间（若 API 支持）
的逐帧旋转增量(deg)与角速度(deg/s)，标出峰值位置与距末尾的时间。
同时给出"末 40ms 累计转角"，即肉眼会看到的一次跳变大小。
"""
import unreal, json, math, os

OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\visual_tail.json"
DT = 1.0/480.0
BONES = ["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l","clavicle_r","clavicle_l"]

CASES = [
    ("pommel",  "/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
    ("slash1",  "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1"),
    ("slash2",  "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash2"),
    ("thrust",  "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Thrust"),
    ("overhead","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Overhead"),
    ("idle",    "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"),
]

def qang(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))

def pose(anim,bone,t,outer):
    try: return unreal.AnimationLibrary.get_bone_pose_for_time(anim,bone,t,outer)
    except Exception: return None

# probe: does outer=True give component space? compare hand_r against idle at t=0 for two flags
res={"probe":{}}
a=unreal.load_asset("/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike")
for flag in (False,True):
    p=pose(a,"hand_r",0.92,flag)
    if p: res["probe"][str(flag)]={"loc":[round(p.translation.x,4),round(p.translation.y,4),round(p.translation.z,4)],
                                   "rot":[round(p.rotation.x,4),round(p.rotation.y,4),round(p.rotation.z,4),round(p.rotation.w,4)]}

for name,path in CASES:
    anim=unreal.load_asset(path)
    e={}
    if not anim: res[name]={"error":"missing"}; continue
    L=float(anim.get_play_length()); e["length"]=round(L,4)
    e["space"]=res["probe"]
    for outer in (False,True):
        tag="comp" if outer else "local"
        e[tag]={}
        for b in BONES:
            if pose(anim,b,L*0.5,outer) is None: continue
            t0=max(0.0,L-0.10)
            T=[];t=t0
            while t<=L+1e-9:
                T.append(min(t,L)); t+=DT
            rows=[];prev=None
            for tt in T:
                p=pose(anim,b,tt,outer)
                d=0.0
                if prev is not None: d=qang(prev.rotation,p.rotation)
                rows.append(round(math.degrees(d),4))
                prev=p
            # find peak and accumulated last-40ms rotation
            peak=max(rows) if rows else 0.0
            n40=int(0.04/DT)
            tail40=sum(rows[-n40:]) if len(rows)>=n40 else sum(rows)
            e[tag][b]={"peak_step_deg":round(peak,3),
                       "peak_deg_per_s":round(peak/DT,1),
                       "acc40ms_deg":round(tail40,3),
                       "steps":rows}
    res[name]=e

os.makedirs(os.path.dirname(OUT),exist_ok=True)
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("VISUAL_TAIL_DONE")
print("WROTE",OUT)
