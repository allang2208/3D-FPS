import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestAtmosphere20261110')
BASE='/Game/WorldGeneration/TemperateHills'
lib=u.MaterialEditingLibrary
r={'wind':{},'materials':{},'api':{}}
da=u.load_asset(BASE+'/DA_TemperateHillsStreaming')
for role in ('trees','forest_saplings','forest_ferns'):
    m=u.load_asset(da.get_editor_property(role)[-1].get_path_name())
    for data in m.get_editor_property('asset_user_data'):
        if data and data.get_class().get_name()=='DynamicWindSkeletalData':
            r['wind'][role]={}
            for p in ('bIsEnabled','bIsGroundCover','GustAttenuation','SimulationGroups'):
                try:r['wind'][role][p]=str(data.get_editor_property(p))
                except Exception as e:r['wind'][role][p]=str(e)
for path in (BASE+'/ForestSpecies20261110/Materials/M_ForestPCG',BASE+'/MI_ValleyLowFog'):
    m=u.load_asset(path)
    if isinstance(m,u.Material):
        n=lib.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        r['materials'][path]={'wpo':n.get_path_name() if n else None,'wpo_output':lib.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)}
    else:r['materials'][path]={'scalars':{str(p):lib.get_material_instance_scalar_parameter_value(m,p) for p in lib.get_scalar_parameter_names(m)}}
for name in ('DynamicWindData','MaterialParameterCollectionFactoryNew','MaterialExpressionTransformPosition','MaterialExpressionObjectBounds'):
    r['api'][name]=str(getattr(u,name,None))
for name in ('transform_provider','asset_user_data'):
    pass
sky=u.get_default_object(u.load_class(None,'/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C'))
for p in ('Speed Up','Speed Down','Auto Exposure Speed Up','Auto Exposure Speed Down','Exposure Speed Up','Exposure Speed Down'):
    try:r[p]=str(sky.get_editor_property(p))
    except Exception:pass
(ROOT/'authoring_details.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
u.log('FOREST_ATMOSPHERE_DETAILS_READ')
