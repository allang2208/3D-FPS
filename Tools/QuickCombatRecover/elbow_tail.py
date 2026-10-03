"""recover 末段肘部形态测量：找"突然形变"落在哪条通道。

对每条 clip 在末段以 480Hz 记录（组件空间）：
  - 肘弯曲偏离(deg)：向量(肘-肩) 与 (腕-肘) 的夹角（90 = 直角，越大越直）
  - 肘绕"肩-腕轴"的方位角(deg)：若翻转即为肘面跳变
  - 腕相对肘的距离(cm)
  - 每帧变化量，标出突变帧
"""
import unreal, json, math, os
DT=1.0/480.0
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\elbow_tail.json"
CASES=[
 ("pommel","/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike"),
 ("pistol715","/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat"),
 ("rifle_base","/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base"),
]
def P(a,b,t): return unreal.AnimationLibrary.get_bone_pose_for_time(a,b,t,False)
def comp(a,bone,t):
    path=[str(n) for n in unreal.AnimationLibrary.find_bone_path_to_root(a,bone)]
    acc=None
    for n in reversed(path):
        p=P(a,n,t)
        if p is None: return None
        acc = p if acc is None else p.multiply(acc)
    return acc

def measure(a,side,t):
    A=comp(a,f'upperarm_{side}',t); E=comp(a,f'lowerarm_{side}',t); H=comp(a,f'hand_{side}',t)
    if A is None or E is None or H is None: return None
    a0=A.translation; e=E.translation; h=H.translation
    ua=e-a0; fa=h-e
    if ua.length()<1e-6 or fa.length()<1e-6: return None
    ua=ua.normal(); fa=fa.normal()
    bend=math.degrees(math.acos(max(-1,min(1,ua.dot(fa)))))
    # azim: elbow offset around shoulder-wrist axis
    axis=(h-a0).normal()
    n=ua-axis*ua.dot(axis)
    if n.length()<1e-6: azim=0.0
    else:
        n=n.normal()
        # reference plane from world up
        up=unreal.Vector(0,0,1)
        ref=up-axis*up.dot(axis)
        if ref.length()<1e-6: ref=unreal.Vector(0,1,0)
        ref=ref.normal()
        azim=math.degrees(math.atan2(axis.cross(ref).dot(n),ref.dot(n)))
    return bend,azim,(h-e).length()*100,(e-a0).length()*100

res={}
for name,path in CASES:
    a=unreal.load_asset(path)
    if not a: res[name]={"error":"missing"};continue
    L=float(a.get_play_length()); e={"length":round(L,4),"sides":{}}
    for side in ('l','r'):
        rows=[]
        prev=None
        t=max(0.0,L-0.60)
        while t<=L+1e-9:
            tt=min(t,L); m=measure(a,side,tt)
            if m is None: break
            bend,azim,fl,ul=m
            dbend=dazim=0.0
            if prev is not None:
                dbend=bend-prev[0]; dazim=azim-prev[1]
                if dazim>180: dazim-=360
                if dazim<-180: dazim+=360
            rows.append({"t":round(tt,4),"bend":round(bend,2),"azim":round(azim,2),
                         "dbend":round(dbend,3),"dazim":round(dazim,3),
                         "fore_cm":round(fl,2),"upper_cm":round(ul,2)})
            prev=(bend,azim); t+=DT
        e["sides"][side]=rows
    res[name]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
unreal.log("ELBOW_DONE")
print("WROTE",OUT)
