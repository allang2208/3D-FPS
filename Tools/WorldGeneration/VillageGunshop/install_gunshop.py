"""Restore plot 09 around the southern lane, in the village level's local frame."""
from collections import Counter, defaultdict
from pathlib import Path
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'AbandonedVillage'), str(HERE.parent/'VillageBlacksmith')]
from author_shop import BENCH, CRATE, KIT, require, shell_transform
from layout_geometry import plot_geometry
from shop_staff_light import WICK, configure
from room_daylight import SHOP_DAYLIGHT, apply_daylight
from repair_house_instances import transfer_ruin
from gunshop_shell import build_shell, install_windows
from gunshop_furnish import build_furnishings, counter_point

SITE = 'VillageGunshop.Site'
RESTORED = 'VillageGunshop.Restored'
SOLID = 'VillageGunshop.Solid'
SERVICE = 'VillageGunshop.Service'
GROUP = 'VillageGunshop.Group.'
LANTERN = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
FLAG = '/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelYardPathStone'


def layout_site(actors, current, plan, kit, subs):
    house = next(h for h in plan['houses'] if h[0] == '09')
    pieces = kit[house[2]]
    shape = plot_geometry(house, pieces, plan)
    # The old west-side threshold faced a dead end. Centre the wider house on
    # its original footprint and put the new public gable towards the lane end.
    x, y = shape['center']
    pose = ue.Transform(location=(100*x, 100*y-450, 4))
    site = next((a for a in current if SITE in map(str, a.tags)), None)
    if site:
        site.modify()
        return site, 0
    site = actors.spawn_actor_from_class(ue.Actor, pose.translation)
    site.set_actor_label('Village_09_Gunshop')
    site.tags = [SITE]
    if not site.root_component:
        parent = subs.k2_gather_subobject_data_for_instance(site)[0]
        subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.SceneComponent))
    site.root_component.set_mobility(ue.ComponentMobility.STATIC)
    site.set_actor_transform(pose, False, True)
    scale = plan['house_scale']
    original = ue.Transform(location=(house[3]*100, house[4]*100, 4-shape['floor']*scale),
                            rotation=ue.Rotator(yaw=house[5]), scale=(scale,)*3)
    expected = defaultdict(list)
    for piece in pieces:
        if not piece['mesh'].endswith('.SM_Door_00A'):
            expected[piece['mesh'].split('.')[0]].append(shell_transform(piece, original).translation)
    count = transfer_ruin(current, site, expected, shape, prefix='VillageGunshop',
                          loose_furniture={KIT+'TimberBed', KIT+'OakTable', KIT+'OakShelf', BENCH, CRATE})
    return site, count


def install_services(actors, current, site):
    existing = {a.get_actor_label():a for a in current if SERVICE in map(str, a.tags)}
    keep = ue.AttachmentRule.KEEP_WORLD

    def service(cls, name, local):
        pose = ue.MathLibrary.compose_transforms(local, site.get_actor_transform())
        actor = existing.get(name)
        if not actor:
            actor = actors.spawn_actor_from_class(cls, pose.translation, pose.rotation.rotator())
        actor.modify()
        actor.set_actor_label(name)
        actor.tags = [SERVICE]
        actor.attach_to_actor(site, 'None', keep, keep, keep, False)
        actor.set_actor_transform(pose, False, True)
        actor.set_actor_hidden_in_game(True)
        actor.set_actor_enable_collision(False)
        return actor

    # Use the same table and calibration frame as the build palette. Scale the
    # entire station uniformly so the assembly camera and parts still register.
    palette = require('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    definition = next(e for e in palette.get_editor_property('components')
                      if str(e.get_editor_property('id')) == 'gun_workbench_table')
    mesh = definition.get_editor_property('mesh')
    bounds = mesh.get_bounding_box()
    scale = min(1., 216./max(bounds.max.x-bounds.min.x, bounds.max.y-bounds.min.y))
    anchor = ue.Vector((bounds.min.x+bounds.max.x)*.5, (bounds.min.y+bounds.max.y)*.5, bounds.min.z)
    frame = ue.Transform(location=(110,714,0), rotation=ue.Rotator(yaw=90), scale=(scale,)*3)
    local = ue.MathLibrary.compose_transforms(ue.Transform(location=-anchor), frame)
    table = service(ue.VillageGunshopWorkbench, 'Village_09_Gunshop_Workbench', local)
    table.set_editor_property('station_mesh', mesh)
    body = table.get_component_by_class(ue.StaticMeshComponent)
    body.modify()
    body.set_static_mesh(mesh)
    body.set_editor_property('receives_decals', False)
    service(ue.VillageGunshopCounter, 'Village_09_Gunshop_OrderBook', ue.Transform(location=counter_point(61,-8,5)))
    return mesh.get_path_name()


