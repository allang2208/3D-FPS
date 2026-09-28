"""Read the reported coverage/material failure in the user's running world."""
import unreal as u,json
from pathlib import Path
e=u.get_editor_subsystem(u.UnrealEditorSubsystem);w=e.get_game_world() or e.get_editor_world()
out={'world':str(w),'actors':[],'textures':{}}
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    clouds=a.get_components_by_class(u.VolumetricCloudComponent)
    if 'GodSpaceDistant' in a.get_actor_label() or clouds:
        row={'name':a.get_actor_label(),'location':str(a.get_actor_location()),'scale':str(a.get_actor_scale3d())}
        for c in a.get_components_by_class(u.StaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if mesh:row['mesh']={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounding_box()),'materials':[str(c.get_material(i)) for i in range(c.get_num_materials())]}
        if clouds:
            c=clouds[0];row['cloud']={p:str(c.get_editor_property(p)) for p in ['layer_bottom_altitude','layer_height','tracing_max_distance','visible']}
            row['cloud']['material']=str(c.get_editor_property('material'))
            row['atmosphere']=[{'relative_location':str(x.get_editor_property('relative_location')),'mode':str(x.get_editor_property('transform_mode')),'ground_radius':x.get_editor_property('bottom_radius')} for x in a.get_components_by_class(u.SkyAtmosphereComponent)]
        out['actors'].append(row)
for name in ['T_Ocean_Waves01_Normals','T_Ocean_Waves02_Normals','T_Ocean_Foam']:
    t=u.load_asset('/Game/WaterMaterials/Textures/'+name)
    out['textures'][name]={p:str(t.get_editor_property(p)) for p in ['srgb','compression_settings','lod_group']}
(Path(__file__).parent/'Receipts/ocean-v2-inputs.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out))
