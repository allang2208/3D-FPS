"""Scoped hall finish: shrine breach, aligned gallery lamps, doorway and vent fit."""
from pathlib import Path
import copy,json,runpy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/ReceptionFinish20261010'
REVISION='reception_entry_gallery_vent_finish_20261010'
MODULE='FacilityReceptionHall'
GROUND=PROJECT/'SourceAssets/ReceptionGroundLighting20261009/recipe.py'
REMOVED={
 '/Game/Dungeons/FacilityFlow20261007/Meshes/SM_FacilityFlow_OuterWalls',
 '/Game/Dungeons/FacilityFlow20261007/Meshes/SM_FacilityFlow_BreachRebar',
 '/Game/Dungeons/FacilityFlow20261007/EntryPolish20261008/Meshes/SM_EntryPolish_BreachAggregate_UV2'}

def manifest():return json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']

def lamp_rows():
    old=runpy.run_path(str(GROUND));rows=old['fixtures']()
    for row in rows:
        pos=row['anchor'];pos[1]=1325. if pos[1]>0 else -1325.;pos[2]=389.3
        if row['id'].endswith('stair_approach'):pos[0]=-200.
        row['light']['position']=[pos[0],pos[1],377.8]
        row['light']['fixture_anchor_cm']=pos
    row=copy.deepcopy(rows[0]);row['id']='GroundContinuity_MainDoor'
    row['anchor']=[-2290.,0.,391.]
    row['light'].update(id=row['id'],position=[-2290.,0.,379.5],fixture_anchor_cm=row['anchor'],
        yaw=90.,intensity=400.,radius=650.,optimized_radius_cm=650.)
    row['fixture_yaw']=90.
    rows.append(row)
    return rows

def apply_module(module):
    if module['id']!=MODULE:return
    ground=runpy.run_path(str(GROUND))
    module['parts']=[p for p in module['parts'] if p['mesh'] not in REMOVED and not p['mesh'].startswith(BASE+'/') and not ground['is_added'](p)]
    module['lights']=[p for p in module['lights'] if not ground['is_added'](p)]
    for item in manifest():
        module['parts'].append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],
            collision=item['collision'],cast_shadow=item['cast_shadow'],materials=[],fluid=False,finish_revision=REVISION))
    for row in lamp_rows():
        module['lights'].append(copy.deepcopy(row['light']))
        module['parts'].append(dict(id=row['id']+'_Fixture',mesh=ground['MESH'],position=row['anchor'],
            yaw=row.get('fixture_yaw',0.),scale=[1,1,1],collision=False,cast_shadow=True,fluid=False,
            materials=ground['MATERIALS'],ground_continuity_revision=ground['REVISION'],finish_revision=REVISION))
    for part in module['parts']:
        if part.get('fixture_id')=='FacilityReceptionHall.vent.03':
            if part['mesh'].endswith('VentCompactBody'):part['position']=[-540.,-1581.,412.]
            elif part['mesh'].endswith('VentCompactLeaf'):part['position']=[-598.5,-1581.,280.]
    assets={item['mesh'] for item in manifest()}|{v for item in manifest() for v in item['materials'].values()}
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-REMOVED)|assets|{ground['MESH'],*ground['MATERIALS']})
    module['finish_revision']=REVISION

def installed():
    p=ROOT/'Receipts/install.json'
    return p.exists() and json.loads(p.read_text('utf8')).get('stage')=='maps_saved'

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog);apply_module(next(m for m in out['modules'] if m['id']==MODULE))
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out)
    return out

def apply_subject(world):
    import unreal as u
    ground=runpy.run_path(str(GROUND))
    if world.get_path_name().split('.')[0] not in ground['SUBJECTS']:return {}
    # Reuse the fixture binding implementation with this final seven-lamp layout.
    # Only supplemental lamps are touched; all 23 older lamps stay unchanged.
    apply=ground['apply_subject'];apply.__globals__['fixtures']=lamp_rows
    lights=apply(world)
    aa=u.get_editor_subsystem(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    label='Reception_GroundContinuity_MainDoor'
    actors[label].set_actor_rotation(u.Rotator(pitch=-90,yaw=90,roll=90),True)
    fixture=actors[label+'_Fixture'];fixture.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    fixture.set_actor_rotation(u.Rotator(yaw=90),True);fixture.static_mesh_component.set_mobility(u.ComponentMobility.STATIC)
    has_breach=False;has_vent=False
    # These walkthroughs may still use their original intact shell. Do not cut
    # a new portal in a subject that has no production entrance passage.
    for a in list(actors.values()):
        for component in a.get_components_by_class(u.StaticMeshComponent):
            if not component.static_mesh:continue
            path=component.static_mesh.get_path_name().split('.')[0]
            if path in REMOVED:
                has_breach=True
                if path.endswith('SM_FacilityFlow_OuterWalls'):
                    component.modify();component.set_static_mesh(u.load_asset(BASE+'/Meshes/SM_ReceptionFinish_OuterWalls'))
                else:
                    component.modify();component.set_visibility(False);component.set_hidden_in_game(True)
                    component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            if path.endswith('SM_Entry_VentCompactBody') and abs(component.get_world_location().x+540)<2:
                has_vent=True;a.modify();component.set_mobility(u.ComponentMobility.MOVABLE)
                a.set_actor_location(u.Vector(-540,-1581,412),False,True)
                component.set_mobility(u.ComponentMobility.STATIC)
            elif path.endswith('SM_Entry_VentCompactLeaf') and abs(component.get_world_location().x+598.5)<2:
                a.modify();component.set_mobility(u.ComponentMobility.MOVABLE)
                a.set_actor_location(u.Vector(-598.5,-1581,280),False,True)
                component.set_mobility(u.ComponentMobility.STATIC)
    added=[]
    for item in manifest():
        if item['kind']=='OuterWalls':continue
        if item['kind'].startswith('Breach') and not has_breach:continue
        if item['kind']=='VentMounts' and not has_vent:continue
        name='Reception_Finish_'+item['kind'];a=actors.get(name)
        if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(),u.Rotator());a.set_actor_label(name)
        a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(u.load_asset(item['mesh']))
        c.set_mobility(u.ComponentMobility.STATIC);c.set_cast_shadow(item['cast_shadow'])
        c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
        c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if item['collision'] else u.CollisionEnabled.NO_COLLISION)
        a.set_folder_path('Reception/Finish20261010');a.set_editor_property('tags',[REVISION,'Reception.Subject'])
        added.append(name)
    return dict(lights=lights,added=added,production_breach_present=has_breach,vent_present=has_vent)
