"""Rebuild the official layers from the published planting inputs or assemble a named combination."""
import os
import sys
from pathlib import Path
import unreal as u

LIB=u.EditorAssetLibrary
SAVE=u.EditorLoadingAndSavingUtils
BASE='/Game/ForestPathStudy/VillageRegion'
ROOT=BASE+'/PCG_ForestVillageSurroundings'
MAP='/Game/GameMaps/L_ForestPathVillage'
LAYERS=('Trees','Shrubs','Grass','Rocks','Deadwood','Floor','Wetland')

def subgraphs(graph):
    layers={}
    for n in graph.get_editor_property('nodes'):
        settings=n.get_settings()
        if isinstance(settings,u.PCGSubgraphSettings):
            child=settings.get_editor_property('subgraph_instance').get_editor_property('graph')
            if not child:raise RuntimeError('Unassigned ecological subgraph')
            name=child.get_name().removeprefix('PCG_Forest')
            if name not in LAYERS or name in layers:raise RuntimeError('Unexpected child graph: '+child.get_name())
            layers[name]=n
    return layers

def compose(*keys):
    """Create/reuse a separate graph, e.g. compose('Trees','Shrubs','Grass'). Never alters the official map."""
    keys={key.strip() for key in keys}
    if not keys or keys-set(LAYERS):raise ValueError('Choose among '+', '.join(LAYERS))
    master=LIB.load_asset(ROOT)
    if not master:raise RuntimeError('Missing '+ROOT)
    active=subgraphs(master)
    if keys-active.keys():raise ValueError('Selected layer has no baked sites: '+', '.join(keys-active.keys()))
    if keys==set(active):return master.get_path_name()
    name='PCG_'+'_'.join(k for k in LAYERS if k in keys)
    folder=BASE+'/Ecology/Combinations';path=folder+'/'+name
    if LIB.does_asset_exist(path):
        graph=LIB.load_asset(path)
        if not isinstance(graph,u.PCGGraph) or set(subgraphs(graph))!=keys:
            raise RuntimeError('A different asset already occupies '+path)
        return graph.get_path_name()
    LIB.make_directory(folder)
    graph=LIB.duplicate_asset(ROOT,path)
    if not graph:raise RuntimeError('Cannot create '+path)
    try:
        for key,node in subgraphs(graph).items():
            if key not in keys:graph.remove_node(node)
        if not LIB.save_loaded_asset(graph,False):raise RuntimeError('Cannot save '+path)
    except Exception:
        LIB.delete_asset(path)
        raise
    return graph.get_path_name()

def rebuild(points_directory):
    directory=Path(points_directory)
    if (directory/'theme.id').is_file():
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from landscape_themes import build
        return build((directory/'theme.id').read_text(encoding='ascii').strip(),directory)
    points=directory/'planting.bin'
    for required in (points,directory/'reference-meshes.txt',directory/'harvest-trees.f32',directory/'study-granite.i32'):
        if not required.is_file():raise FileNotFoundError(required)
    world=SAVE.load_map(MAP)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('The persistent forest village map must be selected')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(MAP+'.'))
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates or not region.bake_vegetation(str(points),templates):raise RuntimeError('Forest layer bake failed')
    if not SAVE.save_map(world,MAP):raise RuntimeError('Cannot save '+MAP)

if __name__=='__main__':
    layers=os.environ.get('FPS_FOREST_ECOLOGY_LAYERS','')
    if layers:print(compose(*layers.split(',')))
    else:
        src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
        rebuild(Path(os.environ.get('FPS_FOREST_PLANTING_DIR',str(src/'Dressing'))))
