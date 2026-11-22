"""Replace only the sign and the forge body/fuel in the existing blacksmith assemblies."""
import json,sys
from pathlib import Path
import unreal as u
from author_shop import pose,require
from LoftR3.design import HEARTH
from TradeSign.layout import SIGN
ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ForgeR2'
OLD_BODY='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3/Meshes/SM_SmithLoft_ForgeHearth'
OLD_FUEL='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/SM_SmithHearthDressing'
BODY=ROOT+'/SM_SmithSideBlastHearth'
FUEL=ROOT+'/SM_SmithSideBlastFuel'

def apply_to(house,station):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'AbandonedVillage'))
    from shop_pendants import component,remove_components
    from village_chimney import SMITH_FIRE_AT_STATION
    hosts={a.get_actor_label():a for a in station.get_editor_property('shop_assemblies') if a}
    common=hosts['Village_Blacksmith_Common'];restored=hosts['Village_Blacksmith_Repaired']
    common.modify();restored.modify()
    parts=[(common,'SignBracketR2',pose(house,4,-401.5,321),'SmithBracket',False,False),
           (common,'SignLinksR2',pose(house,4,-401.5,316.8),'SmithSuspension',True,False),
           (common,'SignBoardR2',pose(house,4,-401.5,310.65),'SmithSwingBoard',True,False),
           (common,'SideBlastHearth',pose(house,*HEARTH),'SmithHearthBody',False,True),
           (restored,'SideBlastFuel',pose(house,*HEARTH),'SmithHearthCoals',False,False)]
    paths={SIGN,OLD_BODY,OLD_FUEL,*[ROOT+'/SM_Smith'+name for _,name,*_ in parts]}
    for a in (common,restored):
        old=[c for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_path_name().split('.')[0] in paths]
        remove_components(a,old)
    for owner,name,frame,tag,moving,solid in parts:
        c=component(owner,u.StaticMeshComponent)
        c.set_mobility(u.ComponentMobility.MOVABLE if moving else u.ComponentMobility.STATIC)
        c.set_static_mesh(require(ROOT+'/SM_Smith'+name))
        c.set_world_transform(frame,False,True)
        tags=['VillageShop.'+tag]
        if not solid:tags.append('VillageShop.NoCollision')
        c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        c.set_editor_property('generate_overlap_events',False)
        if owner==restored:
            tags+=['VillageShop.Repaired','VillageShop.SmithWorkfloor']
            c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.component_tags=tags
    for effect in station.get_components_by_class(u.NiagaraComponent):
        if 'VillageShop.HearthFire' in map(str,effect.component_tags):
            station.modify();effect.modify()
            effect.set_relative_location(u.Vector(*SMITH_FIRE_AT_STATION),False,True)
    return dict(meshes=[ROOT+'/SM_Smith'+p[1] for p in parts],fire_in_station_cm=SMITH_FIRE_AT_STATION)

def apply(project):
    layout=json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    house=next(h for h in layout['houses'] if h[0]==layout['blacksmith']['house'])
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    station,=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='Village_01_Blacksmith_Forge']
    return apply_to(house,station)
