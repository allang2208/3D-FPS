"""Read the actual donors needed to author the three living-area employees."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/StaffLivingEmployees20261017')
report={'characters':{},'body_meshes':{},'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
props=['max_health','attack_damage','walk_speed','level','rank','experience_reward','aggro_radius','attack_range','contact_time','contact_end','recovery_time','corpse_seconds']
for role in ['NurseZombie','FacelessSecurity','FacelessReceptionist','FacelessResearcher']:
    bp=u.load_asset('/Game/Monsters/'+role+'/BP_'+role)
    cdo=u.get_default_object(bp.generated_class())
    mesh=cdo.get_editor_property('mesh')
    row={'blueprint':bp.get_path_name(),'tags':[str(t) for t in cdo.get_editor_property('tags')],'stats':{},'clips':{},'components':[]}
    for prop in props:
        value=cdo.get_editor_property(prop)
        row['stats'][prop]=value if isinstance(value,(int,float,str)) else str(value)
    row['visual_mesh']=cdo.get_editor_property('visual_mesh').get_path_name()
    row['mesh_location']=str(mesh.get_editor_property('relative_location'))
    row['mesh_scale']=str(mesh.get_editor_property('relative_scale3d'))
    for prop in ['idle_clip','walk_clip','attack_clip']:
        clip=cdo.get_editor_property(prop);row['clips'][prop]={'path':clip.get_path_name(),'rate':clip.get_editor_property('rate_scale')}
    for group,fields in [('combat',['hit_clip','dizzy_clip']),('knockdown',['fall_clip','get_up_clip','prone_get_up_clip'])]:
        obj=cdo.get_editor_property(group)
        for field in fields:
            clip=obj.get_editor_property(field);row['clips'][group+'.'+field]=clip.get_path_name() if clip else None
    subsystem=u.get_engine_subsystem(u.SubobjectDataSubsystem);library=u.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj=library.get_object_for_blueprint(library.get_data(handle),bp)
        if obj:row['components'].append({'name':obj.get_name(),'type':obj.get_class().get_name()})
    report['characters'][role]=row
for role,name in [('FacelessSecurity','SK_FacelessSecurity_Body_V09'),('FacelessReceptionist','SK_FacelessReceptionist_Body_V04'),('FacelessResearcher','SK_FacelessResearcher_Body_V01')]:
    mesh=u.load_asset('/Game/Monsters/'+role+'/'+name)
    if not mesh:raise RuntimeError('Missing original body '+name)
    report['body_meshes'][role]={'path':mesh.get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),'physics_asset':mesh.get_editor_property('physics_asset').get_path_name() if mesh.get_editor_property('physics_asset') else None,'materials':[m.material_interface.get_path_name() if m.material_interface else None for m in mesh.get_editor_property('materials')]}
(ROOT/'source_inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
