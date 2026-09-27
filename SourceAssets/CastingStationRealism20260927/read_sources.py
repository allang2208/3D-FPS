from pathlib import Path
import json
import unreal as u
paths=['/Game/Props/CastingStation20260926/SM_CastingStation',
 '/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A',
 '/Game/UnrealNormandy/MaterialInstances/MI_Wood_00B',
 '/Game/Clearwater/MI_ClearwaterWater']
result={}
for path in paths:
    a=u.load_asset(path)
    if not a: raise RuntimeError('Missing '+path)
    if isinstance(a,u.StaticMesh):
        result[path]={'slots':[(str(s.material_slot_name),s.material_interface.get_path_name() if s.material_interface else '') for s in a.static_materials],
          'sockets':{n:str(a.find_socket(n).relative_location) for n in ['AnvilFace','QuenchSurface'] if a.find_socket(n)}}
    else:
        result[path]={'parent':str(a.parent),
          'textures':[(str(p.parameter_info.name),str(p.parameter_value)) for p in a.texture_parameter_values],
          'scalars':[(str(p.parameter_info.name),p.parameter_value) for p in a.scalar_parameter_values],
          'vectors':[(str(p.parameter_info.name),str(p.parameter_value)) for p in a.vector_parameter_values]}
out=Path(u.Paths.project_dir())/'SourceAssets/CastingStationRealism20260927/sources.json'
out.write_text(json.dumps(result,indent=2),encoding='utf8')
print('CASTING_SOURCE_READ '+json.dumps(result))