def install_gunshop(actors, plan, kit):
    current = list(actors.get_all_level_actors())
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    handles = ue.SubobjectDataBlueprintFunctionLibrary
    site, transferred = layout_site(actors, current, plan, kit, subs)
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    old = {t[len(GROUP):]:c for c in site.get_components_by_class(ue.SceneComponent)
           for t in map(str, c.component_tags) if t.startswith(GROUP)}
    def component(key, cls):
        c = old.pop(key, None)
        if not c:
            h, error = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=cls))
            c = handles.get_associated_object(handles.get_data(h))
            if not c:
                raise RuntimeError(str(error))
        c.modify()
        c.component_tags = [RESTORED, GROUP+key]
        c.set_visibility(False)
        c.set_hidden_in_game(True)
        return c

    meshes, groups, roles = {}, defaultdict(list), Counter()
    def asset(path):
        if path not in meshes:
            meshes[path] = require(path)
        return meshes[path]

    def place(role, path, position, size, yaw=0, solid=False):
        box = asset(path).get_bounding_box()
        pivot = ue.Vector((box.min.x+box.max.x)*.5, (box.min.y+box.max.y)*.5, box.min.z)
        frame = ue.Transform(location=position, rotation=ue.Rotator(yaw=yaw), scale=ue.Vector(*size)/(box.max-box.min))
        groups[path, solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-pivot), frame))
        roles[role] += 1

    def rigid(role, path, position, rotation_pyr, uniform_scale=1., solid=False):
        asset(path)
        p, y, r = rotation_pyr
        groups[path, solid].append(ue.Transform(location=position, rotation=ue.Rotator(pitch=p,yaw=y,roll=r),
                                                 scale=(uniform_scale,)*3))
        roles[role] += 1

    place.rigid = rigid
    build_shell(place)
    build_furnishings(place)

    # Flags follow the bend between the existing dirt track and the covered threshold.
    for x,y,w,d,angle in [(-8,-76,62,38,-8),(-61,-94,52,41,11),(-94,-126,45,35,-21),
                           (-141,-139,48,32,8),(-175,-152,35,23,-17)]:
        place('ApproachFlags', FLAG, (x,y,-6.5), (w,d,4), angle)

    lamps = [('Entry',0,145,273,40), ('SampleWall',-300,505,273,40),
             ('Bench',110,745,273,40), ('Loft',-120,458,574,39)]
    for name,x,y,z,height in lamps:
        place('HangingLantern', LANTERN, (x,y,z), (21,21,height), 17)
        lamp = component('Lamp.'+name, ue.PointLightComponent)
        lamp.set_mobility(ue.ComponentMobility.MOVABLE)
        lamp.set_relative_location(ue.Vector(x,y,z+height*.42), False, True)
        configure(lamp)
        lamp.set_editor_property('max_draw_distance', 2100.)

    def fit_component(key, cls, mesh, pose, solid, wick):
        c = component(key, cls)
        c.set_mobility(ue.ComponentMobility.STATIC)
        c.set_relative_transform(pose,False,True)
        c.set_static_mesh(mesh)
        if solid:
            c.component_tags = [RESTORED, GROUP+key, SOLID, 'HillsStaticSupport']
        c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        c.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('receives_decals',False)
        c.set_editor_property('generate_overlap_events',False)
        if wick:
            c.set_material(0,wick)
            c.set_cast_shadow(False)
        return c

    ordinary = {}
    for (path,solid), poses in groups.items():
        key = path + ('.Solid' if solid else '.Art')
        mesh = meshes[path]
        wick = require(WICK) if path==LANTERN else None
        finishes = [slot.material_interface for slot in mesh.static_materials]
        if wick:
            finishes[0] = wick
        if not finishes or not all(finishes):
            raise RuntimeError('Missing gunshop material on '+path)
        if all(mat.get_base_material().get_editor_property('used_with_instanced_static_meshes') for mat in finishes):
            c = fit_component(key,ue.InstancedStaticMeshComponent,mesh,ue.Transform(),solid,wick)
            c.clear_instances()
            c.add_instances(poses,False,False,False)
        else:
            # A gun part typically occurs once. The ordinary mesh renderer can use its
            # exact factory shaders, including the translucent glass and optic reticles.
            for i,pose in enumerate(poses):
                fit_component(key+'.Mesh.'+str(i),ue.StaticMeshComponent,mesh,pose,solid,wick)
            ordinary[path] = len(poses)
    for key, retired in old.items():
        retired.modify()
        retired.component_tags = [GROUP+key]
        retired.set_visibility(False)
        retired.set_hidden_in_game(True)
        if isinstance(retired,ue.InstancedStaticMeshComponent):
            retired.clear_instances()
        if isinstance(retired,ue.StaticMeshComponent):
            retired.set_static_mesh(None)
            retired.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
    windows = install_windows(actors,site,current,require)
    from trade_sign_layout import crossroads, hang_trade
    hang_trade(site,site.get_actor_transform(),'Gunshop')
    crossroads(actors,'Gunshop')
    station = install_services(actors,current,site)
    room = next(a for a in current if a.get_actor_label().startswith('Village_InteriorVision_09_'))
    room.modify()
    room.set_actor_label('Village_InteriorVision_09_枪店')
    room.set_actor_transform(site.get_actor_transform(),False,True)
    room.set_editor_property('room_minimum',ue.Vector(-475,12,0))
    room.set_editor_property('room_maximum',ue.Vector(475,900,625))
    apply_daylight(room, SHOP_DAYLIGHT['09'])
    return dict(plot='09',ruin_transferred=transferred,roles=dict(roles),windows=windows,
                interior_lights=len(lamps),station_mesh=station,restored_instances=sum(roles.values()),
                ordinary_mesh_placements=ordinary)
