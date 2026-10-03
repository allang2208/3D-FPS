"""决定性测量：接近战武器快速近战(剑配重锤) recover 段的逐帧几何。

修正单位（上一次脚本把度数又乘了一次 57.3），并补充：
  - 逐帧角增量(deg) 与角速度(deg/s) @480Hz
  - 肘/腕的组件空间位置逐帧位移(cm) —— "形变"若来自肘面翻转，位置不动而角速度尖峰
  - 列出所有 >0.8deg/帧（=384deg/s）的孤立尖峰及其时刻
"""
import unreal, json, math, os

OUT = r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\definitive.json"
DT = 1.0/480.0
BONES = ["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l"]

CASES = [
    ("pommel", "/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
    ("slash1", "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1"),
    ("thrust", "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Thrust"),
    ("idle",   "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"),
]

def qang_deg(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))

def pose(anim,bone,t):
    return unreal.AnimationLibrary.get_bone_pose_for_time(anim,bone,t,False)

res={}
for name,path in CASES:
    anim=unreal.load_asset(path)
    if not anim: res[name]={"error":"missing"};continue
    L=float(anim.get_play_length())
    e={"length":round(L,4),"bones":{}}
    n=int(round(L/DT))
    for b in BONES:
        rows=[]
        prev=None
        for i in range(n+1):
            t=min(i*DT,L)
            p=pose(anim,b,t)
            if p is None: continue
            ang=0.0; dloc=0.0
            if prev is not None:
                ang=qang_deg(prev.rotation,p.rotation)
                dloc=(p.translation-prev.translation).length()*100.0
            rows.append({"t":round(t,4),"deg":round(ang,4),"cm":round(dloc,4),
                         "loc":[round(p.translation.x*100,3),round(p.translation.y*100,3),round(p.translation.z*100,3)]})
            prev=p
        e["bones"][b]=rows
    res[name]=e

# analyze: isolated spikes (deg > 0.8 and neighbors < 0.4)
report={}
for name,e in res.items():
    if "bones" not in e: continue
    rep={"length":e["length"],"spikes":[],"recover_window":{}}
    for b,rows in e["bones"].items():
        for i in range(1,len(rows)-1):
            v=rows[i]["deg"]
            if v>0.8 and rows[i-1]["deg"]<0.4 and rows[i+1]["deg"]<0.4:
                rep["spikes"].append({"bone":b,"t":rows[i]["t"],"deg":round(v,3),
                                      "deg_per_s":round(v/DT,0),
                                      "prev":rows[i-1]["deg"],"next":rows[i+1]["deg"]})
    # recover window summary: last 0.30 s
    w0=max(0,e["length"]-0.30)
    for b,rows in e["bones"].items():
        sel=[r for r in rows if r["t"]>=w0]
        tot=sum(r["deg"] for r in sel)
        mx=max((r["deg"] for r in sel),default=0)
        rep["recover_window"][b]={"total_deg":round(tot,2),"max_step_deg":round(mx,3),
                                  "max_step_deg_per_s":round(mx/DT,0)}
    report[name]=rep

json.dump({"raw":res,"report":report},open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("DEFINITIVE_DONE")
print("WROTE",OUT)
