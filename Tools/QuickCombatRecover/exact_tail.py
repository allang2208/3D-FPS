"""逐帧打印 sword pommel 末段 + 相关边界比较。"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\exact_tail.json"
BONES=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l","clavicle_r","clavicle_l"]

def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def P(a,b,t):
    return unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)

res={}
anim=unreal.load_asset("/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike")
idle=unreal.load_asset("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle")
walk=unreal.load_asset("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Walk")
res["lengths"]={"pommel":float(anim.get_play_length()),"idle":float(idle.get_play_length()),
                "walk":float(walk.get_play_length()) if walk else None}
# 1) exact tail 1.50-1.60 per frame
tail={}
L=float(anim.get_play_length())
for b in BONES:
    rows=[];prev=None
    i0=int(1.50/DT);i1=int(round(L/DT))
    for i in range(i0,i1+1):
        t=min(i*DT,L);p=P(anim,b,t)
        d=0.0
        if prev is not None: d=qd(prev.rotation,p.rotation)
        rows.append([round(t,4),round(d,4)])
        prev=p
    tail[b]=rows
res["tail_1.50_1.60"]=tail
# 2) idle pose variation over loop (sample every 0.1s): max delta vs frame0
var={}
for b in BONES:
    base=P(idle,b,0.0);mx=0;mxt=0
    t=0.0
    while t<float(idle.get_play_length()):
        p=P(idle,b,t)
        d=qd(base.rotation,p.rotation)
        if d>mx:mx=d;mxt=t
        t+=0.1
    var[b]={"max_drot_deg":round(mx,3),"at":round(mxt,3)}
res["idle_variation"]=var
# 3) boundary comparisons: pommel end vs idle0 / walk0
cmp={}
for b in BONES:
    pe=P(anim,b,L)
    for name,clip in (("idle0",idle),("walk0",walk)):
        if clip is None: continue
        p0=P(clip,b,0.0)
        cmp.setdefault(name,[]).append({"bone":b,
            "dpos_cm":round((pe.translation-p0.translation).length()*100,3),
            "drot_deg":round(qd(pe.rotation,p0.rotation),3)})
res["end_vs"]=cmp
# 4) pommel start (0) vs idle random phases: how big is entry snap if idle at phase p?
en={}
for b in BONES:
    ps=P(anim,b,0.0)
    mx=0;mxt=0
    t=0.0
    while t<float(idle.get_play_length()):
        p=P(idle,b,t)
        d=qd(ps.rotation,p.rotation)
        if d>mx:mx=d;mxt=t
        t+=0.1
    en[b]={"max_drot_deg":round(mx,3),"at":round(mxt,3)}
res["start_vs_idle_phase"]=en
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("EXACT_TAIL_DONE")
print("WROTE",OUT)
