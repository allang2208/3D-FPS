"""Static 2.4-second sample of the shipped rune shader, baked for offline icon rendering.

Uses existing runtime mask files and semantic colors; no invented emblem artwork.
The material_sources.json and wild_totem_v2.hlsl production sources define this translation.
"""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;SRC=P.parent
def sat(v):return np.clip(v,0,1)
def smooth(a,b,x):
 t=sat((x-a)/(b-a));return t*t*(3-2*t)
def make(oid,dimensions,innate=False):
 key=f'{oid}_{dimensions[1]}_{dimensions[2]}_{innate}'
 if bpy.data.images.get(key):return bpy.data.images[key]
 sources=json.loads((P/'rune_sources.json').read_text())
 data=json.loads((SRC/'MeleeRuneFade20260922/material_sources.json').read_text(encoding='utf-8'))
 group=data['spirit' if oid=='spirit_burst_rune' else 'shared']
 par={n['name']:n['value'] for n in group['nodes'] if n.get('type')=='parameter'}
 mode='erosion_rune' if oid=='spirit_burst_rune' else oid
 tex=bpy.data.images.load(sources[mode]['source'][0],check_existing=True);tex.colorspace_settings.name='Non-Color'
 tw,th=tex.size;pix=np.empty(tw*th*4,dtype=np.float32);tex.pixels.foreach_get(pix);pix=pix.reshape(th,tw,4)
 n=1024;u,v=np.meshgrid((np.arange(n)+.5)/n,1-(np.arange(n)+.5)/n)
 # v is the UE top-origin projected coordinate; Blender pixels are bottom-first.
 def sample(x,y):
  xx=sat(x)*(tw-1);yy=(1-sat(y))*(th-1)
  x0=xx.astype(int);y0=yy.astype(int);x1=np.minimum(x0+1,tw-1);y1=np.minimum(y0+1,th-1)
  fx=xx-x0;fy=yy-y0
  return ((pix[y0,x0,0]*(1-fx)+pix[y0,x1,0]*fx)*(1-fy)+(pix[y1,x0,0]*(1-fx)+pix[y1,x1,0]*fx)*fy)
 t=2.4;along=dimensions[1]+(1-v)*dimensions[2]
 glow=.75 if innate else 1.25;base=.65 if innate else .85
 if oid=='wild_rune':
  spec=json.loads((SRC/'HighlandClaymoreMeshy20260922/WildRuneTotemV2_20260922/production.json').read_text(encoding='utf-8'))
  ax,ay,aw,ah=spec['art_uv_rect'];sx=ax+v*aw;sy=ay+(1-u)*ah
  dx,dy=1.8/tw,1.8/th;value=sample(sx,sy)
  core=sat((value-.028)/.88)
  near=(sample(sx+dx,sy)+sample(sx-dx,sy)+sample(sx,sy+dy)+sample(sx,sy-dy))*.25
  far=(sample(sx+dx*2.6,sy+dy*2.6)+sample(sx-dx*2.6,sy-dy*2.6)+sample(sx+dx*2.6,sy-dy*2.6)+sample(sx-dx*2.6,sy+dy*2.6))*.25
  halo=sat((near*.72+far*.28-.028)/.88)
  slow=.5+.5*np.sin(t*1.12+along*.047+3*np.sin(along*.032));ember=sat(.5+.5*np.sin(t*.92-along*.12))**8
  pulse=.55+.19*slow+.13*ember;jaw=smooth(.68,.87,v)
  corecolor=np.array([.32,.006,.004])*base+(np.array([1,.022,.006])+(np.array([1,.055,.009])-np.array([1,.022,.006]))*ember[...,None]*.32)*glow*pulse[...,None]*(.86+.18*jaw[...,None])
  halocolor=np.array([1,.022,.006])*glow*.4*pulse[...,None]
  w=sat(core/np.maximum(core+halo*.20,.0001))
  color=halocolor*(1-w[...,None])+corecolor*w[...,None]
  alpha=sat(core*.88+halo*.145*(.76+.24*slow))*smooth(0,.018,u)*(1-smooth(.982,1,u))*smooth(0,.018,v)*(1-smooth(.982,1,v))
  peak=1.8
 else:
  sx=.3+.4*u;sy=v;dx=par.get('HaloRadiusTexels',1.8)/tw;dy=par.get('HaloRadiusTexels',1.8)/th
  core=sat(sample(sx,sy)*1.2)
  halo=(sample(sx+dx,sy)+sample(sx-dx,sy)+sample(sx,sy+dy)+sample(sx,sy-dy))*.25
  if oid=='spirit_burst_rune':
   x=(u-.5)*2.55+.012*np.sin(v*49+u*7);bands=np.zeros_like(u);aura=bands.copy();facets=bands.copy();wake=bands.copy()
   for node in range(3):
    y=(v-(.18+node*.30))*3.05+.010*np.sin(u*21+v*31)
    dist=np.maximum(0,np.sqrt(x*x+.0049)+.92*np.sqrt(y*y+.0049)-.1344)
    phase=(t*par['BurstRate']-node*.19)%1
    life=smooth(.02,.20,phase)*(1-smooth(.70,.98,phase));charge=smooth(.02,.22,phase)*(1-smooth(.28,.55,phase))
    outline=np.exp2(-2*((dist-.24)/par['EdgeSoftness'])**2);inner=np.exp2(-2*(dist/.16)**2)*charge
    facets+=inner*.55;bands+=outline*life*.13;wake+=np.exp2(-(dist/.58)**2)*life
    for echo in range(2):
     progress=sat((phase-.20-echo*.10)/(.70-echo*.05));envelope=smooth(0,.18,progress)*(1-smooth(.48,1,progress))
     radius=.18+(.76-.18)*progress;width=par['EdgeSoftness']+.075*progress
     strength=envelope*(1-progress)**.85*(.65 if echo==0 else .42)
     bands+=np.exp2(-1.7*((dist-radius)/width)**2)*strength*(.83+.17*np.sin(v*37+u*19+node*1.7))
     aura+=np.exp2(-1.5*((dist-radius)/(width*2.2))**2)*strength
   breath=.5+.5*np.sin(t*1.35-v*5)
   body=(core*.22+halo*.78)*(.10+.14*breath+.12*sat(wake))+bands+facets
   aura=(aura+halo*.05)*par['BurstHalo']
   alpha=(1-np.exp2(-1.8*(body+aura*.22)))*par['SpiritOpacity']
   w=sat(facets/np.maximum(body,.0001))*.5
   tint=np.array(par['BurstColor'][:3])*(1-w[...,None])+np.array(par['InnerColor'][:3])*w[...,None]
   w=.08*sat(aura/np.maximum(body+aura,.0001))
   tint=tint*(1-w[...,None])+np.array(par['AccentColor'][:3])*w[...,None]
   color=tint*par['SpiritBrightness']*(.62+.38*sat(body))[...,None]
   alpha*=par['RuneOpacity']*smooth(0,.09,u)*(1-smooth(.91,1,u))*smooth(.02,.12,v)*(1-smooth(.87,.985,v));peak=1.15
  else:
   prefix={'resonance_rune':'Resonance','erosion_rune':'Erosion','conduction_rune':'Conduction'}[oid]
   pulse=.8+.2*np.sin(t*2.2-along*.024) if oid=='resonance_rune' else .68+.2*np.sin(t*3.6+along*.17)+.12*np.sin(t*8.4-along*.08) if oid=='erosion_rune' else .60+.4*(.5+.5*np.sin(along*.17-t*2.6))**3
   ct=np.array(par[prefix+'CoreColor'][:3]);gt=np.array(par[prefix+'GlowColor'][:3]);ho=par['HaloOpacity']
   alpha=sat(core*par['RuneOpacity']+halo*ho);w=sat(core/np.maximum(core+halo*ho,.0001))
   color=(gt*glow*.65*pulse[...,None])*(1-w[...,None])+(ct*base+gt*glow*pulse[...,None])*w[...,None];peak=par['EmissionPeak']
 color*=np.minimum(1,peak/np.maximum(color.max(axis=2),.0001))[...,None]
 rgba=np.concatenate([color,alpha[...,None]],axis=2).astype(np.float32)
 image=bpy.data.images.new(key,width=n,height=n,alpha=True,float_buffer=True);image.colorspace_settings.name='Non-Color'
 image.pixels.foreach_set(rgba.ravel());image.pack()
 return image
