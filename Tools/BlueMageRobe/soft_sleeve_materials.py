"""First-person twill, embroidered cuff and lining with one paired inertia field."""
import hashlib, json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020'
DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/FPSoftSleeves20261020'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Sleeve surface save failed '+asset.get_path_name())
def node(mat,kind,**props):
    value=L.create_material_expression(mat,kind)
    for key,data in props.items():value.set_editor_property(key,data)
    return value
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Sleeve material pin '+pin)
def create():
    files=sorted((R/'Textures').glob('*.png'))
    revision=hashlib.sha256(Path(__file__).read_bytes()+b''.join(f.read_bytes() for f in files)).hexdigest()
    receipt=R/'materials-saved.json'
    if receipt.exists():
        saved=json.loads(receipt.read_text())
        if saved['revision']==revision:
            return [u.load_asset(p) for p in saved['materials']]
    textures={}
    for family in ('RobeSoftTwill','RobeSoftCuff'):
        for channel in ('BaseColor','Normal','ORM'):
            name='T_'+family+'_'+channel
            task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'))
            task.destination_path=DEST+'/Textures';task.destination_name=name
            task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/Textures/'+name)
            if not tex:raise RuntimeError('Missing imported sleeve texture '+name)
            tex.set_editor_property('srgb',channel=='BaseColor')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property('never_stream',False)
            tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
            tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP)
            tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP if family=='RobeSoftCuff' else u.TextureAddress.TA_WRAP)
            if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
            save(tex);textures[family,channel]=tex
    result=[]
    for label,family in [('Fabric','RobeSoftTwill'),('Cuff','RobeSoftCuff'),('Lining','RobeSoftTwill')]:
        name='M_RobeSoft_'+label
        mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        L.delete_all_material_expressions(mat)
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
        mat.set_editor_property('use_material_attributes',True)
        mat.set_editor_property('max_world_position_offset_displacement',.3)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        attrs=node(mat,u.MaterialExpressionMakeMaterialAttributes)
        uv=node(mat,u.MaterialExpressionTextureCoordinate)
        samples={}
        for channel in ('BaseColor','Normal','ORM'):
            sample=node(mat,u.MaterialExpressionTextureSample,texture=textures[family,channel],
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            wire(uv,sample,'UVs');samples[channel]=sample
        color=samples['BaseColor']
        if label=='Lining':
            tint=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.38,.42,.52,1))
            color=node(mat,u.MaterialExpressionMultiply)
            wire(samples['BaseColor'],color,'A','RGB');wire(tint,color,'B')
        wire(color,attrs,'BaseColor','RGB' if color==samples['BaseColor'] else '')
        wire(samples['Normal'],attrs,'Normal','RGB')
        wire(samples['ORM'],attrs,'Metallic','B')
        wire(samples['ORM'],attrs,'AmbientOcclusion','R')
        if label=='Lining':wire(node(mat,u.MaterialExpressionConstant,r=.92),attrs,'Roughness')
        else:wire(samples['ORM'],attrs,'Roughness','G')
        wire(node(mat,u.MaterialExpressionConstant,r=.22),attrs,'Specular')
        metal=node(mat,u.MaterialExpressionMultiply,const_b=1/.68);wire(samples['ORM'],metal,'A','B')
        clamp=node(mat,u.MaterialExpressionClamp)
        wire(metal,clamp,str(L.get_material_expression_input_names(clamp)[0]))
        fabric=node(mat,u.MaterialExpressionOneMinus)
        wire(clamp,fabric,str(L.get_material_expression_input_names(fabric)[0]))
        fuzz=node(mat,u.MaterialExpressionMultiply,const_b=.28 if label=='Fabric' else .20)
        wire(fabric,fuzz,'A');wire(fuzz,attrs,'ClearCoat')
        fuzz_color=node(mat,u.MaterialExpressionMultiply,const_b=.65)
        wire(color,fuzz_color,'A','RGB' if color==samples['BaseColor'] else '')
        wire(fuzz_color,attrs,'SubsurfaceColor')
        mask=node(mat,u.MaterialExpressionVertexColor)
        def field(previous):
            terms=[]
            for side,pin in [('Left','R'),('Right','G')]:
                vector=node(mat,u.MaterialExpressionVectorParameter,
                    parameter_name='CuffLag'+('Previous' if previous else '')+side,
                    default_value=u.LinearColor(0,0,0,0))
                term=node(mat,u.MaterialExpressionMultiply)
                wire(vector,term,'A','RGB');wire(mask,term,'B',pin);terms.append(term)
            total=node(mat,u.MaterialExpressionAdd);wire(terms[0],total,'A');wire(terms[1],total,'B')
            return total
        switch=node(mat,u.MaterialExpressionPreviousFrameSwitch)
        wire(field(False),switch,'Current Frame');wire(field(True),switch,'Previous Frame')
        wire(switch,attrs,'WorldPositionOffset')
        if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):
            raise RuntimeError('Cannot connect sleeve surface')
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Sleeve material compile failed '+str(errors))
        save(mat);result.append(mat)
    receipt.write_text(json.dumps(dict(completed=True,revision=revision,
        materials=[m.get_path_name() for m in result]),indent=2),encoding='utf-8')
    return result
