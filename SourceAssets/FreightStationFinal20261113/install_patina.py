from pathlib import Path
import json,runpy
import unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    tile=actors['StationLine_AbandonedTransitStation_6'];tile.modify();tile.static_mesh_component.modify()
    tile.static_mesh_component.set_static_mesh(u.load_asset('/Game/SceneTests/FreightOppositePlatform20261113/Meshes/SM_StationTiles_WestRepair'))
    src=(R.parent/'FreightStationSurfaces20261113/install_ground.py').read_text('utf8').replace("ROOT/'Textures'","ROOT/'PatinaTextures'")
    env={'__file__':str(R/'install_patina.py')};exec(compile(src,'patina_assets','exec'),env)
    env.update(ROOT=R,BASE='/Game/SceneTests/FreightStationFinal20261113/SkirtPatina')
    rows=json.loads((R/'skirt-plan.json').read_text('utf8'));mi=env['instances']([{'texture':r['name']} for r in rows])
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    used=[]
    for row in rows:
        if not row['clusters']:continue
        label='StationFinal_'+row['name']
        a=actors.get(label) or api.spawn_actor_from_class(u.DecalActor,u.Vector(*row['pos']),u.Rotator(yaw=row['yaw']))
        a.set_actor_label(label);a.set_folder_path('StationLine/StationSurface/SkirtPatina')
        c=a.get_component_by_class(u.DecalComponent);a.modify();c.modify()
        c.set_decal_material(mi[row['name']]);c.set_editor_property('decal_size',u.Vector(*row['size']))
        c.set_editor_property('sort_order',7);c.set_editor_property('fade_screen_size',.001)
        used.append({'name':row['name'],'clusters':row['clusters']})
    return {'original_ceramic_mesh_retained':True,'local_patina':used}
