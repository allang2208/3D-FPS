import numpy as np,wave
from pathlib import Path
root=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04/Audio");root.mkdir(exist_ok=True)
sr=48000;rng=np.random.default_rng(904)
for role,length in {"SwingLeft":2.3,"SwingRight":2.3,"Resonance":2.8,"Gaze":3.,"Claw":1.1,"Stagger":1.4,"Death":1.}.items():
 t=np.arange(round(length*sr))/sr;noise=rng.normal(0,1,len(t))
 smooth=np.convolve(noise,np.ones(21)/21,mode="same")
 y=np.zeros_like(t)
 if role=="Resonance":
  y=.12*np.sin(2*np.pi*(42*t+8*t*t))*np.minimum(t,1.1)/1.1*np.exp(-t/2)
  for pulse,hz in [(1.1,68),(1.45,91),(1.8,120)]:
   age=np.maximum(0,t-pulse);env=(t>=pulse)*(1-np.exp(-age*160))*np.exp(-age*8)
   y+=env*(.45*np.sin(2*np.pi*hz*age)+.16*np.sin(2*np.pi*hz*1.47*age)+.12*smooth)
 elif role=="Gaze":
  charge=np.minimum(t/.9,1)*(1/(1+np.exp(np.clip((t-1.23)*100,-50,50))))
  y=.18*charge*np.sin(2*np.pi*(180*t+180*t*t))
  fire=(t>=1.25)&(t<1.85);y+=fire*(.25*smooth+.18*np.sin(2*np.pi*74*t))
 elif role.startswith("Swing"):
  env=np.exp(-((t-1.02)/.18)**2);y=.5*env*smooth+.15*env*np.sin(2*np.pi*(55*t-12*t*t))
 elif role=="Claw":
  env=np.exp(-((t-.44)/.065)**2);y=env*(.45*smooth+.14*np.sin(2*np.pi*410*t))
 elif role=="Stagger":
  env=np.exp(-t*4)*(1-np.exp(-t*80));y=env*(.35*np.sin(2*np.pi*(90*t-20*t*t))+.2*smooth)
 else:
  y=np.exp(-t*3)*(1-np.exp(-t*70))*(.42*np.sin(2*np.pi*(65*t-15*t*t))+.15*smooth)
 y*=np.minimum(1,t/.008)*np.minimum(1,(length-t)/.02)
 peak=np.max(np.abs(y));y=y/max(1,peak/.72)
 with wave.open(str(root/f"S_M09_{role}.wav"),"wb") as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((y*32767).astype("<i2").tobytes())
print("M09 original cues saved: 7")
