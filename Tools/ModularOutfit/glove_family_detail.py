"""Shared production definition for the three companion gloves, September 2026.

Keep the published silhouettes, bone weights, UV atlases and gameplay contracts.
High-poly sculpts are baking sources; they never replace the equipped mesh.
"""
import json
from pathlib import Path
import numpy as np

P=Path(__file__).resolve().parents[2]
R=P/'SourceAssets/GloveCompanionDetail20260928'
DEST='/Game/Characters/ModularOutfit20260924/GloveCompanionDetail20260928'
FAMILIES={
 'Fingerless':dict(item='ue_field_gloves',groups=['Shared','Body','DW715_l'],source=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1',
                   icon_source=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1/Editable/TailoredFingerless_Pickup.blend'),
 'Tactical':dict(item='ue_original_gloves',groups=['M4','Body'],source=P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV2',
                 icon_source=P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV2/OriginalLeatherV2_Icon.blend'),
 'Steel':dict(item='ue_steel_gauntlets',groups=['Plates','Mail'],source=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1',
              icon_source=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1/SteelGauntlet_Icon.blend')}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def gauss(x,w):return np.exp(-(x/w)**2)

def stitch(distance,arc,pitch=.27):
 s=np.mod(arc,pitch)-pitch*.5
 length=1-smooth(pitch*.23,pitch*.32,abs(s))
 thread=gauss(distance,.023)*length
 holes=gauss(distance,.024)*gauss(abs(s)-pitch*.31,.019)
 fine=.017*thread*(.90+.10*np.sin(arc*87))-.013*holes-.003*gauss(distance,.06)
 rub=gauss(abs(distance)-.071,.033)*(.55+.45*length)
 return fine,thread,holes,rub

def pattern(x,y,palm,tactical=False):
 from tailored_fingerless_candidate import tailoring
 relief,oldfine,oldthread,panel,polish=tailoring(x,y,palm)
 back=1-palm;end=smooth(-1.,-.4,y)*(1-smooth(6.8,7.5,y))
 gus=(x-(-1.62-.047*(y-3.6)**2))/np.sqrt(1+(.094*(y-3.6))**2)
 yoke=(y-(7.25-.045*x*x))/np.sqrt(1+(.09*x)**2)
 fine=np.zeros_like(x);thread=np.zeros_like(x);holes=np.zeros_like(x);rub=np.zeros_like(x)
 for d,arc,mask in [(gus-.23,y,end),(gus+.19,y,end*.50),(yoke-.23,x,back*end)]:
  f,t,h,r=stitch(d,arc);fine+=f*mask;thread+=t*mask;holes+=h*mask;rub+=r*mask
 # A shallow closed padded panel stays on the back of the tactical hand.
 if tactical:
  rr=(abs((x+.05)/3.0)**4+abs((y-4.2)/2.5)**4)**.25
  sd=(rr-1)*2.5;panel_mask=(1-smooth(-.08,.06,sd))*back
  fine+=.018*panel_mask
  f,t,h,r=stitch(sd+.13,np.arctan2((y-4.2)/2.5,(x+.05)/3.)*2.8,.29)
  fine+=f*back;thread+=t*back;holes+=h*back;rub+=r*back
  panel*=1-.11*panel_mask
 # Preserve the accepted wrist tab and folds; replace its fine sewn surface.
 fine+=oldfine*.35+.0025*np.sin(x*31+y*5)*np.sin(y*27-x*3)*gauss(y-2,4)
 thread=np.clip(thread+oldthread*.35,0,1)
 wear=np.clip(rub*.48+polish*.2,0,.65)
 return dict(fine=fine,thread=thread,holes=np.clip(holes,0,1),wear=wear,panel=panel,polish=polish)

def surface_fields(x,y,palm,edge,arc,inside,tactical):
 a=pattern(x,y,palm,tactical);f,t,h,r=stitch(edge-.28,arc,.27)
 fade=1-inside
 a['fine']=(a['fine']+f)*fade*smooth(.035,.14,edge)
 a['thread']=np.clip(a['thread']+t,0,1)*fade
 a['holes']=np.clip(a['holes']+h,0,1)*fade
 a['wear']=np.clip(a['wear']+r*.3,0,1)*fade
 a['fuzz']=np.clip(a['thread']*.6+gauss(edge-.06,.065)*.5,0,1)*fade
 return a

def prepare():
 cfg=read(P/'Content/ColdSteelData/modular_outfits.json');items=read(P/'Content/ColdSteelData/items.json')
 for family,spec in FAMILIES.items():
  folder=R/family;folder.mkdir(parents=True,exist_ok=True)
  before=folder/'before.json'
  if not before.exists():write(before,dict(item=items[spec['item']],recipe=cfg['items'][spec['item']]))
  for sub in ['Textures','Editable','Saved','Authoring','Baked']: (folder/sub).mkdir(exist_ok=True)
 write(R/'production-plan.json',dict(items=[s['item'] for s in FAMILIES.values()],
  pipeline='actual subdivided and displaced high mesh -> native UV bake -> bounded leather POM / solid metal PBR -> native mesh duplicate and per-slot binding',
  preserve=['native geometry','native skin weights','all existing animations','armor values and speed modifiers','black V4 glove'],
  icon_contract='single empty glove, production PBR, transparent 320x320, 91 percent fill',runtime_tested=False))

if __name__=='__main__':prepare()
