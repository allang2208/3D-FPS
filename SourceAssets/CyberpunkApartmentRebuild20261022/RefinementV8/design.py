from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV8'
MAP='/Game/GameMaps/L_CyberpunkApartment'
# Author coordinates in metres, shared with the retained bay city.
BOARDS=[
 dict(key='Nexus',kind='portrait',p=(-705,1391.8,195),w=26,h=39,depth=7,slot=0,phase=0),
 dict(key='Estuary',kind='portrait',p=(-1485,1415.8,208),w=40,h=60,depth=6,slot=1,phase=4.1),
 dict(key='Tideline',kind='portrait',p=(394,1633,110),w=24,h=36,depth=5,slot=2,phase=8.3),
 dict(key='Port',kind='portrait',p=(1120,2399,118),w=24,h=36,depth=8,slot=3,phase=2.7),
 dict(key='NexusRibbon',kind='ribbon',p=(-680,1411.7,249.7),w=42,h=7,depth=5,slot=0,phase=6.4),
 dict(key='EstuaryRibbon',kind='ribbon',p=(-1472,1409.8,123.2),w=80,h=5,depth=6,slot=2,phase=11.2),
]
