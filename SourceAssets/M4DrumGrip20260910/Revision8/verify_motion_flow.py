import bpy,re,json
from pathlib import Path
O=Path(__file__).parent;root=O.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision7/M4_DrumMatch_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['A_M4_DrumMatch_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def keys(path):
 t=path.read_text().split('FKey Empty[] = {')[1].split('};')[0]
 return [(float(f),float(t)*4.725) for f,t in re.findall(r'\{([\d.]+)f,\s*([\d.]+)f\}',t)]
def evaluate(ks,t,smooth):
 d=[(b[0]-a[0])/(b[1]-a[1]) for a,b in zip(ks,ks[1:])]
 slopes=[d[0]]
 for i in range(1,len(ks)-1):
  h0=ks[i][1]-ks[i-1][1];h1=ks[i+1][1]-ks[i][1]
  slopes.append(3*(h0+h1)/((2*h1+h0)/d[i-1]+(h1+2*h0)/d[i]))
 slopes.append(d[-1])
 for i in range(1,len(ks)):
  if t<=ks[i][1]:
   f0,t0=ks[i-1];f1,t1=ks[i];h=t1-t0;u=(t-t0)/h
   if not smooth:return f0+(f1-f0)*u
   return (2*u**3-3*u**2+1)*f0+(u**3-2*u**2+u)*h*slopes[i-1]+(-2*u**3+3*u**2)*f1+(u**3-u**2)*h*slopes[i]
 return ks[-1][0]
report={}
for label,path,sm in [('before',O/'previous_timing.h',False),('after',root/'Source/FPSGAME/Weapons/M4DrumReloadTiming.h',True)]:
 ks=keys(path);start=next(t for f,t in ks if f==80);end=next(t for f,t in ks if f==116)
 prev=None;streak=longest=0;speeds=[]
 for k in range(int((end-start)*240)+1):
  t=start+k/240;f=evaluate(ks,t,sm);s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  p=(r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix).translation
  if prev is not None:
   speed=(p-prev).length*240;speeds.append(speed)
   streak=streak+1/240 if speed<.01 else 0;longest=max(longest,streak)
  prev=p.copy()
 report[label]={'seat_to_strike_seconds':end-start,'longest_wrist_speed_below_1cm_s':longest,'max_speed_m_s':max(speeds)}
(O/'motion_flow.json').write_text(json.dumps(report,indent=2));print(report)
assert report['after']['longest_wrist_speed_below_1cm_s']<.1,report
