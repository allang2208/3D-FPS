import unreal, json, math, os
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\raw_tail.json"
DT=1.0/480.0
def qang(a,b):
    d=abs(a.w*b.w+a.x*b.x+a.y*b.y+a.z*b.z); d=max(-1.0,min(1.0,d))
    return math.degrees(2.0*math.acos(d))
def get(anim,b,t):
    try: return unreal.AnimationLibrary.get_bone_pose_for_time(anim,b,t,False)
    except Exception: return None
cases=[
 dict(name="sword_pommel",clip="/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",
      bones=["hand_r","hand_l","lowerarm_r","lowerarm_l","upperarm_r","upperarm_l","lowerarm_twist_01_l","lowerarm_twist_01_r"],
      win=(1.20,1.60)),
]
res={}
for c in cases:
    a=unreal.load_asset(c["clip"]); L=float(a.get_play_length())
    e={"length":L,"win":c["win"],"bones":{}}
    for b in c["bones"]:
        T=[];t=c["win"][0]
        while t<=c["win"][1]+1e-9:
            T.append(round(t,6)); t+=DT
        rows=[];prev=None
        for tt in T:
            p=get(a,b,min(tt,L))
            if p is None: continue
            v=0.0; ang=0.0; loc=None
            if prev is not None:
                ang=qang(prev.rotation,p.rotation); v=ang/DT
            rows.append(dict(t=round(tt,4),deg=round(ang,3),v=round(v,1),
                             loc=[round(x*100,3) for x in (p.translation.x,p.translation.y,p.translation.z)]))
            prev=p
        # keep all rows but trim print size: store rounded
        e["bones"][b]=rows
    res[c["name"]]=e
os.makedirs(os.path.dirname(OUT),exist_ok=True)
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("RAWTAIL_DONE")
print("WROTE",OUT)
