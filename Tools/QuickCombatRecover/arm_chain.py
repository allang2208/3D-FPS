"""组件空间手臂链运动学：把 recover 末段的手臂"甩动/复位"量出来。

用 find_bone_path_to_root 组装组件空间变换（Child_abs = Child_local * Parent_abs）。
对每根关键骨输出：
  - 组件空间角速度(deg/s) 逐帧，末段
  - 最后 40ms / 100ms 的累计转角(deg)
  - 肘（lowerarm 原点）位置的最后 40ms 位移(cm)
并输出峰值时刻。
"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\arm_chain.json"
BONES=["hand_r","lowerarm_r","upperarm_r","clavicle_r","hand_l","lowerarm_l","upperarm_l","clavicle_l"]
CASES=[("pommel","/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
       ("slash1","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1"),
       ("idle","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle")]

def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def P(a,b,t): return unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)

def chain_names(anim,bone):
    try:
        path=unreal.AnimationLibrary.find_bone_path_to_root(anim,bone)
        return [str(n) for n in path]
    except Exception as e:
        return None

def comp_pose(anim,bone,t):
    names=chain_names(anim,bone)
    if not names: return None
    # path likely root..bone; compose local transforms
    acc=None
    for n in names:
        p=P(anim,n,t)
        if p is None: return None
        acc = p if acc is None else p.multiply(acc)
    return acc

res={}
for name,path in CASES:
    anim=unreal.load_asset(path)
    if not anim: res[name]={"error":"missing"}; continue
    L=float(anim.get_play_length()); e={"length":round(L,4),
        "path_sample":chain_names(anim,"hand_r"),"bones":{}}
    t0=max(0.0,L-0.30)
    for b in BONES:
        rows=[];prev=None
        t=t0
        while t<=L+1e-9:
            tt=min(t,L); c=comp_pose(anim,b,tt)
            if c is None: break
            ang=0.0; dloc=0.0
            if prev is not None:
                ang=qd(prev.rotation,c.rotation)/DT
                dloc=(c.translation-prev.translation).length()*100.0/DT
            rows.append({"t":round(tt,4),"w":round(ang,1),"v":round(dloc,1),"loc":[round(x*100,3) for x in (c.translation.x,c.translation.y,c.translation.z)]})
            prev=c; t+=DT
        if not rows: continue
        ws=[r["w"] for r in rows]
        peak=max(ws); pt=rows[ws.index(peak)]["t"]
        n40=int(0.04/DT); n100=int(0.10/DT)
        # accumulated angle in last 40ms/100ms = sum of steps; approximate with mean speed * dt
        acc40=sum(ws[-n40:])*DT
        acc100=sum(ws[-n100:])*DT
        e["bones"][b]={"peak_deg_per_s":round(peak,0),"peak_at":pt,
                       "end_speed_deg_per_s":ws[-1],
                       "acc40ms_deg":round(acc40,2),"acc100ms_deg":round(acc100,2),
                       "end_pos_cm":rows[-1]["loc"],"rows":rows}
    res[name]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("ARM_CHAIN_DONE")
print("WROTE",OUT)
