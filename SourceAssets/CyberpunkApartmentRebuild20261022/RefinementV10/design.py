"""First-row facade placements, in the retained bay author coordinate system."""
from pathlib import Path
import json,runpy
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV10'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OLD8='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV8'
OLD7='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7'
CITY=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings']
def building(x):return min((b for b in CITY if b['group'] in ('City_1','City_2')),key=lambda b:abs(b['x']-x))
a,b,c,d=[building(x) for x in (-943.4,-363.1,-63.1,386.3)]
BOARDS=[
 dict(key='Nexus',kind='portrait',p=(a['x']-a['width']*.06,a['y']-a['depth']/2-2.5,97),w=44,h=62,depth=3,slot=0,phase=0,host=a),
 dict(key='Estuary',kind='portrait',p=(b['x']+b['width']*.04,b['y']-b['depth']*.83/2-2.5,98),w=30,h=44,depth=3,slot=1,phase=4.1,host=b),
 dict(key='Tideline',kind='portrait',p=(c['x']-c['width']*.06,c['y']-c['depth']/2-2.5,88),w=35,h=52,depth=3,slot=2,phase=8.3,host=c),
 dict(key='Port',kind='portrait',p=(d['x'],d['y']+d['depth']*.13-d['depth']*.66/2-2.5,124),w=30,h=36,depth=3,slot=3,phase=2.7,host=d),
 dict(key='NexusRibbon',kind='ribbon',p=(a['x'],a['y']-a['depth']*.78/2-2.5,50),w=38,h=7,depth=3,slot=0,phase=6.4,host=a),
 dict(key='EstuaryRibbon',kind='ribbon',p=(b['x'],b['y']-b['depth']/2-2.5,60),w=40,h=6,depth=3,slot=2,phase=11.2,host=b),
]
SEARCH=runpy.run_path(str(ROOT.parent/'RefinementV9/design.py'))['SEARCH']
def world_metres(p):return ((-p[0]+10)*1.25,p[1]*1.25,(p[2]-90)*1.25)
# Match the existing display geometry (U points along world -X; V points down).
WATER_PARAMETERS=dict(AdReflectionGain=.8,BeamReflectionGain=.7,ReflectionNormalWeight=.65,ReflectionBlur=.009,ReflectionMaxRadiance=1.8)
