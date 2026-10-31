"""District-only render/physics policy shared by production and later rebuilds."""
import math
def settings(mesh_path,mesh,transforms):
    hidden='/Repair/Collision/' in mesh_path
    continuous='/Performance/Meshes/SM_ContinuousRoad_' in mesh_path
    decal=any(k in mesh_path for k in ['SM_White_Line','SM_Yellow_Line','SM_Painted_Parking_Line'])
    road_tile='SM_Lane_Car_' in mesh_path
    walk=any(k in mesh_path for k in ['Sidewalk','Modular_Curb','SM_Plaza_Square'])
    street=any(k in mesh_path for k in ['StreetLamp','Parking_Meter','Road_Sign','Hydrant','Mailbox'])
    solid=hidden or walk or street or 'BlackAlder' in mesh_path or '/Meshes/ParkGround' in mesh_path
    detail=any(k in mesh_path for k in ['roof_','Roof_','Kit_antenna','Kit_Prop_AC','Kit_Prop_Firehose'])
    b=mesh.get_bounding_box();size=max(b.max.x-b.min.x,b.max.y-b.min.y,b.max.z-b.min.z)
    scale=max((max(abs(x) for x in t['s']) for t in transforms),default=1)
    end=0
    if detail:end=math.ceil(min(100000,max(18000,size*scale*100))/100)*100
    elif decal:end=45000
    elif '/Vehicle/' in mesh_path:end=60000
    elif 'StreetLamp' in mesh_path:end=80000
    elif any(k in mesh_path for k in ['Parking_Meter','Road_Sign','Hydrant','Mailbox']):end=25000
    elif 'FireEscape' in mesh_path:end=80000
    # Solid collision proxies remain available independently of visual draw distance.
    return dict(hidden=hidden,solid=solid,cast_shadow=not(hidden or continuous or decal or road_tile),cull_start=int(end*.85),cull_end=end,navigation=solid,overlaps=False,raytracing=not hidden)

def apply(component,mesh_path,mesh,transforms):
    p=settings(mesh_path,mesh,transforms)
    component.set_collision_profile_name('BlockAll' if p['solid'] else 'NoCollision')
    component.set_editor_property('generate_overlap_events',False)
    component.set_editor_property('can_ever_affect_navigation',p['navigation'])
    component.set_visibility(not p['hidden']);component.set_hidden_in_game(p['hidden'])
    component.set_editor_property('cast_shadow',p['cast_shadow'])
    component.set_editor_property('visible_in_ray_tracing',p['raytracing'])
    component.set_editor_property('affect_distance_field_lighting',False)
    component.set_cull_distances(p['cull_start'],p['cull_end'])
    return p
