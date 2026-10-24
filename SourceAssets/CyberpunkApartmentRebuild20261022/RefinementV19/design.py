from pathlib import Path
import runpy,json,copy
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV19';MAP='/Game/GameMaps/L_CyberpunkApartment'
V17=runpy.run_path(str(R.parent/'RefinementV17/design.py'));FAMILIES=V17['FAMILIES'];SOURCE_FAMILY=V17['SOURCE_FAMILY']
SHIFT=-615.
PALETTE=dict(WarmBands=(1.,.78,.49),PearlVertical=(.72,.87,1.),AmberTerrace=(1.,.67,.40),BlueFrame=(.45,.68,1.),CopperArcade=(1.,.77,.47),QuietGlass=(.72,.83,.96))
OFFICES={'WarmBands','PearlVertical','BlueFrame','CopperArcade'}
CITY=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings']
a,b=CITY[35],CITY[63]
BOARDS=[
 dict(key='Arcade',kind='portrait',p=(a['x']+a['width']*.04,a['y']-a['depth']*.83/2-2.6,96),w=30,h=42,depth=3,slot=3,phase=17.3,host_index=35),
 dict(key='Metro',kind='portrait',p=(b['x'],b['y']-b['depth']/2-2.6,42),w=28,h=42,depth=3,slot=0,phase=22.7,host_index=63),
]
HOLOGRAMS=[]
for key,title,subtitle,idx,style,color,phase in [('Aether','AETHER','SKY NETWORK',30,0,(.12,.74,1.),2.1),('Orbit','ORBIT','HARBOR TRANSIT',58,1,(.80,.32,1.),7.8)]:
 b=CITY[idx];roof=b['authored_height']+5
 HOLOGRAMS.append(dict(key=key,title=title,subtitle=subtitle,host_index=idx,origin=(b['x']-b['width']*.30,b['y']-b['depth']*.30,roof+1.5),p=(b['x']-b['width']*.30,b['y']-b['depth']*.30-28,roof+166),w=92,h=92,style=style,color=color,phase=phase))
def world_metres(p):return ((-p[0]+10)*1.25,(p[1]+SHIFT)*1.25,(p[2]-90)*1.25)
