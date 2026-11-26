"""Install the road comparison in the village-only material function."""
from pathlib import Path
import os
import unreal as u

ed=u.MaterialEditingLibrary
lib=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
recipe=Path(__file__).resolve().parent
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
ref='/Game/ForestPathStudy/VillageRegion/Reference'
out=ref+'/GateRoad'
lib.make_directory(out)

def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError(asset.get_path_name())

def import_texture(name,kind,srgb,filter_field=False):
    task=u.AssetImportTask()
    task.filename=str(src/(name+'.png'));task.destination_path=out;task.destination_name=name
    task.replace_existing=True;task.automated=True
    tools.import_asset_tasks([task])
    tex=u.load_asset(out+'/'+name)
    if not tex:raise RuntimeError(name)
    tex.set_editor_property('srgb',srgb)
    tex.set_editor_property('compression_settings',kind)
    for key in ('address_x','address_y'):tex.set_editor_property(key,u.TextureAddress.TA_CLAMP)
    if filter_field:tex.set_editor_property('compression_no_alpha',False)
    save(tex)
    return tex

def node(cls):return ed.create_material_expression_in_function(fn,cls)

def collection_node(coll,name):
    expr=node(u.MaterialExpressionCollectionParameter)
    expr.set_editor_property('collection',coll)
    expr.set_editor_property('parameter_name',name)
    return expr

def connect(expr,channel,custom,pin):
    if not ed.connect_material_expressions(expr,channel,custom,pin):raise RuntimeError(pin)

assets={}
k=u.TextureCompressionSettings
for pin,name,kind,color,sampler in [('Wear','T_RoadWearField',k.TC_BC7,False,'LINEAR_COLOR'),
                                    ('PalColor','T_RoadPaletteColor',k.TC_DEFAULT,True,'COLOR'),
                                    ('PalNormal','T_RoadPaletteNormal',k.TC_NORMALMAP,False,'NORMAL'),
                                    ('PalData','T_RoadPaletteData',k.TC_MASKS,False,'MASKS')]:
    assets[pin]=(import_texture(name,kind,color,pin=='Wear'),sampler)
mpc=u.load_asset(out+'/MPC_GateRoad') if lib.does_asset_exist(out+'/MPC_GateRoad') else tools.create_asset('MPC_GateRoad',out,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
values=list(mpc.get_editor_property('scalar_parameters'))
index=next((i for i,p in enumerate(values) if str(p.get_editor_property('parameter_name'))=='RoadLook'),len(values))
if index==len(values):values.append(u.CollectionScalarParameter())
value=values[index]
value.set_editor_property('parameter_name','RoadLook')
value.set_editor_property('default_value',3.)
values[index]=value
mpc.set_editor_property('scalar_parameters',values)
save(mpc)

fn=u.load_asset(ref+'/MF_TrailDirt')
custom=next(n for n in ed.get_material_function_expressions(fn) if str(n.get_editor_property('desc'))=='R21 independent soil and moss')
pins=list(custom.get_editor_property('inputs'))
known={str(i.get_editor_property('input_name')) for i in pins}
for name in [*assets,'Look','RainWetness']:
    if name not in known:
        extra=u.CustomInput()
        extra.set_editor_property('input_name',name)
        pins.append(extra)
custom.set_editor_property('inputs',pins)
nodes=ed.get_material_function_expressions(fn)
for pin,(texture,kind) in assets.items():
    tag='Gate road '+pin
    expr=next((e for e in nodes if str(e.get_editor_property('desc'))==tag),None)
    if not expr:expr=node(u.MaterialExpressionTextureObject)
    expr.set_editor_property('desc',tag)
    expr.set_editor_property('texture',texture)
    expr.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
    connect(expr,'',custom,pin)
for pin,collection,parameter in [('Look',mpc,'RoadLook'),('RainWetness',u.load_asset('/Game/Weather/Materials/MPC_FPS_Weather'),'WeatherWetness')]:
    expr=next((e for e in nodes if str(e.get_editor_property('desc'))=='Gate road '+pin),None)
    if not expr:expr=collection_node(collection,parameter)
    expr.set_editor_property('desc','Gate road '+pin)
    connect(expr,'',custom,pin)
original=(recipe/'trail_soil.ush').read_text(encoding='utf-8-sig')
if original.count('return color;')!=1:raise RuntimeError('Unexpected trail outputs')
blend="""RoadNormal=normalize(lerp(RoadNormal,compactNormal,roadMix));
RoadRoughness=lerp(RoadRoughness,compactData.g,roadMix);
RoadAO=lerp(RoadAO,compactData.r,roadMix);
RoadHeight=lerp(RoadHeight,compactData.b,roadMix);
return lerp(color,compactColor,roadMix);"""
code=(recipe/'gate_road_surface.ush').read_text(encoding='utf-8-sig')+'\n'+original.replace('return color;',blend)
if lib.does_asset_exist(out+'/RoadMix/T_RoadMixField'):
    import sys
    sys.path.insert(0,str(recipe))
    from author_forest_road_mix import bind
    code=bind(fn,custom,code)
custom.set_editor_property('code',code)
ed.update_material_function(fn)
for path in (ref+'/M_ForestReferenceMesh',ref+'/TrailCover/M_ForestVillageLandscape'):
    errors=ed.recompile_material(u.load_asset(path))
    if errors:raise RuntimeError(str(errors))
save(fn)
(batch/'authored.txt').write_text(fn.get_path_name(),encoding='utf-8')
