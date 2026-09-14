"""Adapt Epic's downloaded Chromium material to the existing 715 and rain contract.

Authors only this revision. Source materials, meshes, textures and animations stay intact.
Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -unattended -nullrhi.
"""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
ROOT = O.parents[1]
D = '/Game/Weapons/DanWesson715/Chrome20260914'
EPIC = '/Game/SubstrateMaterials/Materials'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
detail = json.loads((O.parent/'DanWesson715Detail20260914/import.json').read_text())
mirror = json.loads((O.parent/'DanWesson715Mirror20260914/import.json').read_text())
source = u.load_asset(EPIC+'/03_Metals/1_Basic/MI_Chromium')
if not source: raise RuntimeError('Downloaded Epic MI_Chromium is required')
receipt = {'source': source.get_path_name(), 'materials': {}, 'attachments': {}, 'wet_materials': {}}
wetmaps = {}

def save(obj):
    if not E.save_loaded_asset(obj, False): raise RuntimeError('Save failed: '+obj.get_path_name())
    return obj

def duplicate(src, dest):
    obj = u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(src,dest)
    if not obj: raise RuntimeError('Duplicate failed: '+dest)
    return obj

def node(owner, cls):
    return L.create_material_expression(owner,cls) if isinstance(owner,u.Material) else L.create_material_expression_in_function(owner,cls)

def wire(src, dst, pin, output=''):
    if isinstance(src,tuple): src, output = src
    if not L.connect_material_expressions(src,output,dst,pin): raise RuntimeError('Cannot connect '+dst.get_name()+':'+pin)

def prop(src, name, output=''):
    if isinstance(src,tuple): src, output = src
    if not L.connect_material_property(src,output,getattr(u.MaterialProperty,'MP_'+name)): raise RuntimeError('Cannot connect material '+name)

def scalar(owner,name,value):
    n=node(owner,u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name',name); n.set_editor_property('default_value',value)
    return n

def constant(owner,value):
    n=node(owner,u.MaterialExpressionConstant); n.set_editor_property('r',value); return n

def custom(owner,code,inputs,kind,label):
    n=node(owner,u.MaterialExpressionCustom)
    n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(kind)))
    n.set_editor_property('description',label)
    entries=[]
    for name in inputs:
        item=u.CustomInput(); item.set_editor_property('input_name',name); entries.append(item)
    n.set_editor_property('inputs',entries)
    for name,src in inputs.items(): wire(src,n,name)
    return n

def sample(owner,name,path,normal=False):
    n=node(owner,u.MaterialExpressionTextureSampleParameter2D)
    n.set_editor_property('parameter_name',name); n.set_editor_property('texture',u.load_asset(path))
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    wire(node(owner,u.MaterialExpressionTextureCoordinate),n,'UVs')
    return n

def call(owner,fn):
    n=node(owner,u.MaterialExpressionMaterialFunctionCall); n.set_editor_property('material_function',fn); return n

def beads(owner):
    return custom(owner,(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),
        {'UV':node(owner,u.MaterialExpressionTextureCoordinate),'Wet':scalar(owner,'WeaponWetness',0)},4,'715 rain beads in gun UV0')

def apply_params(mi, values, category):
    setter=getattr(L,'set_material_instance_'+category+'_parameter_value')
    available={str(n) for n in getattr(L,'get_'+category+'_parameter_names')(mi)}
    for name,value in values.items():
        # UE 5.8's setters apply the value but always return their initial false.
        # See MaterialEditingLibrary.cpp, SetMaterialInstance*ParameterValue.
        if name in available: setter(mi,name,value)

# Flatten the actual effective preset, including its template's overrides, before reparenting.
source_params={}
for category in ('scalar','vector','texture','static_switch'):
    source_params[category]={str(n):getattr(L,'get_material_instance_'+category+'_parameter_value')(source,n)
        for n in getattr(L,'get_'+category+'_parameter_names')(source)}
chrome_color=source_params['vector']['Metallic Color A']

def instance(parent,name,folder=D+'/Materials',normal=None,orm=None,rough=.025,old_base=.045):
    mi=duplicate(source.get_path_name(),folder+'/'+name)
    L.set_material_instance_parent(mi,parent)
    for category,values in source_params.items(): apply_params(mi,values,category)
    apply_params(mi,{'Use Geo UV':True},'static_switch')
    apply_params(mi,{'Use Fingerprints':0,'Use Dust':0,'Use Scratches':0,'Use Emissive':0,
        'Use Opacity Mask':0,'Use Metallic Thin Film':0,'Use Imperfections Debug':0,
        'Normal Map Strength':1,'Normal Map Channel Flip':0,'UV Index':0,'Tile U':1,'Tile V':1,
        'Tile Uniform Scale':1,'Rotation':0,'Offset U':0,'Offset V':0,'Dithering':0,
        'Secondary Roughness Weight':0,'WeaponWetness':0,'Chrome Roughness':rough,
        'Previous Surface Base':old_base,'Structural Roughness Amount':.35},'scalar')
    apply_params(mi,{'Metallic Color A':chrome_color,'Metallic Color B':chrome_color,
        'Primary Roughness Control':u.LinearColor(rough,rough,1,0),
        'Anisotropy Strength Variation Control':u.LinearColor(0,0,1,0)},'vector')
    textures={}
    if normal: textures['Normal Map']=u.load_asset(normal)
    if orm: textures['DW715 Surface ORM']=u.load_asset(orm)
    apply_params(mi,textures,'texture')
    E.set_metadata_tag(mi,'FabSource',source.get_path_name())
    L.update_material_instance(mi); save(mi)
    return mi

