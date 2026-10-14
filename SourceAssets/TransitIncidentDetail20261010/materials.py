"""Shared texture PBR with authored dirt/contact/dampness vertex channels."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;BASE='/Game/Dungeons/TransitIncidentDetail20261010';OWNER='TransitIncidentDetail20261010'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
STYLE={
    'Yellow':(0,4,(.80,.57,.025),.55),'Steel':(1,7,(1,1,1),.50),
    'Rubber':(2,16,(.15,.16,.17),.72),'Cotton':(3,16,(.85,.83,.71),1.),
    'Teal':(0,5,(.036,.15,.119),.65),'Board':(3,3,(.47,.32,.15),.3),
    'Paper':(3,4,(.94,.90,.79),.2),'Forms':(-1,1,(1,1,1),.7),'Caution':(-2,7,(1,1,1),.45)}

def owned(path):
    if not E.does_asset_exist(path):return None
    obj=u.load_asset(path)
    if E.get_metadata_tag(obj,'TransitIncidentDetail.Owner')!=OWNER:raise RuntimeError('Preserve unowned asset '+path)
    return obj

def save(obj):
    E.set_metadata_tag(obj,'TransitIncidentDetail.Owner',OWNER)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    return obj

def install():
    textures={};saved=[]
    for source in sorted((ROOT/'Authored/Textures').glob('*.png')):
        key=source.stem.removeprefix('T_IncidentDetail_');path=BASE+'/Textures/'+source.stem;tex=owned(path)
        if not tex:
            task=u.AssetImportTask();task.filename=str(source);task.destination_path,task.destination_name=path.rsplit('/',1)
            task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.TextureFactory();A.import_asset_tasks([task]);tex=u.load_asset(path)
            if not tex:raise RuntimeError('Missing imported texture '+path)
            is_normal=key.endswith('NormalDX');is_mask=key.endswith('ORM')
            tex.set_editor_property('srgb',not(is_normal or is_mask));tex.set_editor_property('never_stream',False)
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if is_normal else u.TextureCompressionSettings.TC_MASKS if is_mask else u.TextureCompressionSettings.TC_BC7)
            tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            if is_normal:tex.set_editor_property('flip_green_channel',False)
            save(tex)
        textures[key]=tex;saved.append(path)
    for role,(tile,scale,tint,normal_strength) in STYLE.items():
        path=BASE+'/Materials/M_IncidentDetail_'+role;m=owned(path)
        if m:saved.append(path);continue
        m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        m.set_editor_property('used_with_instanced_static_meshes',True)
        if role=='Board':m.set_editor_property('two_sided',True)
        def node(kind,**props):
            n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
            for k,v in props.items():n.set_editor_property(k,v)
            return n
        def link(value,dst,pin):
            n,out=value if isinstance(value,tuple) else (value,'')
            if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot wire '+role+'/'+pin)
        def custom(code,inputs,width):
            n=node('Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
            arr=[]
            for key in inputs:
                pin=u.CustomInput();pin.set_editor_property('input_name',key);arr.append(pin)
            n.set_editor_property('inputs',arr)
            for key,value in inputs.items():link(value,n,key)
            return n
        uv=node('TextureCoordinate');wear=node('VertexColor')
        index=max(tile,0);offx=(index%2)*.5;offy=(index//2)*.5
        tiled=custom(f'return frac(UV*{scale})*.496+float2({offx+.002},{offy+.002});',{'UV':uv},2)
        def sample(key,sampler,coord):
            n=node('TextureSample',texture=textures[key],sampler_type=sampler);link(coord,n,'UVs');return n
        source='Forms' if tile==-1 else 'Surfaces'
        coord=uv if tile==-1 else tiled
        color=sample('Caution_BC' if tile==-2 else source+'_BC',u.MaterialSamplerType.SAMPLERTYPE_COLOR,uv if tile==-2 else coord)
        normals=sample(source+'_NormalDX',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,coord)
        masks=sample(source+'_ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS,coord)
        tc=','.join(str(x) for x in tint)
        plastic=role in ('Yellow','Teal');paper=role in ('Paper','Forms','Board','Caution')
        colorcode=f'float3 b=C*float3({tc}); float dirt=W.r; float edge=W.g; float wet=W.b; '
        colorcode+=('b=lerp(b,b*float3(.61,.58,.50),dirt*.30); ' if paper else 'b=lerp(b,float3(.034,.026,.016),dirt*.52); ')
        if plastic:colorcode+='b=lerp(b,b*1.18+float3(.035,.032,.018),edge*.22); '
        elif role=='Steel':colorcode+='b=lerp(b,b*1.20,edge*.30); '
        if role=='Cotton':colorcode+='b*=1-wet*.29; '
        colorcode+='return saturate(b);'
        base=custom(colorcode,{'C':(color,'RGB'),'W':wear},3)
        rough=custom('return clamp(R + W.r*.11 - W.g*.055 - W.b*.16,.20,.98);',{'R':(masks,'G'),'W':wear},1)
        normal=custom(f'return normalize(float3(N.xy*{normal_strength},N.z));',{'N':(normals,'RGB')},3)
        metal=custom('return M*(1-W.r*.32);',{'M':(masks,'B'),'W':wear},1)
        slab=node('SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for value,pin,prop in ((base,'BaseColor','BASE_COLOR'),(rough,'Roughness','ROUGHNESS'),(normal,'Normal','NORMAL'),(metal,'Metallic','METALLIC'),(node('Constant',r=.28),'Specular','SPECULAR')):
            link(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
        L.connect_material_property(masks,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Detail material build failed '+role+' '+str(errors))
        save(m);saved.append(path)
    return saved
