"""决定性测量：recover 末段"到终点姿态的距离"逐帧曲线。

若曲线在接近终点前先降到接近 0、又回升、再回到 0，就是"回摆/缺口"（overshoot-notch），
在画面上表现为收势末端的抽动（突然形变/切换不自然）。
同时按轴向分解最后 30ms 的旋转脉冲：swing(摆动) vs twist(绕自身轴扭转)。
"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\gap_to_end.json"
BONES=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l"]
CASES=[("pommel","/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
       ("thrust","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Thrust"),
       ("slash1","/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1")]

def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def P(a,b,t): return unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)

res={}
for name,path in CASES:
    anim=unreal.load_asset(path)
    if not anim: res[name]={"error":"missing"}; continue
    L=float(anim.get_play_length()); e={"length":round(L,4),"bones":{}}
    for b in BONES:
        pend=P(anim,b,L)
        rows=[]
        t0=max(0.0,L-0.35)
        t=t0
        while t<=L+1e-9:
            tt=min(t,L); p=P(anim,b,tt)
            rows.append([round(tt,4), round(qd(p.rotation,pend.rotation),3),
                         round((p.translation-pend.translation).length()*100,3)])
            t+=DT
        e["bones"][b]=rows
    res[name]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("GAP_DONE")
print("WROTE",OUT)
