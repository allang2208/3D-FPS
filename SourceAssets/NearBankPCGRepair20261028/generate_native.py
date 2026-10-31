"""Manufacture one near-bank district using Epic's native PCG primitives.

This runs in AuthoringHost only. Source sample assets are read, never saved.
The producer world is not a game/test level and is never imported into FPSGAME.
"""
from pathlib import Path
from datetime import datetime
import json,unreal as u,collections
R=Path(__file__).resolve().parent
BASE='/Game/NativeNearBank20261028'
CFG=json.loads((R/'native_inputs.json').read_text())
T=u.get_default_object(u.PCGToolset);E=u.EditorAssetLibrary
if E.does_asset_exist(BASE+'/AuthoringState'):
    world=u.EditorLoadingAndSavingUtils.load_map(BASE+'/AuthoringState')
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if not isinstance(a,(u.WorldSettings,u.LevelScriptActor)):
            a.destroy_actor()
else:world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
for r in CFG['inputs']:
    a=u.NearBankPCGAuthoringTools.create_spline_input(world,r['name'],[u.Vector(*p) for p in r['points']],r['closed'],r['tag'])
    if not a:raise RuntimeError('Cannot create native spline '+r['name'])
graph_path=BASE+'/Graphs/PCG_ApartmentNearBank'
g=u.load_asset(graph_path)
if not g:g=T.call_method('CreateGraph',('PCG_ApartmentNearBank',BASE+'/Graphs'))
else:
    for n in list(g.get_editor_property('nodes')):g.remove_node(n)
