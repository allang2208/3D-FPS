"""Analytic high-yarn surface projection and native sweater UV authoring."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterKnit20260929';OLD=P/'SourceAssets/ChainmailInterlace20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def png(p,a):
 p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(p)
def textures():
 size=2048;tile=1.92;pitch=.24;radius=.036
 # Periodic bent yarn loops: legs, crown and rear crossover in centimetres.
 controls=np.array([[-.40,.48,.2],[-.32,.03,.75],[-.14,-.38,.9],[0,-.47,.8],[.14,-.38,.9],[.32,.03,.75],[.40,.48,.2],[.18,.67,-.3],[0,.43,-.6],[-.18,.67,-.3],[-.40,.48,.2]])
 spline=CubicSpline(np.arange(len(controls)),controls,bc_type='periodic')
 curve=spline(np.linspace(0,len(controls)-1,160,endpoint=False));curve[:,:2]*=pitch;curve[:,2]*=.030
 paths=[]
 for row in range(8):
  for col in range(8):
   points=curve.copy();points[:,0]+=(col+.5)*pitch;points[:,1]+=(row+.5)*pitch
   points[:,2]+=.05+.002*np.sin(col*1.7+row*.8);paths.append(points)
 yy,xx=np.meshgrid((np.arange(size)+.5)*tile/size,(np.arange(size)+.5)*tile/size,indexing='ij')
 report={}
 for family in ['Knit','Rib']:
  h=np.full((size,size),-.010,dtype=np.float32)
  source=[];rpx=int(np.ceil(radius*size/tile));offset=np.arange(-rpx,rpx+1)
  for points in paths:
   points=points.copy()
   if family=='Rib':points[:,2]+=.027*np.cos(points[:,0]/pitch*np.pi)
   source.append(points)
   for x,y,z in points:
    ix=np.floor(x*size/tile).astype(int)+offset;iy=np.floor(y*size/tile).astype(int)+offset
    dx=(ix+.5)*tile/size-x;dy=(iy+.5)*tile/size-y
    d=radius*radius-dy[:,None]**2-dx[None,:]**2
    top=np.where(d>0,z+np.sqrt(np.maximum(d,0)),-1.)
    rows=iy%size;cols=ix%size;h[np.ix_(rows,cols)]=np.maximum(h[np.ix_(rows,cols)],top)
  # Short twisted fibre field on the same projected high surface, not colour noise.
  yarn=np.clip((h+.01)/.05,0,1)
  fibre=.0011*np.sin(xx*2*np.pi/.010+3*np.sin(yy*2*np.pi/.026))*np.sin(yy*2*np.pi/.007)
  h=gaussian_filter(h,.55,mode='wrap')+fibre*yarn
  dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))/(2*tile/size)
  dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))/(2*tile/size)
  normal=np.stack([-dx,-dy,np.ones_like(h)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
  variation=.94+.04*np.sin(xx*2*np.pi/tile*3+np.sin(yy*2*np.pi/tile*2))+.02*np.sin(yy*2*np.pi/.014)
  bc=np.stack([variation*.94,variation*.96,variation],axis=-1)
  cavity=np.clip((h+.01)/.075,0,1);ao=.55+.45*cavity
  rough=np.clip(.91-.07*cavity+.025*np.sin(xx*2*np.pi/.010),.80,.97)
  orm=np.stack([ao,rough,np.zeros_like(h)],axis=-1)
  relief=np.stack([np.clip((h+.015)/.14,0,1),.65+.25*yarn,np.ones_like(h)],axis=-1)
  folder=R/'Textures'/family
  # Rows are UV-v increasing; PNG stores the upper row first.
  for channel,a in [('BaseColor',bc),('Normal',normal*.5+.5),('ORM',orm),('Relief',relief)]:png(folder/(channel+'.png'),np.flipud(a))
  np.savez_compressed(R/(family+'_high_surface.npz'),height=h,paths=np.array(source),tile_cm=tile,radius_cm=radius)
  report[family]=dict(stitches=64,centerline_samples=160,yarn_diameter_mm=radius*20,tile_cm=tile,resolution=size,normal='OpenGL',bake='Orthographic max-surface projection of yarn tubes plus shared micro-fibre height field')
 write(R/'surface-production.json',report)

def geometry():
 c=read(P/'Content/ColdSteelData/modular_outfits.json');items=read(P/'Content/ColdSteelData/items.json')
 keys=['ue_field_sweater','ue_field_sweater_charcoal'];write(R/'before.json',dict(recipes={k:c['items'][k] for k in keys},items={k:items[k] for k in keys}))
 metadata={v['profile']:v for v in read(OLD/'manifest.json')};records=[]
 for name,source in c['items'][keys[0]]['rig_meshes'].items():
  original_name=name if name in metadata else next(k for k,v in metadata.items() if v['source']==source)
  entry=metadata[original_name];data=read(OLD/'Authored'/(original_name+'.json'))
  data['profile']=name
  if data.get('binding_source',data.get('source'))!=source:raise RuntimeError('Current sweater source differs '+name)
  count=entry['details']['original_triangles'];faces=data['triangles'][:count];used=sorted({v for f in faces for v in f});remap={v:i for i,v in enumerate(used)}
  data['positions']=[data['positions'][v] for v in used];data['weights']=[data['weights'][v] for v in used]
  data['triangles']=[[remap[v] for v in f] for f in faces];data['normals']=data['normals'][:count];data['uv']=data['uv'][:count];slots=[0]*count
  if name!='Body':
   # Native sleeve cuffs share the transported M4 topology. Use its coordinate
   # classification rather than recalculating a cuff plane in a bent native bind.
   master=read(OLD/'Authored/M4.json');mp=np.asarray(master['positions']);mf=master['triangles'][:metadata['M4']['details']['original_triangles']]
   sides={s for s in ['l','r'] if any(sum(v for k,v in w.items() if k.endswith('_'+s))>.7 for w in data['weights'])}
   master_faces=[i for i,f in enumerate(mf) if len(sides)==2 or all(mp[v,0]<0 if 'l' in sides else mp[v,0]>0 for v in f)]
   if len(master_faces)!=count:raise RuntimeError('Cuff face mapping changed '+name)
   for fi,mi in enumerate(master_faces):
    mid=mp[mf[mi]].mean(0);side='l' if mid[0]<0 else 'r';w=np.array(master['bones']['hand_'+side]['position']);e=np.array(master['bones']['lowerarm_'+side]['position']);axis=(w-e)/np.linalg.norm(w-e)
    t=np.dot(mid-w,axis)
    slots[fi]=2 if master['triangle_materials'][mi]==2 else (1 if t>-7.0 else 0)
  data['triangle_materials']=slots;data['contract']='Current fitted sweater shape/weights; metric knit UV and ribbed cuff surfaces only'
  write(R/'Authored'/(name+'.json'),data);records.append(dict(profile=name,source=source,triangles=count))
 write(R/'manifest.json',records);print('SWEATER_NATIVE_AUTHORED',len(records),flush=True)
if __name__=='__main__':
 R.mkdir(parents=True,exist_ok=True);geometry();textures();print('SWEATER_HIGH_SURFACE_BAKED',flush=True)
