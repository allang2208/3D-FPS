"""Per-frame tail detail of the shipped (fixed) sword pommel clip."""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\v47_tail_detail.json"
anim=unreal.load_asset("/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike")
L=float(anim.get_play_length())
BONES=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l"]
def qd(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
res={"length":L,"bones":{}}
for b in BONES:
    rows=[];prev=None;t=1.38
    while t<=L+1e-9:
        tt=min(t,L); p=unreal.AnimationLibrary.get_bone_pose_for_time(anim,b,tt,False)
        d=0.0
        if prev is not None: d=qd(prev.rotation,p.rotation)
        rows.append([round(tt,5),round(d,4)])
        prev=p; t+=DT
    res["bones"][b]=rows
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("V47_TAIL_DETAIL_DONE")
print("WROTE",OUT)
