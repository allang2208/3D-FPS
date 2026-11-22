"""Interior-only fittings for the repaired workshop. Positions are in house-local cm."""
import json
import unreal as u
from author_shop import pose, require
from shop_pendants import component, remove_components

ROOT='/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1'
MODELS=ROOT+'/SM_Carpenter'
TAG='VillageCarpenter.InteriorR1'
STATE='VillageCarpenter.Repaired'
LEVEL='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
CHEST_ID='HillsVillage.Plot04.JoinersChest'
CHEST_LABEL='Village_04_Carpenter_JoinersChest'
WASH=(328,63,-2.43)
CHEST=(62,326,-1.02,-4)
STONEWARE='/Game/WorldGeneration/VillageTavern/StonewareDetail/SM_Tavern'
BREAD='/Game/WorldGeneration/TemperateHills/VillageBakery/Furnishings/SM_BakeryCounterBread'


def furnish(house,add):
    def place(path,frame,solid=False):
        add('Repaired',path,frame,profile='BlockAll' if solid else 'NoCollision',extra=(TAG,))

    def prop(key,x,y,z,yaw,solid=False):
        place(MODELS+key,pose(house,x,y,z,yaw),solid)

    def fitted(path,x,y,z,yaw,size):
        bounds=require(path).get_bounding_box()
        mid=(bounds.max+bounds.min)*.5
        base=u.Vector(mid.x,mid.y,bounds.min.z)
        local=u.Transform(location=(x,y,z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(*size)/(bounds.max-bounds.min))
        frame=u.MathLibrary.compose_transforms(u.Transform(location=-base),local)
        place(path,u.MathLibrary.compose_transforms(frame,pose(house,0,0)))

    prop('WashBarrel',*WASH,16,True)
    prop('WashWater',WASH[0],WASH[1],WASH[2]+60.8,16)
    prop('StackedCases',-34,320,-1.58,2,True)
    prop('HingeTray',331,-263,75.44,-75)
    prop('PegBin',345,-79,64.44,88)
    # The carpenter keeps lunch upstairs; the existing ledger and stool remain accessible.
    fitted(STONEWARE+'Dish',233,-273,436.5,-11,(24,22,3))
    fitted(BREAD,233,-273,438.8,24,(14,8.8,5.5))
    fitted(STONEWARE+'Tankard',229,-250,436.5,119,(10,12.4,12))


def install_chest(house,station,actors):
    chest=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==CHEST_LABEL),None)
    if not chest:
        frame=pose(house,*CHEST)
        chest=actors.spawn_actor_from_class(u.ColdSteelSceneContainer,frame.translation,frame.rotation.rotator())
        chest.set_actor_label(CHEST_LABEL)
    chest.modify()
    chest.set_actor_transform(pose(house,*CHEST),False,True)
    chest.tags=list(dict.fromkeys([*map(str,chest.tags),'ColdSteel.SceneContainer.Reclosable','VillageCarpenter.Assembly']))
    chest.set_editor_property('container_id',CHEST_ID)
    chest.set_editor_property('caption','木匠工具箱')
    chest.set_editor_property('storage_pages',1)
    chest.set_editor_property('opening_motion',u.ColdSteelContainerMotion.LID)
    chest.set_editor_property('opening_duration',.63)
    chest.set_editor_property('opened_roll',96.)
    hinge=chest.get_editor_property('door_hinge')
    hinge.modify()
    hinge.set_relative_location(u.Vector(0,24.4,37.),False,True)
    for field,key in (('body','JoinersChest'),('door','JoinersChestLid')):
        part=chest.get_editor_property(field)
        part.modify()
        part.set_static_mesh(require(MODELS+key))
        part.set_relative_location(u.Vector(0,0,0),False,True)
        part.component_tags=list(dict.fromkeys([*map(str,part.component_tags),TAG,STATE]))
        part.set_editor_property('generate_overlap_events',False)
        part.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        part.set_visibility(False)
        part.set_hidden_in_game(True)
    assemblies=list(station.get_editor_property('shop_assemblies'))
    if chest not in assemblies:
        station.modify()
        station.set_editor_property('shop_assemblies',assemblies+[chest])


def apply(project):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    owners={a.get_actor_label():a for a in actors.get_all_level_actors()}
    plan=json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    house=next(h for h in plan['houses'] if h[0]=='04')
    repaired=owners['Village_Carpenter_Repaired']
    repaired.modify()
    remove_components(repaired,[c for c in repaired.get_components_by_class(u.StaticMeshComponent)
                                if TAG in map(str,c.component_tags)])
    placed=[]
    def add(state,path,frame,profile,extra):
        c=component(repaired,u.StaticMeshComponent)
        c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(require(path))
        c.set_world_transform(frame,False,True)
        c.component_tags=[STATE,*extra]+(['VillageCarpenter.NoCollision'] if profile=='NoCollision' else [])
        c.set_collision_profile_name(profile)
        c.set_editor_property('generate_overlap_events',False)
        c.set_editor_property('receives_decals',False)
        if profile=='NoCollision':
            c.set_cull_distance(2200.)
            c.set_cast_shadow(False)
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_visibility(False)
        c.set_hidden_in_game(True)
        placed.append(path)
    furnish(house,add)
    install_chest(house,owners['Village_04_Carpenter_Workbench'],actors)
    return dict(assembly=repaired.get_actor_label(),static=placed,chest=CHEST_ID)