nodes={};contracts={}
def ref(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required grammar asset unavailable: '+path)
    return {'refPath':asset.get_path_name()}
def vec(x=0,y=0,z=0):return dict(x=x,y=y,z=z)
def sg(name,path,params=None):
    if not path.startswith('/'):path='/PCGPrimitives/Primitives/'+path
    source=u.load_asset(path)
    if not source:raise RuntimeError('Missing native primitive '+path)
    node=T.call_method('AddSubgraphNode',(g,source,name,json.dumps(params or {}),name,'',len(nodes)%6*350,len(nodes)//6*240))
    if not node:raise RuntimeError('Cannot author '+name)
    nodes[name]=node
    contracts[name]=dict(source=path,parameters=params or {},inputs=[str(p.properties.label) for p in source.get_input_node().output_pins],outputs=[str(p.properties.label) for p in source.get_output_node().input_pins])
    return node
def link(a,b,out=0,inp=0):
    if isinstance(a,str):a=nodes[a]
    if isinstance(b,str):b=nodes[b]
    ca=contracts[a.get_name()];cb=contracts[b.get_name()]
    op=ca['outputs'][out] if isinstance(out,int) else out
    ip=cb['inputs'][inp] if isinstance(inp,int) else inp
    T.call_method('ConnectNodePins',(a,op,b,ip))
def get(name,tag):return sg(name,'Get/Get_ActorData',{'ActorTag':tag})
def exclude(name,a,b,out=0):
    n=sg(name,'Compose/Compose_Areas_Exclusion');link(a,n,out);link(b,n,inp=1);return n
def offset(name,src,z,out=0):
    n=sg(name,'Transform/Transform_Offset',{'offset':vec(z=z),'AbsoluteOffset':True});link(src,n,out);return n
def planar(name,src,material,out=0):
    n=sg(name,'Create/Create_Mesh_Planar',{'Material':ref(material),'DynamicMesh':False,'OutMeshName':name,'OutMeshPath':BASE+'/Meshes'});link(src,n,out);return n
def spawn(name,src,params=None,out=0):
    n=sg(name,'Spawn/Spawn_Assets',params or {});link(src,n,out);return n

boundary=get('Boundary','NBPCG_Boundary');host=get('ApartmentExclusion','NBPCG_Exclusion')
local=get('LocalRoadInputs','NBPCG_Local');collector=get('CollectorInputs','NBPCG_Collector');artery=get('ArteryInputs','NBPCG_Artery')
widths=CFG['road_width_cm']; wp=dict(LocalRoadWidth=widths['local'],CollectorRoadWidth=widths['collector'],ArteryRoadWidth=widths['artery'])
solve=sg('SolveIntersections','/CitySamplePCG/PCG/Intersection_solving',dict(wp,Crosswalk_distance_from_intersection=650,intersection_expansion_range=100,roadSectionLimit=300))
link(local,solve,inp='Local Roads');link(collector,solve,inp='Collector Roads');link(artery,solve,inp='Artery Roads')
profile='/CitySamplePCG/PCG/DataAssets/Roads/Road_City/SGD_Road_City_HighRes'
for kind,pin in [('local','LocalSections'),('collector','CollectorSections'),('artery','ArterySections')]:
    road=sg('Road_'+kind,'Assign/Assign_ShapeGrammarDefinition',{'ShapeGrammarDefinition':ref(profile),'Size':widths[kind],'SpawnAssets':True})
    link(solve,road,out=pin)
asphalt='/Game/Props/CyberpunkNearBank20261028/Materials/M_NB_Asphalt'
junctions=planar('JunctionAsphalt',solve,asphalt,'IntersectionsPlanar')
crosswalk=sg('Crosswalks','/CitySamplePCG/PCG/Crosswalks',dict(wp,Grammar_Asset=ref('/CitySamplePCG/PCG/DataAssets/Roads/Road_City/SGD_Road_City'),Crosswalk_distance_from_intersection=650))
for kind in ('Local','Collector','Artery'):link(solve,crosswalk,out=kind+'Sections',inp=kind+' Road Sections')
spawn('SpawnCrosswalks',crosswalk)

site=exclude('PreserveApartment',boundary,host)
lots=sg('RoadsSubtractLots','Compose/Compose_Areas_Exclusion');link(site,lots);link(solve,lots,out='RoadsFootprints',inp=1)
walks=sg('SidewalksAndStreetFurniture','Assign/Assign_ShapeGrammarDefinition',{'ShapeGrammarDefinition':ref('/CitySamplePCG/PCG/DataAssets/Roads/Sidewalk_A/SGD_Sidewalk_A'),'Size':570,'SpawnAssets':True});link(lots,walks)
segments=sg('LotCornerSegments','Extract/Extract_Segments',{'CutAngleThreshold':20});link(lots,segments)
corners=sg('RoundedSidewalkCorners','Assign/Assign_ShapeGrammarDefinition',{'ShapeGrammarDefinition':ref('/CitySamplePCG/PCG/DataAssets/Roads/Sidewalk_A/SGD_Sidewalk_Corners'),'Size':1,'SpawnAssets':True});link(segments,corners)
inner=sg('SubtractSidewalks','Transform/Transform_Areas_Contract',{'Contract':570});link(lots,inner)
setback=sg('BuildingSetback','Transform/Transform_Areas_Contract',{'Contract':CFG['building_setback_cm']});link(inner,setback)
split=sg('SubdivideBuildingLots','Subdivide/Subdivide_Areas_WithRecursiveSplit',{'Iterations':1,'MinAreaSize':1200,'MaxSplitDistancFromCenter':.15,'Seed':CFG['seed']});link(setback,split)
minimum=sg('RejectTinyFootprints','Filter/Filter_Areas_BySize',{'Size':500,'Operator':'Greater'});link(split,minimum,out='Areas')
width=sg('RejectNarrowFootprints','/CitySamplePCG/PCG/FilterPolygonByEdgeLength',{'Filter_Operator':'Greater','Threshold':600});link(minimum,width,out='Selected',inp='Out')
reserve=sg('ReserveParksAndPlazas','Filter/Filter_RandomChoice',{'Ratio':1-CFG['park_ratio'],'Seed':CFG['seed'],'RandomPerDataset':True});link(width,reserve)
data=sg('CitySampleBuildingGrammar','/CitySamplePCG/PCG/Primitives/Buildings/Subgraphs/LoadCitySampleData')
buildings=sg('NineBuildingStyles','/CitySamplePCG/PCG/Primitives/Buildings/Assign_CitySampleBuildings',{'MinHeight':2100,'MaxHeight':7500,'BuildingsStyles':','.join(CFG['building_styles']),'Seed':CFG['seed'],'SpawnMeshes':True,'SpawnIntoBuildingsActors':True,'Foundation':False})
link(reserve,buildings,out='Selected',inp='BuildingsFootprints');link(data,buildings,inp='CitySample data')
roof=offset('RoofSurfaceOffset',buildings,-10,'Rooftops Footprints')
planar('RoofSurfaces',roof,'/Game/Environment/RoofTop/Material/M_Rooftop')
roofs=sg('RoofDetails','/CitySamplePCG/PCG/Primitives/Fill_Areas_WithFittingAssets_with_Corrective',{'Assets':[ref('/CitySamplePCG/PCG/DataAssets/RoofTops/Rooftop_Small_'+k+'_PCG') for k in ('A','B','D','G','K','N','Q','T')],'Seed':CFG['seed'],'Overlap':.1,'SpawnAssets':True,'KeepAssembliesRoot':False,'Random90DegRotation':True,'BaseFillPointsPerSquareMeters':.01});link(roof,roofs)

parkchoice=sg('ParkOrPlaza','Filter/Filter_RandomChoice',{'Ratio':.35,'Seed':281029});link(reserve,parkchoice,out='Unselected')
plazas=sg('FittedPocketPlazas','/CitySamplePCG/PCG/Primitives/Fill_Areas_WithFittingAssets_with_Corrective',{'Assets':[ref('/CitySamplePCG/PCG/DataAssets/Plazas/Plaza_Medium_'+k+'_PCG') for k in ('A','B','C','F')],'Seed':281029,'Overlap':.1,'SpawnAssets':True,'KeepAssembliesRoot':False,'Random90DegRotation':True,'BaseFillPointsPerSquareMeters':.01});link(parkchoice,plazas,out='Selected')
parkfloor=offset('ParkGroundOffset',parkchoice,4,'Unselected');planar('ParkGround',parkfloor,'/Game/Props/CyberpunkUrbanLandscape20261025/Materials/M_UL_Lawn')
treearea=sg('TreeCrownSetback','Transform/Transform_Areas_Contract',{'Contract':650});link(parkchoice,treearea,out='Unselected')
scatter=sg('ParkTreeCandidates','Fill/Fill_Areas_Randomly',{'PointsPerSquaredMeter':.012,'SamplingSeed':CFG['seed'],'OutputPointsExtents':vec(450,450,600)});link(treearea,scatter)
treeassets=['/CitySamplePCG/BlackAlder/Geometry/PivotPainter/SM_BlackAlder_Field_'+k+'_PP' for k in ('01','02','03','04')]
assign=sg('AssignTreeForms','Assign/Assign_Assets',{'Assets':[ref(p) for p in treeassets],'ScaleOffset':vec(.75,.75,.75),'RandomRotationRange':vec(0,0,360),'RandomScaleRange':vec(.18,.18,.18),'Seed':CFG['seed'],'UseMeshBounds':True});link(scatter,assign)
prune,ps=g.add_node_of_type(u.PCGSelfPruningSettings)
nodes[prune.get_name()]=prune;contracts[prune.get_name()]=dict(source='native SelfPruning',inputs=['In'],outputs=['Out'])
link(assign,prune);spawn('SpawnParkTrees',prune,{'Collision':True})

# Give every buildable plot a paved foundation; this is below the facade and
# sidewalk walking surface, so it cannot cover the road or existing riverbank.
pad=offset('FoundationGroundOffset',reserve,1,'Selected')
planar('BuildingPads',pad,'/Game/Props/CyberpunkNearBank20261028/Materials/M_NB_Cap')
for stage,src,pin in [('Boundary',boundary,0),('Lots',lots,0),('Interior',inner,0),('Setback',setback,0),('Subdivision',split,'Areas'),('MinArea',minimum,'Selected'),('MinWidth',width,'InsideFilter'),('BuildingPlots',reserve,'Selected'),('ParkPlots',reserve,'Unselected')]:
    tag=sg('Output_'+stage,'Write/Write_Tag',{'CustomTags':stage});link(src,tag,out=pin)
    T.call_method('ConnectNodePins',(tag,contracts[tag.get_name()]['outputs'][0],g.get_output_node(),'Out'))
E.save_loaded_asset(g,False)
(R/'native_graph_contracts.json').write_text(json.dumps(contracts,indent=2),encoding='utf8')
print('NATIVE_PCG_GRAPH_SAVED',len(nodes),flush=True)
tr=u.Transform();tr.translation=u.Vector(0,-25000,-10857);tr.scale3d=u.Vector(650,650,250)
T.call_method('SpawnGraphInstance',(g,'NBPCG_Production',tr,'{}'))
volume=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PCGVolume) if a.get_actor_label()=='NBPCG_Production')
volume.pcg_component.set_editor_property('seed',CFG['seed'])
print('NATIVE_PCG_GENERATION_START',flush=True)
if not u.NearBankPCGAuthoringTools.generate_offline(volume,600):raise RuntimeError('Native graph did not complete')
print('NATIVE_PCG_GENERATION_FINISHED',flush=True)
for asset in E.list_assets(BASE,True,False):
    if asset.split('.')[0]!=BASE+'/AuthoringState':E.save_asset(asset,False)
if not u.EditorLoadingAndSavingUtils.save_map(world,BASE+'/AuthoringState'):raise RuntimeError('Cannot save producer state')
summary=collections.Counter();meshes=collections.Counter()
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        count=c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1
        summary[c.get_class().get_name()]+=count;meshes[c.static_mesh.get_path_name()]+=count
    summary['dynamic_mesh_components']+=len(a.get_components_by_class(u.DynamicMeshComponent))
result=dict(stage='native_generation_saved',graph=graph_path,producer_map=BASE+'/AuthoringState',generated_counts=dict(summary),mesh_counts=dict(meshes),saved_at=datetime.now().astimezone().isoformat(),main_map_modified=False,game_run=False)
(R/'native_generation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('NATIVE_DISTRICT_SAVED',dict(summary),len(meshes),flush=True)
out=volume.pcg_component.get_generated_graph_output()
(R/'native_output_data.txt').write_text(out.export_text(),encoding='utf8')
import runpy
runpy.run_path(str(R/'export_native.py'))['export'](world)
