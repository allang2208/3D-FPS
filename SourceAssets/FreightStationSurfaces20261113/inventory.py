from pathlib import Path
import unreal as u
def apply(w):
    result=[]
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor):
        c=a.static_mesh_component
        if not c.static_mesh:continue
        p,e=a.get_actor_bounds(False)
        if p.x+e.x<5400:continue
        result.append(dict(label=a.get_actor_label(),name=a.get_name(),folder=str(a.get_folder_path()),mesh=c.static_mesh.get_path_name(),p=c.get_world_location().to_tuple(),rot=c.get_world_rotation().to_tuple(),s=c.get_world_scale().to_tuple(),center=p.to_tuple(),ext=e.to_tuple(),hidden=bool(a.is_hidden_ed()),visible=c.get_editor_property('visible'),slots=[str(m.get_path_name()) if m else '' for m in c.get_materials()]))
    return result
