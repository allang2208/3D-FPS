"""Single source of the flue-gas station's dimensions and placements (metres)."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('Config','Authored','Receipts'):(ROOT/folder).mkdir(exist_ok=True)
base='/Game/Dungeons/FlueGasStation20261001'
config=dict(id='AbandonedFlueGasStation',name='废弃烟气净化站',revision='flue_gas_controls_pipes_rails_v2_20261001',
    phase='production_reserved',ue_base=base,sample_map=None,
    active_refinement='RefineV2',refinement_author='RefineV2/Scripts/author_revision.py',refinement_installer='RefineV2/Scripts/import_assets.py',
    hall=dict(width=28.,length=24.,height=8.,wall_thickness=.28),
    towers=[dict(id='ST-01',position=[-8,-5,0],radius=1.55),dict(id='ST-02',position=[-8,2,0],radius=1.55)],
    filter=dict(position=[8.6,.8,0],width=4.8,length=7.),
    platform=dict(rect=[-13.5,8.5,13.5,11.65],height=2.4),
    stairs=dict(centres_x=[-12.4,12.4],start_y=3.1,width=1.8,steps=15,rise=.16,going=.36),
    clear_combat_rect_m=[-4.35,-7.0,4.35,7.8],
    ports=[dict(id=key,position=[x,-8,0],normal=[normal,0,0],width=3.,height=2.8)
        for key,x,normal in [('Incinerator',-16,-1),('Onward',16,1)]],
    player_start_m=[-12.5,-8,1.05],player_yaw=0,
    return_portal_m=[-15.45,-8,0],return_portal_yaw=0,
    reused_parts=[dict(id='PowerCabinet',mesh='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet',
        position=[5,-11.35,0],yaw=180,collision=True)],
    lights=[],postprocess=dict(exposure_ev=.7,exposure_bias=-.1,indirect_intensity=.75,vignette=.3,bloom=.25),
    route_intent=dict(predecessor='AbandonedIncineratorHall',successor='DataArchive convergence via optional transition',
        fixed_adjacency=True,registration='production_catalog_reserved_for_fixed_themed_route'),
    tests_run=False,rendered=False,random_pool_registered=False)
for name,p,lm,radius,shadow,color in [
    ('Entry',[-15,-8,3.05],260,370,False,[1,.76,.48]),
    ('Exit',[15,-8,3.05],280,370,False,[1,.76,.48]),
    ('FrontAisle',[0,-7,5.5],1450,1080,True,[.60,.73,.79]),
    ('Centre',[0,1.5,6.0],1950,1250,True,[.59,.72,.77]),
    ('Scrubber',[-8,-1.5,6.9],680,800,False,[.72,.78,.73]),
    ('Filter',[8.3,-4.4,5.4],730,720,False,[.79,.74,.60]),
    ('WestStair',[-12.4,5.3,5.4],460,510,False,[.60,.72,.76]),
    ('EastStair',[12.4,5.3,5.4],400,510,False,[.60,.72,.76]),
    ('Gallery',[0,10.1,6.1],820,900,False,[.75,.67,.48])]:
    config['lights'].append(dict(id=name,position=p,lumens=lm,radius_cm=radius,cast_shadows=shadow,
        tint=color,fixture=True,role='key' if shadow else 'path',indirect=.7,max_draw_distance_cm=3200,fade_range_cm=500))
(ROOT/'Config/room.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/sources.json').write_text(json.dumps(dict(new_geometry='Original Blender procedural hard-surface meshes; editable blend and FBX retained',
    new_textures='Original equipment lettering, gauge faces and safety sign atlas authored with Pillow; no generated reference images',
    reused=['DungeonSeamMetal20260923 industrial steel/enamel/rubber materials','DungeonWallUpgrade20260924 concrete',
        'DungeonIndustrialV1 ceiling fixtures','DungeonFacilityScenes20260927 power cabinet',
        'DungeonRoomShells20260922 geometry helpers'],external_downloads=[],
    license_note='Shared project dependencies retain their existing provenance; no new third-party download or redistribution.'),ensure_ascii=False,indent=2),encoding='utf-8')
print('FLUE_GAS_DESIGN_WRITTEN')
