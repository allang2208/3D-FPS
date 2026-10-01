"""Author a restrained abandoned-hospital lighting pass for the accepted B1 layout."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
layout=json.loads((HALL/'MorgueOpenPlan20260930/Config/layout.json').read_text(encoding='utf-8'))
settings={
 'StairUpper':(170,330,'steady',0,1.0,(.69,.82,.88)),
 'StairLanding':(140,340,'steady',0,.8,(.69,.82,.88)),
 'Receiving':(230,430,'steady',0,1.0,(.68,.82,.78)),
 'OpenSouth':(0,350,'dead',0,0,(.68,.82,.78)),
 'OpenCentre':(280,440,'flicker',3.7,1.4,(.66,.82,.75)),
 'ColdFront':(350,440,'steady',0,1.25,(.67,.80,.89)),
 'NorthWest':(0,350,'dead',0,0,(.68,.82,.78)),
 'Wash':(170,320,'flicker',12.43,1.1,(.73,.83,.72)),
 'Service':(95,280,'steady',0,.65,(1.,.59,.29))}
lights=[]
for old in layout['lights']:
    lumens,radius,fault,phase,emission,tint=settings[old['id']]
    lights.append(dict(old,lumens=lumens,radius_cm=radius,fault=fault,phase=phase,
                       emission=emission,tint=tint,indirect=.15 if fault=='flicker' else .35,
                       max_draw_distance_cm=1800,fade_range_cm=300))
c=dict(revision='morgue_hospital_lighting_v1_20260930',map=layout['map'],
       ue_base='/Game/Dungeons/IncineratorHall20260929/MorgueLightingV1',lights=lights,
       postprocess=dict(center_m=[0,0,-2.25],extent_cm=[1420,1070,155],blend_radius_cm=90,
                        exposure_ev=1.,exposure_bias=-.25,indirect_intensity=.55,
                        saturation=.83,contrast=1.055,vignette=.32,bloom=.12),
       source_references=['SourceAssets/DungeonIsolationWard20260929/Scripts/author_atmosphere_materials.py',
       'https://dev.epicgames.com/documentation/en-us/unreal-engine/using-light-functions-in-unreal-engine'],
       tests_run=False)
(ROOT/'Config/lighting.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('MORGUE_LIGHTING_CONFIG_AUTHORED')
