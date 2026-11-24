"""West smith's shed, in the same metre coordinates as the published village ground."""
import json
import math
from pathlib import Path

ORIGIN=(-43.90,-9.00)
YARD_GRAVEL=[(-1.91,-2.84,7),(-2.01,-2.71,5),(-1.95,-.27,6),(-1.84,-.04,4),
             (-1.99,1.69,8),(-2.04,1.80,5),(.21,-3.56,6),(1.59,-3.49,4)]
# A narrow margin clears overhanging leaves next to the roof and its open north entrance.
_plan=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsVillage/layout.json'
BOUNDS=json.loads(_plan.read_text(encoding='utf-8'))['blacksmith']['smelting_yard']['bounds_m']

def overlaps(x,y,rx=0.,ry=0.):
    return x+rx>BOUNDS[0] and x-rx<BOUNDS[2] and y+ry>BOUNDS[1] and y-ry<BOUNDS[3]

def cart_wheelways():
    # The same tyre paths drive the broad PCG substrate and near-field tread on the repaired apron.
    route=[(2.55,3.95),(2.50,2.65),(2.28,1.18),(2.35,-.48),(2.75,-1.65),
           (3.31,-2.33),(3.95,-2.66),(4.57,-2.61)]
    for side in (-1,1):
        line=[]
        for i,(x,y) in enumerate(route):
            a,b=route[max(0,i-1)],route[min(len(route)-1,i+1)]
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            line.append((x-side*.57*dy/length,y+side*.57*dx/length,.115))
        yield line

def patch(packed,height,gravel,plan):
    import numpy as np
    from PIL import Image
    from village_tread import ramp, soil_variation, tread, window
    ex,ey=plan['surface_extent_m']
    def features(u,v):
        tracks=[tread(u,v,line) for line in cart_wheelways()]
        worn=ramp((np.maximum(*tracks)+.145)/.25)
        drip=np.exp(-((u+1.91)/.21)**2)*ramp((3.65-abs(v))/.55)
        return worn,drip
    def coverage(u,v):
        inset=np.minimum(np.minimum(u+2.12,8.03+.035*v-u),3.94-abs(v))
        return ramp((inset+.41)/.86)

    # Reuse the existing native height lattice and embedded gravel. Keep the post shoes,
    # stove bases, payload and wall ledger on the common village level datum.
    rows,cols=height.shape
    u=np.linspace(-ex,ex,cols)[None,:]-ORIGIN[0]
    v=np.linspace(-ey,ey,rows)[:,None]-ORIGIN[1]
    cover=coverage(u,v)
    rut,drip=features(u,v)
    settled=-1.4*rut-1.8*drip
    limit=22.*(1.-cover)**2
    height=np.where(cover>0.,np.clip(height,settled-limit,settled+limit),height)

    # Paint at texture resolution to retain wheel tracks and the drip line between height samples.
    w,h=packed.size
    px=((np.arange(w)[None,:]+.5)/w-.5)*(2*ex)
    py=((np.arange(h)[:,None]+.5)/h-.5)*(2*ey)
    (ys,xs),x,y=window(px,py,(-46.45,-13.52,-35.24,-4.50))
    u,v=x-ORIGIN[0],y-ORIGIN[1]
    cover=coverage(u,v)
    fine=soil_variation(x,y,.29,37191)
    coarse=soil_variation(x,y,1.09,37201)
    rut,drip=features(u,v)
    import sys
    sites_dir=_plan.parents[1]/'HillsVillageBlacksmith20261117/SmeltingYard'
    if str(sites_dir) not in sys.path:
        sys.path.insert(0,str(sites_dir))
    from yard_sites import BAY_Y,bay
    fuel=tread(u,v,[(.61,-2.19,.41),(2.15,-1.11,.55),(4.53,-.38,.60),(6.18,-.81,.60)],.075*coarse)
    apron=tread(u,v,[(2.,3.64,.52),(2.15,2.58,.49),(3.47,1.26,.60),(4.83,1.10,.55),(6.05,1.57,.67)],.065*coarse)
    wear=ramp((np.maximum(fuel,apron)+.43)/.77)
    hearth=np.maximum.reduce([np.exp(-((u-(bay(y)[0]-.72))/.87)**2-((v-y)/.62)**2) for y in BAY_Y])
    soil=np.clip(.62+.18*wear+.25*rut+.21*drip+.19*hearth+.085*coarse+.054*fine,.47,.98)
    grit=np.clip(.36-.19*rut-.17*drip-.12*hearth+.048*coarse+.024*fine,.07,.45)
    area=(xs.start,ys.start,xs.stop,ys.stop)
    tile=np.array(packed.crop(area).convert('RGBA'))
    for channel,target in ((1,soil),(2,grit)):
        raw=tile[:,:,channel]/255.
        tol=(1.-cover)**2
        tile[:,:,channel]=np.rint(255*np.clip(raw,np.maximum(0.,target-tol),np.minimum(1.,target+tol))).astype('uint8')
    packed.paste(Image.fromarray(tile),area)

    stones=[p for p in gravel if not overlaps(p[0]/100.,p[1]/100.,p[2]/150.,p[2]/150.)]
    # Yard gravel belongs to the repaired shop assembly, so it can switch with the furnaces.
    return packed,height,sorted(stones,key=lambda p:(p[1],p[0]))

def publish_local():
    # Apply just the new courtyard to the live mask and native table, including any later edits elsewhere.
    from pathlib import Path
    import json,re
    import numpy as np
    from PIL import Image
    from village_ground_relief import ROOT,SOURCE,write_native
    src=ROOT/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl'
    data=src.read_text(encoding='utf-8')
    grid=data.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    stones=data.split('constexpr FGravel Gravel[]={',1)[1].split('};',1)[0]
    def records(text):
        return [tuple(map(int,g.split(','))) for g in re.findall(r'\{([0-9,\-]+)\}',text)]
    plan=json.loads((SOURCE/'layout.json').read_text(encoding='utf-8'))
    with Image.open(SOURCE/'RoadMask.png') as im:
        result,height,gravel=patch(im.convert('RGBA'),np.array(records(grid),dtype='f'),records(stones),plan)
    result.save(SOURCE/'RoadMask.png')
    # write_native samples the regular quarter-metre lattice on full village rebuilds.
    write_native(height,gravel,plan,sample_stride=1)

if __name__=='__main__':
    publish_local()
