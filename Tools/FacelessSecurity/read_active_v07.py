"""Read only the guard mesh currently used by the Blueprint and PIE actors."""
import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V07');root.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cls=bp.generated_class();cdo=u.get_default_object(cls)
def describe(actor):
    parts=[]
    for component in actor.get_components_by_class(u.MeshComponent):
        row={'name':component.get_name(),'type':component.get_class().get_name()}
        if isinstance(component,u.SkeletalMeshComponent):
            mesh=component.get_skeletal_mesh_asset();row['mesh']=mesh.get_path_name() if mesh else None
        elif isinstance(component,u.StaticMeshComponent):
            mesh=component.get_editor_property('static_mesh');row['mesh']=mesh.get_path_name() if mesh else None
        parts.append(row)
    return {'actor':actor.get_path_name(),'visual_mesh':actor.get_editor_property('visual_mesh').get_path_name(),'components':parts}
report={'blueprint':describe(cdo),'pie_actors':[]}
for world in u.EditorLevelLibrary.get_pie_worlds(False):
    for actor in u.GameplayStatics.get_all_actors_of_class(world,cls):report['pie_actors'].append(describe(actor))
(root/'active_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_V07_ACTIVE '+json.dumps(report),flush=True)
