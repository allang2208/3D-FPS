"""Slot recipes from current SVD sources. Production UV allocation, no game tests."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/'A762'))
from seated import read_geometry
materials=json.loads((HERE/'Input/materials.json').read_text())
graphs=json.loads((HERE/'Input/effective.json').read_text())['materials']
plan={}
for key,entry in materials.items():
 h,pos,tri,ids,uv,nrm=read_geometry(HERE/'Input'/(key+'.bin'))
 xyz=pos[tri].astype(float);area=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)*.5
 U=uv.astype(float);e1=U[:,1]-U[:,0];e2=U[:,2]-U[:,0];ua=np.abs(e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0])*.5
 specs={}
 for i,s in enumerate(entry['slots']):
  name=s['slot'];m=s['material'];g=graphs[m['path']];sel=ids==i
  eligible=any('matte' in c['description'].lower() and c['description'].endswith('ROUGHNESS') for c in g['custom'])
  reason='original polymer / rubber / interior / hands'
  if key in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring') or key in ('flashlight','laser') and name.endswith('_0'):
   eligible=False;reason='optical, reticle or emitter housing retains authored mixed response'
  if key=='titanium_brake':eligible=False;reason='authored titanium coloration and interior'
  if 'BLEND_OPAQUE' not in g['blend']:eligible=False;reason='optical glass or masked surface'
  if not sel.any():eligible=False;reason='empty slot'
  spec={'index':i,'before':m['path'],'source_base':g['base'],'action':'preset' if eligible else 'keep','preset':'CleanSatinSteel','scalars':{},'vectors':{}}
  if not eligible:spec['reason']=reason
  if any(x in name for x in ('Mount','AdapterSteel','InterfaceSteel')) or key in ('optic_bridge','suppressor','tactical_suppressor','brake'):
   spec['preset']='CleanAnodized'
  if 'BoltCarrier' in name:spec['scalars']['Roughness']=.34
  elif 'ChargingHandle' in name:spec['scalars']['Roughness']=.38
  elif 'Fastener' in name:
   spec['vectors']['FinishColor']=[.042,.043,.045];spec['scalars']['Roughness']=.38
  elif 'Recess' in name:
   spec['vectors']['FinishColor']=[.012,.013,.014];spec['scalars'].update(Roughness=.52,EdgeWear=.02,EdgeHighlight=.04)
  if sel.any():
   part=U[sel];lo=part.min(axis=(0,1));hi=part.max(axis=(0,1))
   raster=Image.new('1',(1024,1024));draw=ImageDraw.Draw(raster)
   for t in part:draw.polygon([tuple(x*1023) for x in t],fill=1)
   covered=float(np.asarray(raster).mean());a=float(area[sel].sum());u=float(ua[sel].sum());ratio=u/max(covered,1e-9)
   spec['uv']={'area_cm2':round(a,3),'uv_per_cm':float(np.sqrt(u/max(a,1e-9))),'bounds':[*lo.tolist(),*hi.tolist()],'overlap_ratio':ratio}
   unique=bool(lo.min()>=-1e-3 and hi.max()<=1.001 and ratio<=1.15 and u>1e-4 and covered>1e-4)
   spec.update(mask='bake' if unique else 'neutral',mask_name='T_SVD_WS_'+key+'_'+name, resolution=2048 if a>450 else 1024 if a>12 else 512)
  if key=='SVD' and eligible:spec.update(mask='bake',mask_name='T_SVD_WS_Body',resolution=4096,mask_uv=1)
  specs[name]=spec
  if eligible:print(key,name,spec['preset'],spec.get('mask'),round(spec.get('uv',{}).get('overlap_ratio',0),2),flush=True)
 plan[key]={'path':entry['path'],'slots':specs}
(HERE/'slot_plan.json').write_text(json.dumps(plan,indent=1))
