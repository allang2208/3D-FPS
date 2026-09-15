from study_smd import *
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial import ConvexHull
data={c['name']:c for c in json.loads((ROOT/'motion_data.json').read_text())}
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
choices={'bayonet/draw':[8,10,12,13,14,15,16,17,18,20,22,24], 'stiletto/lookat01':[58,60,62,64,66,68,70,72,74,80,90,100]}
for name,frames in choices.items():
 c=data[name]
 for angle in [0,math.pi/2]:
  rot=np.array([[-math.cos(angle),math.sin(angle),0],[0,0,1],[math.sin(angle),math.cos(angle),0]])
  def pose(f):
   points=np.array(c['points'][f])@rot.T;parts=[]
   for part in c['parts']:
    v=(np.array(part['matrices'][f])@np.c_[part['vertices'],np.ones(len(part['vertices']))].T).T[:,:3]@rot.T;parts.append(v)
   return points,parts
  allpoints=np.concatenate([np.concatenate([pose(f)[0][2:],*pose(f)[1]]) for f in frames]);mn=allpoints.min(0);mx=allpoints.max(0);scale=min(360/(mx[0]-mn[0]),280/(mx[1]-mn[1]));center=(mn+mx)/2
  img=Image.new('RGB',(1600,1020),(24,28,35))
  for k,f in enumerate(frames):
   cell=Image.new('RGB',(400,340),(24,28,35));d=ImageDraw.Draw(cell);p,parts=pose(f)
   def xy(v):return (200+(v[0]-center[0])*scale,185-(v[1]-center[1])*scale)
   for v in parts:
    vv=np.array([xy(a) for a in v]);h=ConvexHull(vv);d.polygon([tuple(vv[j]) for j in h.vertices],fill=(175,185,193))
   for a,b in c['edges']:
    if a<2:continue
    s=c['names'][b];color=(245,175,75) if s.startswith('Finger0') or s=='Tip0' else (80,190,220) if 'Finger' in s or 'Tip' in s else (110,115,123)
    d.line([xy(p[a]),xy(p[b])],fill=color,width=5)
   for v in p[2:]:
    x,y=xy(v);d.ellipse((x-3,y-3,x+3,y+3),fill=(240,240,240))
   d.text((10,8),f'{name} F{f} {f/30:.3f}s',font=font,fill=(235,235,240))
   img.paste(cell,((k%4)*400,(k//4)*340))
  img.save(ROOT/'sheets'/(name.replace('/','_')+('_side_detail.png' if angle else '_front_detail.png')))

for name,frames in choices.items():
 weapon,action=name.split('/');ns,fs,_=read_smd(ROOT/'decompiled'/weapon/f'v_csgo_{weapon}_anims'/f'{action}.smd');nm={n:i for i,(n,p) in ns.items()}
 worlds=[world(ns,f) for f in fs];a0=worlds[frames[0]][nm['ValveBiped.Bip01_R_Forearm']][:3,:3];h0=(np.linalg.inv(worlds[frames[0]][nm['ValveBiped.Bip01_R_Forearm']])@worlds[frames[0]][nm['ValveBiped.Bip01_R_Hand']])[:3,:3]
 print(name)
 for f in frames:
  w=worlds[f];a=w[nm['ValveBiped.Bip01_R_Forearm']];h=w[nm['ValveBiped.Bip01_R_Hand']];local=np.linalg.inv(a)@h
  deg=lambda m:round(math.degrees(math.acos(float(np.clip((np.trace(m)-1)/2,-1,1)))),1)
  curls=[math.degrees(math.acos(float(np.clip(matrix(fs[f][nm['ValveBiped.Bip01_R_Finger'+str(j)+'1']])[0,0],-1,1)))) for j in range(1,5)]
  print(f,'forearm delta',deg(a0.T@a[:3,:3]),'wrist delta',deg(h0.T@local[:3,:3]),'PIP bends',np.round(curls,1))
