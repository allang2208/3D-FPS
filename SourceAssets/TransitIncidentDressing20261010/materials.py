"""Small original print/plastic materials; all existing facility materials stay untouched."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;BASE='/Game/Dungeons/TransitIncidentDressing20261010'
OWNER='TransitIncident20261010';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()

def owned(path):
    if not E.does_asset_exist(path):return None
    obj=u.load_asset(path)
    if E.get_metadata_tag(obj,'TransitIncident.Owner')!=OWNER:raise RuntimeError('Preserve unowned incident asset '+path)
    return obj

def save(obj):
    E.set_metadata_tag(obj,'TransitIncident.Owner',OWNER)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    return obj

def install():
    saved=[];textures={}
    for kind in ('Forms','Caution'):
        path=BASE+'/Textures/T_Incident_'+kind;tex=owned(path)
        if not tex:
            t=u.AssetImportTask();t.filename=str(ROOT/'Authored/Textures'/('T_Incident_'+kind+'.png'))
            t.destination_path,t.destination_name=path.rsplit('/',1);t.automated=True;t.save=False;t.replace_existing=False;t.factory=u.TextureFactory()
            A.import_asset_tasks([t]);tex=u.load_asset(path)
            if not tex:raise RuntimeError('Texture import failed '+path)
            tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',False)
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
            tex.set_editor_property('max_texture_size',2048 if kind=='Forms' else 1024)
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            save(tex)
        textures[kind]=tex;saved.append(path)
    for key,color,rough,texture in (
        ('YellowPlastic',(.75,.50,.018),.51,None),('Fiberboard',(.29,.21,.115),.91,None),('Cotton',(.35,.33,.25),.96,None),
        ('Forms',None,.9,'Forms'),('Caution',None,.55,'Caution')):
        path=BASE+'/Materials/M_Incident_'+key;m=owned(path)
        if m:saved.append(path);continue
        m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        m.set_editor_property('used_with_instanced_static_meshes',True)
        if key=='Fiberboard':m.set_editor_property('two_sided',True)
        def node(kind,**props):
            n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
            for k,v in props.items():n.set_editor_property(k,v)
            return n
        slab=node('SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        def connect(n,out,prop,pin):
            L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+prop));L.connect_material_expressions(n,out,slab,pin)
        uv=node('TextureCoordinate')
        def custom(code,width):
            inp=u.CustomInput();inp.set_editor_property('input_name','UV')
            n=node('Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)),inputs=[inp])
            L.connect_material_expressions(uv,'',n,'UV');return n
        if texture:base=node('TextureSample',texture=textures[texture],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);out='RGB'
        else:
            c=node('Constant3Vector',constant=u.LinearColor(*color,1))
            variation=custom('float s=sin(UV.x*57+sin(UV.y*91))*sin(UV.y*137);return .94+.06*s;',1)
            base=node('Multiply');L.connect_material_expressions(c,'',base,'A');L.connect_material_expressions(variation,'',base,'B');out=''
        connect(base,out,'BASE_COLOR','BaseColor')
        roughness=custom(f'return clamp({rough} + .04*sin(UV.x*107)*sin(UV.y*241), .2, .98);',1)
        connect(roughness,'','ROUGHNESS','Roughness')
        connect(node('Constant',r=0.),'','METALLIC','Metallic');connect(node('Constant',r=.25),'','SPECULAR','Specular')
        if key=='YellowPlastic':
            grain=custom('float f=1-saturate(length(fwidth(UV))*600);float2 g=sin(UV*1700+sin(UV.yx*317));return normalize(float3(g*.018*f,1));',3)
            connect(grain,'','NORMAL','Normal')
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Incident material build failed '+key+' '+str(errors))
        save(m);saved.append(path)
    return saved
