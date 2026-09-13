"""Connect a curated Project Nature meadow to the existing temperate hills.

Run after building the grass-enabled FPSGAMEEditor module. Authors only owned
grass copies, the grass PCG descriptor and the existing biome's grass fields.
Does not open a map, run gameplay, render previews or change the source library.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
BASE='/Game/WorldGeneration/TemperateHills'
DEST=BASE+'/Grass'
SOURCE='/Game/PN_GrassLibrary'
OUT=ROOT/'Saved/TemperateGrass'
OUT.mkdir(parents=True,exist_ok=True)
EAL=u.EditorAssetLibrary
LIB=u.MaterialEditingLibrary
REPORT={'source':'https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303',
        'meshes':[],'saved':[],'scope':'Grass authoring only; gameplay and visuals not tested'}

# Compact clusters for cover; a separate set adds taller silhouettes and herbs.
# All retain the publisher's four LODs, vertex colours and Pivot Painter UVs.
COVER=['lowGrass_01_02_SM','lowGrass_02_02_SM','lowGrass_04_03_SM',
       'lowGrass_08_02_SM','lowGrass_09_02_SM','grass_01_08_mesh']
ACCENTS=['grass_03_08_mesh','grass_05_03_mesh','grass_07_01_mesh',
         'grass_09_02_mesh','grass_11_02_mesh','grass_12_05_mesh']

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing grass authoring source: '+path)
    return obj

def save(obj):
    if not EAL.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj

def copy(source,target):
    obj=load(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source,target)
    if obj is None:raise RuntimeError('Could not copy '+source)
    return obj

# Preserve the two existing assets before changing their grass-specific fields.
backup=OUT/('BeforeGrass-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.mkdir(parents=True)
for name in ('DA_TemperateHillsStreaming','PCG_HillsGrass'):
    shutil.copy2(ROOT/'Content/WorldGeneration/TemperateHills'/(name+'.uasset'),backup/(name+'.uasset'))
EAL.make_directory(DEST)
master=copy(SOURCE+'/Materials/grassMaterials/MA_Grass',DEST+'/M_TemperateMeadow')
master.set_editor_property('used_with_instanced_static_meshes',True)
opacity=LIB.get_material_property_input_node(master,u.MaterialProperty.MP_OPACITY_MASK)
if opacity is None:raise RuntimeError('The imported grass master has no opacity-mask input')
if opacity.get_editor_property('desc')!='TemperateMeadowDistanceFade':
    output=LIB.get_material_property_input_node_output_name(master,u.MaterialProperty.MP_OPACITY_MASK)
    fade=LIB.create_material_expression(master,u.MaterialExpressionPerInstanceFadeAmount)
    multiply=LIB.create_material_expression(master,u.MaterialExpressionMultiply)
    multiply.set_editor_property('desc','TemperateMeadowDistanceFade')
    if not LIB.connect_material_expressions(opacity,output,multiply,'A'):raise RuntimeError('Opacity connection failed')
    if not LIB.connect_material_expressions(fade,'',multiply,'B'):raise RuntimeError('Fade connection failed')
    if not LIB.connect_material_property(multiply,'',u.MaterialProperty.MP_OPACITY_MASK):raise RuntimeError('Mask connection failed')

# Recolour the original texture luminance instead of merely multiplying a green
# albedo by yellow. Apply the same remap to subsurface transmission, which would
# otherwise remain vivid green when the player looks towards the sun.
DRY_COLOR_CODE='''
float patch=.5+.25*sin(P.x*.0011+P.y*.0007)+.25*sin(P.y*.0015-P.x*.0004);
float dry=saturate(Dryness+(R-.5)*Variation+(patch-.5)*.22);
float mix=saturate(.65+(R-.5)*.45+(patch-.5)*.35);
float3 tint=lerp(OliveTint,DryTint,mix);
float luminance=dot(C,float3(.299,.587,.114));
return lerp(C,luminance*tint,dry);
'''

def scalar(name,value):
    expr=LIB.create_material_expression(master,u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name',name)
    expr.set_editor_property('default_value',value)
    return expr

def tint(name,rgb):
    expr=LIB.create_material_expression(master,u.MaterialExpressionVectorParameter)
    expr.set_editor_property('parameter_name',name)
    expr.set_editor_property('default_value',u.LinearColor(*rgb,1))
    return expr

color_inputs=None
for property_name in ('BASE_COLOR','SUBSURFACE_COLOR'):
    prop=getattr(u.MaterialProperty,'MP_'+property_name)
    source_color=LIB.get_material_property_input_node(master,prop)
    if source_color is None:raise RuntimeError('Missing grass colour input: '+property_name)
    marker='TemperateDryMeadow_'+property_name
    if source_color.get_editor_property('desc')==marker:
        source_color.set_editor_property('code',DRY_COLOR_CODE)
        continue
    if color_inputs is None:
        color_inputs={'P':LIB.create_material_expression(master,u.MaterialExpressionWorldPosition),
                      'R':LIB.create_material_expression(master,u.MaterialExpressionPerInstanceRandom),
                      'Dryness':scalar('MeadowDryness',.92),
                      'Variation':scalar('MeadowColorVariation',.16),
                      'DryTint':tint('MeadowDryTint',(1.60,1.21,.57)),
                      'OliveTint':tint('MeadowOliveTint',(1.12,1.05,.62))}
    output=LIB.get_material_property_input_node_output_name(master,prop)
    expr=LIB.create_material_expression(master,u.MaterialExpressionCustom)
    expr.set_editor_property('desc',marker)
    expr.set_editor_property('code',DRY_COLOR_CODE)
    expr.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs={'C':source_color,**color_inputs}
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    expr.set_editor_property('inputs',pins)
    for name,value in inputs.items():
        if not LIB.connect_material_expressions(value,output if name=='C' else '',expr,name):
            raise RuntimeError('Could not connect dry grass colour '+name)
    if not LIB.connect_material_property(expr,'',prop):raise RuntimeError('Could not connect '+property_name)
LIB.recompile_material(master)
save(master)
materials={}

def mesh_copy(name,group):
    source=load(SOURCE+'/Meshes/grassMesh/'+name)
    mesh=copy(source.get_path_name(),DEST+'/SM_Meadow_'+name)
    for index,slot in enumerate(source.get_editor_property('static_materials')):
        original=slot.material_interface
        key=original.get_path_name()
        if key not in materials:
            mat=copy(key,DEST+'/MI_Meadow_'+original.get_name())
            LIB.set_material_instance_parent(mat,master)
            # Predominantly straw/khaki, with grey olive variation between tufts.
            LIB.set_material_instance_scalar_parameter_value(mat,'Brightness',.85)
            LIB.set_material_instance_scalar_parameter_value(mat,'Saturation',.65)
            LIB.set_material_instance_scalar_parameter_value(mat,'Subsurface Saturation',.7)
            LIB.set_material_instance_scalar_parameter_value(mat,'Subsurface Strengh',.55)
            LIB.set_material_instance_scalar_parameter_value(mat,'MeadowDryness',.92)
            LIB.set_material_instance_scalar_parameter_value(mat,'MeadowColorVariation',.16)
            # Keep the pack's blade wind, without evaluating the unused demo
            # character-bending system for every vertex in the dense meadow.
            for level in (1,2,3):
                LIB.set_material_instance_static_switch_parameter_value(mat,'Level %d Bending'%level,False)
                LIB.set_material_instance_static_switch_parameter_value(mat,'Level %d Wind'%level,level==1)
            LIB.update_material_instance(mat)
            materials[key]=save(mat)
        mesh.set_material(index,materials[key])
    save(mesh)
    box=mesh.get_bounding_box()
    size=box.max-box.min
    REPORT['meshes'].append({'source':source.get_path_name(),'copy':mesh.get_path_name(),
                            'group':group,'size_cm':[size.x,size.y,size.z]})
    return mesh

cover=[mesh_copy(name,'cover') for name in COVER]
accents=[mesh_copy(name,'accent') for name in ACCENTS]
graph=load(BASE+'/PCG_HillsGrass')
graph.set_editor_property('hi_gen_grid_size',u.PCGHiGenGrid.GRID16)
for node in graph.get_editor_property('nodes'):
    settings=node.get_settings()
    if not isinstance(settings,u.PCGStaticMeshSpawnerSettings):continue
    selector=settings.get_editor_property('mesh_selector_parameters')
    descriptor=selector.get_editor_property('template_descriptor')
    descriptor.set_editor_property('cast_shadow',False)
    descriptor.set_editor_property('instance_start_cull_distance',3500)
    descriptor.set_editor_property('instance_end_cull_distance',5000)
    body=descriptor.get_editor_property('body_instance')
    body.set_editor_property('collision_profile_name','NoCollision')
    descriptor.set_editor_property('body_instance',body)
    selector.set_editor_property('template_descriptor',descriptor)
save(graph)
assets=load(BASE+'/DA_TemperateHillsStreaming')
assets.set_editor_property('grass',cover)
assets.set_editor_property('grass_accents',accents)
for name,value in {'grass_spacing_cm':55.0,'grass_coverage':.94,
                   'grass_accent_spacing_cm':180.0,'grass_accent_coverage':.5}.items():
    assets.set_editor_property(name,value)
save(assets)
REPORT['configuration']=assets.get_path_name()
REPORT['palette']={'dryness':.92,'variation':.16,'dry_tint':[1.60,1.21,.57],
                   'olive_tint':[1.12,1.05,.62],'brightness':.85,'subsurface_strength':.55}
REPORT['wind_defaults']={}
for name in ('PN_WindParameters','MaterialFunctions/PN_BendingParameters'):
    collection=load(SOURCE+'/Materials/'+name)
    REPORT['wind_defaults'][name]={str(p.get_editor_property('parameter_name')):p.get_editor_property('default_value')
                                  for p in collection.get_editor_property('scalar_parameters')}
REPORT['static_switches']={str(n):LIB.get_material_default_static_switch_parameter_value(master,n)
                           for n in LIB.get_static_switch_parameter_names(master)}
(OUT/'authoring.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('TEMPERATE_GRASS_AUTHORING_COMPLETE')
