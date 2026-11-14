from pathlib import Path
import json,runpy,unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    ctx=runpy.run_path(str(R/'install.py'))
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.get_actor_label()=='StationLine_AbandonedTransitStation_6')
    mat=actor.static_mesh_component.get_material(1);mesh=ctx['meshimport']('SM_CeramicRepairs')
    mesh.modify();mesh.set_material(0,mat)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Repair face asset not saved')
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    a=next((a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.get_actor_label()=='OppositePlatform_CeramicRepairs'),None)
    if not a:
        a=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(6174,-3036,0),u.Rotator());a.set_actor_label('OppositePlatform_CeramicRepairs');a.set_folder_path('StationLine/OppositePlatform')
    c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh);c.set_material(0,mat);c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False);c.set_cast_shadow(False)
    return {'material':mat.get_path_name(),'cells':len(json.loads((R/'tile-plan.json').read_text('utf8'))['patches'])}