# Keep Epic's native metallic BSDF, F0/F90 pipeline and material graph.
# Only this local function copy receives gun-specific roughness and wet normal inputs.
fn=duplicate(EPIC+'/00_MaterialFunctions/MFW_Aniso_BaseMetal',D+'/Functions/MF_DW715_ChromeMetal')
if not E.get_metadata_tag(fn,'DW715ChromeAuthored'):
    nodes={n.get_name():n for n in L.get_material_function_expressions(fn)}
    slab=nodes['MaterialExpressionSubstrateSlabBSDF_0']
    surface=sample(fn,'DW715 Surface ORM',detail['textures']['Frame']['ORM'])
    rough=custom(fn,'return clamp(Base+max(0,Surface.g-Previous)*Amount,.008,.24);',
        {'Base':scalar(fn,'Chrome Roughness',.025),'Surface':(surface,'RGB'),
         'Previous':scalar(fn,'Previous Surface Base',.045),'Amount':scalar(fn,'Structural Roughness Amount',.35)},1,'Clean chrome with local structural contrast')
    data=beads(fn)
    wet_rough=custom(fn,'return lerp(lerp(Base,max(.012,Base*.72),Data.a),.035,Data.b*.8);',
        {'Base':rough,'Data':data},1,'Chrome wet roughness')
    wet_normal=custom(fn,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',
        {'Base':nodes['MaterialExpressionMaterialFunctionCall_4'],'Data':data},3,'Chrome wet structural normal')
    wire(wet_rough,slab,'Roughness'); wire(wet_normal,slab,'Normal')
    E.set_metadata_tag(fn,'DW715ChromeAuthored','1')
    L.update_material_function(fn); save(fn)

master=duplicate(EPIC+'/00_ParentMaterials/M_Metallic',D+'/Materials/M_DW715_Chrome')
if not E.get_metadata_tag(master,'DW715ChromeAuthored'):
    for n in L.get_material_expressions(master):
        if isinstance(n,u.MaterialExpressionMaterialFunctionCall):
            called=n.get_editor_property('material_function')
            if called and called.get_name()=='MFW_Aniso_BaseMetal': n.set_editor_property('material_function',fn)
    master.set_editor_property('tangent_space_normal',True)
    L.set_material_usage(master,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    surface=sample(master,'DW715 Surface ORM',detail['textures']['Frame']['ORM'])
    prop(surface,'AMBIENT_OCCLUSION','R')
    E.set_metadata_tag(master,'DW715ChromeAuthored','1')
    E.set_metadata_tag(master,'FabSource',EPIC+'/00_ParentMaterials/M_Metallic')
    L.recompile_material(master); save(master)

bindings={}
for group,rough,old in [('Frame',.025,.045),('Cylinder',.020,.035),('Steel',.034,.060)]:
    dry=instance(master,'MI_DW715_Chrome_'+group,normal=detail['textures'][group]['Normal'],orm=detail['textures'][group]['ORM'],rough=rough,old_base=old)
    wet=duplicate(dry.get_path_name(),D+'/Materials/'+dry.get_name()+'_Wet'); save(wet)
    bindings['M_DW715_Hero_'+group]=dry; wetmaps[dry.get_path_name()]=wet
    receipt['materials'][group]={'dry':dry.get_path_name(),'wet':wet.get_path_name(),'roughness':rough,
        'normal':detail['textures'][group]['Normal'],'orm':detail['textures'][group]['ORM']}
    u.log('DW715_CHROME_BODY_SAVED '+group)

mesh=duplicate(detail['mesh'],D+'/SK_DW715_Manny')
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):
    if str(slot.material_slot_name) in bindings: slot.material_interface=bindings[str(slot.material_slot_name)]; slots[i]=slot
mesh.set_editor_property('materials',slots); save(mesh); receipt['mesh']=mesh.get_path_name()

