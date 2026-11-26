import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HeadQualityR2')
out.mkdir(parents=True,exist_ok=True)
base='/Game/Characters/ChapelNun20261115/'
report={}
for name in ('Nun_LowBun_Core','Nun_LowBun_Loose'):
    groom=u.load_asset(base+'Grooms/'+name)
    item={}
    for field in ('hair_groups_info','hair_groups_rendering','hair_groups_interpolation','hair_groups_lod','hair_groups_physics','hair_groups_materials','asset_import_data','enable_global_interpolation','rigged_skeletal_mesh'):
        try:
            value=groom.get_editor_property(field)
            item[field]=[x.export_text() for x in value] if isinstance(value,u.Array) else str(value)
        except Exception as e: item[field]={'unavailable':str(e)}
    binding=u.load_asset(base+'Grooms/'+name+'_Binding')
    item['binding']={}
    for field in ('groom','target_skeletal_mesh','source_skeletal_mesh','num_interpolation_points','matching_section','group_infos'):
        try:
            value=binding.get_editor_property(field)
            item['binding'][field]=[x.export_text() for x in value] if isinstance(value,u.Array) else str(value)
        except Exception as e: item['binding'][field]={'unavailable':str(e)}
    report[name]=item
for channel in ('base_color','normal','roughness'):
    tex=u.load_asset(base+'Textures/T_NunHead_'+channel)
    item={}
    for field in ('srgb','compression_settings','flip_green_channel','lod_group','lod_bias','max_texture_size','never_stream','filter','virtual_texture_streaming'):
        try: item[field]=str(tex.get_editor_property(field))
        except Exception as e: item[field]={'unavailable':str(e)}
    item['dimensions']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
    report[channel]=item
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report['current_world']=world.get_path_name() if world else None
(out/'engine_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
