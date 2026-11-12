"""Read saved wet-forest assets and formal-map bindings; never save packages."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');BATCH=ROOT/'SourceAssets/HillsWetForest20261111'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
BASE='/Game/WorldGeneration/TemperateHills'
report={'errors':[],'materials':{},'save_written':False,'map_saved':False}
def check(ok,message):
    if not ok:report['errors'].append(message)
paths={BASE+'/Grass/M_TemperateMeadow':['GrassRoughness'],
       BASE+'/M_TemperateGround':['GroundColor','GroundRoughness','GroundNormal'],
       BASE+'/PebbleShore/M_PebbleShoreGround':['GroundColor','GroundRoughness','GroundNormal'],
       '/Game/Fluids/RiverPilot20260923/M_RiverPilot':['WaterRainNormal'],
       BASE+'/WetForest/M_ForestPond':['WaterRainNormal','PoolShoreCoverage']}
for path,expected in paths.items():
    mat=u.load_asset(path);check(bool(mat),'Missing '+path)
    if not mat:continue
    nodes=L.get_material_expressions(mat)
    tags=[str(n.get_editor_property('desc')) for n in nodes]
    owned=[t for t in tags if t.startswith('HillsWet20261111.')]
    check(len(owned)==len(set(owned)),'Repeated wet nodes '+path)
    for suffix in expected:check('HillsWet20261111.'+suffix in tags,'Missing layer '+path+' '+suffix)
    outputs={}
    for name in ('BASE_COLOR','NORMAL','ROUGHNESS'):
        n=L.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+name))
        outputs[name]=str(n.get_editor_property('desc')) if n else None
    report['materials'][path]={'wet_nodes':len(owned),'outputs':outputs,'native_water_profile':str(E.get_metadata_tag(mat,'NativeWater.Profile'))}
    if 'M_ForestPond' in path:
        check(not mat.get_editor_property('tangent_space_normal'),'Pond normal space')
        check(mat.get_editor_property('blend_mode')==u.BlendMode.BLEND_MASKED,'Pond shoreline mask')
        check(str(E.get_metadata_tag(mat,'NativeWater.Profile'))=='forest_pool','Pond optical profile')
mpc=u.load_asset(BASE+'/Atmosphere20261110/MPC_ForestWind')
names=[str(p.get_editor_property('parameter_name')) for p in mpc.get_editor_property('vector_parameters')]
report['mpc_vectors']=names
for name in ('ForestWind','RainforestRegion','RainforestControl','RainforestWeather'):check(name in names,'MPC '+name)
grass_mpc=u.load_asset('/Game/PN_GrassLibrary/Materials/PN_WindParameters')
grass_names=[str(p.get_editor_property('parameter_name')) for p in grass_mpc.get_editor_property('vector_parameters')]
report['grass_mpc_vectors']=grass_names
for name in ('RainforestRegion','RainforestControl','RainforestWeather'):check(name in grass_names,'Grass MPC '+name)
instances=[]
for path in E.list_assets(BASE+'/Grass',True,False):
    if '/MI_Meadow_' not in path:continue
    mi=u.load_asset(path)
    if not isinstance(mi,u.MaterialInstanceConstant):continue
    parent=mi.get_editor_property('parent')
    check(parent and parent.get_path_name()==BASE+'/Grass/M_TemperateMeadow.M_TemperateMeadow','Grass instance parent '+path)
    instances.append(path)
report['grass_instances_using_master']=instances
check(len(instances)>=12,'Expected saved meadow material instances')
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_TemperateHills_Initial')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
hills=[a for a in actors if a.get_class().get_name()=='TemperateHillsWorld']
check(len(hills)==1,'Formal map hills actor count')
if hills:
    actor=hills[0]
    for field in ('forest_pond_material','river_pilot_material'):
        value=str(actor.get_editor_property(field));report[field]=value
        check(('M_ForestPond' if field=='forest_pond_material' else 'M_RiverPilot') in value,'Map material '+field)
report['finished_at']=datetime.now().astimezone().isoformat()
(BATCH/'Receipts/assets-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['errors']:raise RuntimeError(str(report['errors']))
u.log('WET_FOREST_ASSET_CHECK_OK')