# Mixed optical/polymer materials keep their proven regional masks and legacy shading.
# Their metal branches use Epic's own metal-color function and the same clean Chrome finish.
attachment_map={}
for original in mirror['attachment_materials'].values():
    basename=original.split('.')[-1]
    parent=duplicate(original,D+'/Attachments/Parents/'+basename)
    if not E.get_metadata_tag(parent,'DW715ChromeAuthored'):
        expressions=list(L.get_material_expressions(parent))
        tile_color=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and n.texture.get_name()=='T_DW715_Mirror_Attachment_BaseColor')
        tile_orm=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and n.texture.get_name()=='T_DW715_Mirror_Attachment_ORM')
        coordinates=call(parent,u.load_asset(EPIC+'/00_MaterialFunctions/MF_MakeCoordinates'))
        metal_color=call(parent,u.load_asset(EPIC+'/00_MaterialFunctions/MFW_Metallic_BaseMetal_Color'))
        wire((coordinates,'UV'),metal_color,'UV'); wire((coordinates,'DXY'),metal_color,'DXY')
        rough=scalar(parent,'Chrome Roughness',.030)
        # All seven source materials use either a direct metal output or a metal B branch.
        if L.get_material_property_input_node(parent,u.MaterialProperty.MP_BASE_COLOR)==tile_color:
            prop(metal_color,'BASE_COLOR','Color'); prop(rough,'ROUGHNESS')
        else:
            for n in expressions:
                if not isinstance(n,u.MaterialExpressionLinearInterpolate): continue
                upstream=L.get_inputs_for_material_expression(parent,n)
                if len(upstream)>1 and upstream[1]==tile_color: wire((metal_color,'Color'),n,'B')
                if len(upstream)>1 and upstream[1]==tile_orm and n.get_name()=='MaterialExpressionLinearInterpolate_1': wire(rough,n,'B')
        E.set_metadata_tag(parent,'DW715ChromeAuthored','1'); L.recompile_material(parent); save(parent)
    dry=instance(parent,basename.replace('M_DW715_','MI_DW715_Chrome_'),folder=D+'/Attachments/Materials',rough=.030)
    wet_parent=duplicate(parent.get_path_name(),D+'/Attachments/Parents/'+basename+'_Wet')
    if not E.get_metadata_tag(wet_parent,'DW715ChromeWet'):
        inputs={}
        for name in ('BASE_COLOR','ROUGHNESS','NORMAL'):
            p=getattr(u.MaterialProperty,'MP_'+name)
            src=L.get_material_property_input_node(wet_parent,p)
            if src: inputs[name]=(src,L.get_material_property_input_node_output_name(wet_parent,p))
        data=beads(wet_parent)
        prop(custom(wet_parent,'return Base*(1-Data.a*.07);',{'Base':inputs['BASE_COLOR'],'Data':data},3,'Chrome attachment wet color'),'BASE_COLOR')
        prop(custom(wet_parent,'return lerp(lerp(Base,max(.012,Base*.72),Data.a),.035,Data.b*.8);',{'Base':inputs['ROUGHNESS'],'Data':data},1,'Chrome attachment wet roughness'),'ROUGHNESS')
        if 'NORMAL' not in inputs:
            flat=node(wet_parent,u.MaterialExpressionConstant3Vector); flat.set_editor_property('constant',u.LinearColor(0,0,1,1)); inputs['NORMAL']=flat
        prop(custom(wet_parent,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',{'Base':inputs['NORMAL'],'Data':data},3,'Chrome attachment wet normal'),'NORMAL')
        E.set_metadata_tag(wet_parent,'DW715ChromeWet','1'); L.recompile_material(wet_parent); save(wet_parent)
    wet=instance(wet_parent,dry.get_name()+'_Wet',folder=D+'/Attachments/Materials',rough=.030)
    attachment_map[original]=dry; wetmaps[dry.get_path_name()]=wet
    u.log('DW715_CHROME_ATTACHMENT_MATERIAL_SAVED '+basename)

for part,info in mirror['attachments'].items():
    dest=info['mesh'].split('.')[0].replace('/Mirror20260914/','/Chrome20260914/')
    part_mesh=duplicate(info['mesh'],dest)
    part_slots=part_mesh.get_editor_property('static_materials')
    for i,slot in enumerate(part_slots):
        original=info['slots'].get(str(slot.material_slot_name))
        if original in attachment_map: slot.material_interface=attachment_map[original]; part_slots[i]=slot
    part_mesh.set_editor_property('static_materials',part_slots); save(part_mesh)
    receipt['attachments'][part]={'mesh':part_mesh.get_path_name(),'source':info['mesh'],
        'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in part_slots}}

factory=u.DataAssetFactory(); factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
library=u.load_asset(D+'/DA_DW715_WetMaterials') if E.does_asset_exist(D+'/DA_DW715_WetMaterials') else A.create_asset('DA_DW715_WetMaterials',D,u.WeatherPresentationAssets,factory)
library.set_editor_property('wet_materials',wetmaps); save(library)
receipt['wet_materials']={key:value.get_path_name() for key,value in wetmaps.items()}
receipt['weather_additions']=library.get_path_name()
receipt['state']='Authored and saved; no gameplay, rendering or additional testing performed'
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('DW715_CHROME_IMPORT_COMPLETE')
