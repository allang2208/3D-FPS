"""Prepare slot recipes and UV mask destinations from current runtime sources."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/'A762'))
from seated import read_geometry
materials=json.loads((HERE/'Input'/'materials.json').read_text(encoding='utf-8'))
plan={}
for key,entry in materials.items():
 h,pos,tri,ids,uv,nrm=read_geometry(HERE/'Input'/(key+'.bin'))
 xyz=pos[tri].astype(float)
 area=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)*.5
 U=uv.astype(float); e1=U[:,1]-U[:,0];e2=U[:,2]-U[:,0]
 ua=np.abs(e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0])*.5
 specs={}
 for i,s in enumerate(entry['slots']):
  name=s['slot'];m=s['material'];sel=ids==i
  spec={'index':i,'before':m['path'],'action':'preset','preset':'CleanSatinSteel','scalars':{},'vectors':{}}
  if key=='ASH12':
   if not name.startswith('M_ASH12_'):spec.update(action='keep',reason='V7 hands')
   else:
    spec['regional']=True
    if 'Magazine' in name:spec['preset']='CleanPolymer'
    elif 'Sights' in name:spec['preset']='CleanAnodized'
    if name.endswith('Upper'):
     spec['scalars']['RegionPolymerRoughness']=.70
     spec['vectors']['RegionPolymerColor']=[.0103,.0103,.0103]
    if name.endswith('Flash_Hider'):spec['scalars']['Roughness']=.46
  elif any(x in name for x in ('Glass','Reticle','Optic_')) or name.startswith('M_Tactical_'):
   spec.update(action='keep',reason='protected optical / marking / emitter blend')
  elif name=='ASH12Tac_Inner':spec.update(action='keep',reason='muzzle interior')
  elif name=='ASH12Tac_Band':spec.update(action='keep',reason='intentional bronze band')
  elif key=='ext_mag':
   spec['preset']='CleanPolymer'
   if name=='M_ASH12_Magazine':spec['seam_normal']=True
  elif 'Polymer' in name or name=='ASH12Cheek_Shell':spec['preset']='CleanPolymer'
  elif 'SoftPad' in name:spec['preset']='Rubber'
  elif name in ('ASH_OpticShoe','ASH_BrakeMount'):spec['preset']='CleanAnodized'
  spec['normal']=next((t['path'] for t in m['textures'] if 'NORMALMAP' in t['compression']),None)
  # The old procedural coating samples its micro normal at 12x UV0; preserve that scale.
  if spec['normal'] and 'AttachmentCoat_NormalDX' in spec['normal']:spec['normal_tiling']=12.0
  if sel.any():
   part=U[sel];lo=part.min(axis=(0,1));hi=part.max(axis=(0,1))
   image=Image.new('1',(1024,1024));draw=ImageDraw.Draw(image)
   for t in part:draw.polygon([tuple(x*1023) for x in t],fill=1)
   covered=float(np.asarray(image).mean())
   a=float(area[sel].sum());u=float(ua[sel].sum());ratio=u/max(covered,1e-9)
   spec['uv']={'area_cm2':round(a,3),'uv_per_cm':float(np.sqrt(u/max(a,1e-9))),
     'bounds':[*lo.tolist(),*hi.tolist()],'overlap_ratio':ratio}
   unique=bool(lo.min()>=-1e-3 and hi.max()<=1.001 and ratio<=1.15)
   spec['mask']='bake' if unique else 'neutral'
   spec['mask_name']='T_ASH12_WS_'+key+'_'+name.removeprefix('M_ASH12_').removeprefix('ASH_')
   spec['resolution']=2048 if a>450 else 1024
  else:spec.update(action='keep',reason='empty slot')
  if key=='ASH12' and spec['action']=='preset':
   spec.update(mask='bake',mask_name='T_ASH12_WS_Body',resolution=4096,mask_uv=1)
  specs[name]=spec
  print(key,name,spec['action'],spec.get('preset'),spec.get('mask'),round(spec.get('uv',{}).get('overlap_ratio',0),2),flush=True)
 plan[key]={'path':entry['path'],'slots':specs}
(HERE/'slot_plan.json').write_text(json.dumps(plan,indent=1),encoding='utf-8')
