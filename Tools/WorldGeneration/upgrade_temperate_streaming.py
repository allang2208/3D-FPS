"""Migrate the existing hills map to soft references and smaller PCG cells.

Authoring only: does not run gameplay, audits, screenshots or renderer previews.
Requires the streaming C++ module and the previously authored vegetation assets.
"""
from pathlib import Path
import shutil
from datetime import datetime
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
DEST='/Game/WorldGeneration/TemperateHills'
LEVEL='/Game/GameMaps/L_TemperateHills_Initial'
EAL=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Required authoring asset missing: '+path)
    return obj

backup=ROOT/'Saved/TemperateHills'/('BeforeStreaming-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.umap')
backup.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'Content/GameMaps/L_TemperateHills_Initial.umap',backup)

factory=u.DataAssetFactory()
factory.set_editor_property('data_asset_class',u.TemperateHillsAssets)
path=DEST+'/DA_TemperateHillsStreaming'
assets=load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset('DA_TemperateHillsStreaming',DEST,u.TemperateHillsAssets,factory)
# Python's soft-object setter takes a UObject; the new property serializes a soft path.
assets.set_editor_property('ground_material',load(DEST+'/M_TemperateGround'))
assets.set_editor_property('valley_fog_material',load(DEST+'/MI_ValleyLowFog'))
assets.set_editor_property('valley_fog_class',u.load_class(None,'/Game/UnrealNormandy/Blueprints/BP_LocalFogVolume_Master.BP_LocalFogVolume_Master_C'))
assets.set_editor_property('trunk_collision_mesh',load('/Engine/BasicShapes/Cylinder'))
assets.set_editor_property('trees',[load(DEST+'/SK_BlackPoplarPCG_'+v) for v in 'ABCD'])
assets.set_editor_property('rocks',[load('/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_0'+str(i)+'A') for i in range(4)])
assets.set_editor_property('shrubs',[load('/Game/UnrealNormandy/StaticMeshes/SM_PlantType'+v+'_00A') for v in 'ABC'])
assets.set_editor_property('grass',[load('/Game/UnrealNormandy/StaticMeshes/SM_Grass_0'+str(i)+'A') for i in range(3)]+[load('/Game/UnrealNormandy/StaticMeshes/SM_GrassTall_00A')])
graphs=[]
for layer,name in enumerate(['PCG_BlackPoplar','PCG_HillsRocks','PCG_HillsShrubs','PCG_HillsGrass']):
    graph=load(DEST+'/'+name)
    graph.set_editor_property('hi_gen_grid_size',[u.PCGHiGenGrid.GRID64,u.PCGHiGenGrid.GRID64,u.PCGHiGenGrid.GRID32,u.PCGHiGenGrid.GRID16][layer])
    if layer>0:
        for node in graph.get_editor_property('nodes'):
            settings=node.get_settings()
            if not isinstance(settings,u.PCGStaticMeshSpawnerSettings):continue
            selector=settings.get_editor_property('mesh_selector_parameters')
            descriptor=selector.get_editor_property('template_descriptor')
            descriptor.set_editor_property('instance_start_cull_distance',[0,11000,7000,3500][layer])
            descriptor.set_editor_property('instance_end_cull_distance',[0,16000,11000,6000][layer])
            selector.set_editor_property('template_descriptor',descriptor)
    EAL.save_loaded_asset(graph,False)
    graphs.append(graph)
assets.set_editor_property('graphs',graphs)
EAL.save_loaded_asset(assets,False)

editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not editor.load_level(LEVEL):raise RuntimeError('Could not open the authored hills map')
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor,u.TemperateHillsWorld):
        actor.set_editor_property('assets',assets)
        actor.set_editor_property('detail_radius_meters',160)
        actor.set_editor_property('view_radius_meters',384)
if not editor.save_current_level():raise RuntimeError('Could not save the streaming map')
u.log('TEMPERATE_STREAMING_AUTHORING_COMPLETE '+LEVEL)
