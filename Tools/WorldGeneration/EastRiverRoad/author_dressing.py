"""Prepare roadside hazel with the approved wind slots and two feathered ground decals."""
from pathlib import Path
import json
import os
import unreal as u

out='/Game/WorldGeneration/TemperateHills/EastRiverRoad'
lib=u.EditorAssetLibrary
ed=u.MaterialEditingLibrary
lib.make_directory(out)
def asset(path):
    o=u.load_asset(path)
    if not o: raise RuntimeError(path)
    return o
def save(o):
    if not lib.save_loaded_asset(o,False):raise RuntimeError(o.get_path_name())
slots=json.loads(Path(os.environ['EAST_ROAD_WINDSLOTS']).read_text(encoding='utf-8-sig'))
for name, materials in slots.items():
    if 'Hazel' not in name:continue
    target=out+'/'+name
    mesh=asset(target) if lib.does_asset_exist(target) else lib.duplicate_asset('/Game/CommonHazel/Geometry/SimpleWind/'+name,target)
    for i,material in enumerate(materials):
        mesh.set_material(i,asset(material))
    save(mesh)
def wire(src,pin,target,slot):
    if not ed.connect_material_expressions(src,pin,target,slot):raise RuntimeError(slot)
for label,group in [('Moss','NordicMoss'),('Soil','NordicForestGroundRootsCoarse')]:
    name='M_EastRoad_'+label+'Patch'
    obj=asset(out+'/'+name) if lib.does_asset_exist(out+'/'+name) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,out,u.Material,u.MaterialFactoryNew())
    ed.delete_all_material_expressions(obj)
    obj.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    obj.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(cls,x,y):return ed.create_material_expression(obj,cls,x,y)
    uv=node(u.MaterialExpressionTextureCoordinate,-800,80)
    color=node(u.MaterialExpressionTextureSample,-420,0)
    color.set_editor_property('texture',asset('/Game/ForestPathStudy/Materials/T_'+group+'_BaseColor'))
    normal=node(u.MaterialExpressionTextureSample,-420,220)
    normal.set_editor_property('texture',asset('/Game/ForestPathStudy/Materials/T_'+group+'_Normal'))
    normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    alpha=node(u.MaterialExpressionCustom,-420,410)
    alpha.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    alpha.set_editor_property('code','float2 p=UV*2-1; float edge=length(p)+0.07*sin(12*p.x+3*p.y)+0.08*cos(11*p.y-2*p.x); return 0.66*(1-smoothstep(0.51,0.96,edge));')
    inp=u.CustomInput()
    inp.set_editor_property('input_name','UV')
    alpha.set_editor_property('inputs',[inp])
    wire(uv,'',alpha,'UV')
    for src,pin,prop in [(alpha,'',u.MaterialProperty.MP_OPACITY),(color,'RGB',u.MaterialProperty.MP_BASE_COLOR),(normal,'RGB',u.MaterialProperty.MP_NORMAL)]:
        if not ed.connect_material_property(src,pin,prop):raise RuntimeError(str(prop))
    ed.recompile_material(obj)
    save(obj)
