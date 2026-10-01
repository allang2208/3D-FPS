"""Restore production authoring parameters without recreating a retired sample."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
c=dict(id='AbandonedDataArchive',revision='archive_accepted_v2_pool_20261001',phase='production_pool',
    ue_base='/Game/Dungeons/DataArchive20260930',production_map='/Game/GameMaps/L_Dungeon_Randomized',
    pool_install_script='Pool20261001/Scripts/install_pool.py',sample_retired=True,
    hall=dict(outline=[[-12,-8],[-8,-12],[8,-12],[12,-8],[12,8],[8,12],[-8,12],[-12,8]],height=6.1,wall_thickness=.28),
    central_floor_m=-.6,central_rect_m=[-6,-6,6,6],
    ports=[dict(id=k,position=[x,0,0],normal=[s,0,0],width=3.,height=2.8) for k,x,s in [('Receiving',-14,-1),('Service',14,1)]],
    reused_parts=[
      dict(id='PowerCabinetWest',mesh='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet',position=[-11.465499916,4.65,0],yaw=-90,collision=True),
      dict(id='PowerCabinetEast',mesh='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet',position=[11.465499916,-4.65,0],yaw=90,collision=True)],
    equipment_bays=[dict(id=k,center=p,width=w,depth=1.35) for k,p,w in [
        ('PaperArchiveA',[-5.1,-10.1,0],4.8),('TapeArchiveB',[5.1,-10.1,0],4.8),
        ('ServerArchiveC',[-10.1,-4.5,0],4.0),('ServerArchiveD',[10.1,4.5,0],4.0)]],
    lights=[],random_pool_registered=True,tests_run=False,environment_damage=False)
for name,p,lumens,shadow,warm in [
 ('Entry',[-13,0,3.05],260,False,True),('Exit',[13,0,3.05],260,False,True),
 ('CentreWest',[-3,0,4.9],700,True,False),('CentreEast',[3,0,4.9],600,True,False),
 ('North',[-4.7,9,5.1],450,False,False),('South',[4.7,-9,5.1],360,False,False),
 ('West',[-9,-4.2,5.1],350,False,False),('East',[9,4.2,5.1],400,False,False),
 ('Control',[0,9.3,5.1],280,True,False)]:
 c['lights'].append(dict(id=name,position=p,lumens=lumens,radius_cm=620 if p[2]>4 else 300,
                         warm=warm,cast_shadows=shadow,role='path' if 'Entry' in name or 'Exit' in name else 'key',
                         max_draw_distance_cm=2600,fade_range_cm=400))
(ROOT/'Config/room.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('DATA_ARCHIVE_DESIGN_AUTHORED')

# Keep the active refinement layout when regenerating the architecture parameters.
import runpy
runpy.run_path(str(ROOT/'EquipmentRefine20260930/Scripts/configure_layout.py'),run_name='__main__')
