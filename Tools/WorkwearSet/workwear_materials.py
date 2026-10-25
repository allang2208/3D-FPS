import sys
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside workwear scope')
    a.modify()
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def create():
    file=R/'materials.json';revision=sha(R/'textures.json')+sha(__file__)
    if file.exists():
        old=read(file)
        if old.get('revision')==revision:return [u.load_asset(p) for p in old['materials']]
    textures={};mats=[]
    for row in read(R/'textures.json')['maps']:
        if row['name']=='HatCanvas':continue
        for channel in ('BaseColor','Normal','ORM'):
            name='T_Workwear_'+row['name']+'_'+channel;task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/Textures/'+name)
            for key,value in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,max_texture_size=row['resolution'],compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP).items():tex.set_editor_property(key,value)
            save(tex);textures[row['name']+'_'+channel]=tex
    for family in ('Canvas','Leather','Lining','Brass','Thread'):
        name='M_Workwear_'+family;mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
        cloth=family in ('Canvas','Lining','Thread');mat.set_editor_property('use_material_attributes',True);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if cloth else u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for usage in (u.MaterialUsage.MATUSAGE_SKELETAL_MESH,u.MaterialUsage.MATUSAGE_STATIC_MESH):L.set_material_usage(mat,usage)
        def node(cls):return L.create_material_expression(mat,cls)
        def wire(a,b,pin,out=''):
            if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Workwear material pin '+pin)
        def scalar(value):
            n=node(u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
        attrs=node(u.MaterialExpressionMakeMaterialAttributes);samples={}
        for channel in ('BaseColor','Normal','ORM'):
            n=node(u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',textures[family+'_'+channel]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);samples[channel]=n
        wire(samples['BaseColor'],attrs,'BaseColor','RGB');wire(samples['Normal'],attrs,'Normal','RGB')
        for channel,pin in (('R','AmbientOcclusion'),('G','Roughness'),('B','Metallic')):wire(samples['ORM'],attrs,pin,channel)
        if cloth:
            fuzz=node(u.MaterialExpressionMultiply);wire(samples['BaseColor'],fuzz,'A','RGB');wire(scalar(.18),fuzz,'B');wire(fuzz,attrs,'SubsurfaceColor');wire(scalar(.10),attrs,'ClearCoat')
        wire(scalar(.24 if cloth else .32),attrs,'Specular')
        if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Workwear material output')
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Workwear shader compile '+str(errors))
        save(mat);mats.append(mat)
    write(file,dict(completed=True,revision=revision,materials=[m.get_path_name() for m in mats],textures={k:v.get_path_name() for k,v in textures.items()},runtime_tested=False));return mats
