"""Save reference-ring shirt materials and native mesh copies; scoped publish."""
import json
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailRelief20260929'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailRelief20260929'
ITEM='ue_chainmail_shirt';ICON='Icons/ChainmailRelief20260929/ue_chainmail_shirt.png'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from import_tailored_fingerless_candidate import load,save
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def ensure_authoring():
    commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
    editor=None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('CHAINMAIL_PIE_ACTIVE: end the current play session before saving equipment assets')
    read(R/'production.json')


def material():
    folder=DEST+'/Materials';E.make_directory(folder);textures={}
    for channel in ['BaseColor','ORM','Normal','Relief']:
        name='T_ChainmailRelief_'+channel;t=u.AssetImportTask()
        t.filename=str(R/'Textures'/(name+'.png'));t.destination_path=folder;t.destination_name=name
        t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
        tex=load(folder+'/'+name);tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('flip_green_channel',channel=='Normal')
        tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('never_stream',False)
        tex.set_editor_property('compression_no_alpha',True)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        save(tex);textures[channel]=tex
    name='M_Chainmail_RingRelief'
    mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(mat):
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        mat.set_editor_property('use_material_attributes',True);mat.set_editor_property('tangent_space_normal',True)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        def node(cls):return L.create_material_expression(mat,cls)
        def wire(a,b,pin,output=''):
            if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection failed '+pin)
        def scalar(name,value):
            n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
        uv=node(u.MaterialExpressionTextureCoordinate)
        pos=node(u.MaterialExpressionWorldPosition)
        pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        repeat=node(u.MaterialExpressionVectorParameter);repeat.set_editor_property('parameter_name','TileRepeat25cm')
        repeat.set_editor_property('default_value',u.LinearColor(.25/.0392,.25/.024,0,0))
        mask=node(u.MaterialExpressionComponentMask)
        for c in 'rgba':mask.set_editor_property(c,c in 'rg')
        wire(repeat,mask,'')
        inputs={'UV':uv,'TileRepeat':mask,'Position':pos,'Camera':node(u.MaterialExpressionCameraPositionWS),
                'VertexNormal':node(u.MaterialExpressionVertexNormalWS),'DepthCm':scalar('RingReliefDepthCm',.40),
                'TextureSize':scalar('TileResolution',2048)}
        for channel,pin in [('BaseColor','ColorTex'),('ORM','ORMTex'),('Normal','NormalTex'),('Relief','ReliefTex')]:
            n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',channel)
            n.set_editor_property('texture',textures[channel]);n.set_editor_property('sampler_type',
                u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            inputs[pin]=n
        custom=node(u.MaterialExpressionCustom);custom.set_editor_property('code',(P/'Tools/ModularOutfit/chainmail_relief.ush').read_text())
        custom.set_editor_property('description','Forged ring high-mesh bake; bounded skinned shared-UV relief')
        custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
        pins=[]
        for key in inputs:p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        custom.set_editor_property('inputs',pins)
        for key,value in inputs.items():wire(value,custom,key)
        outputs=[]
        for key,width in [('NormalTangent',3),('AO',1),('Metallic',1)]:
            out=u.CustomOutput();out.set_editor_property('output_name',key)
            out.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));outputs.append(out)
        custom.set_editor_property('additional_outputs',outputs)
        attrs=node(u.MaterialExpressionMakeMaterialAttributes)
        if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Material output missing')
        for channels,pin in [('rgb','BaseColor'),('a','Roughness')]:
            mask=node(u.MaterialExpressionComponentMask)
            for c in 'rgba':mask.set_editor_property(c,c in channels)
            wire(custom,mask,'');wire(mask,attrs,pin)
        for out,pin in [('NormalTangent','Normal'),('AO','AmbientOcclusion'),('Metallic','Metallic')]:wire(custom,attrs,pin,out)
        wire(scalar('SteelSpecular',.5),attrs,'Specular');L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Chainmail material compilation failed '+str(errors))
    save(mat)
    name='MI_Chainmail_Rings_Standard'
    simple=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(simple,mat)
    L.set_material_instance_scalar_parameter_value(simple,'RingReliefDepthCm',0.)
    save(simple)
    write(R/'materials-saved.json',dict(relief=mat.get_path_name(),standard=simple.get_path_name(),
           textures={k:v.get_path_name() for k,v in textures.items()}))
    print('CHAINMAIL_RELIEF_MATERIALS_SAVED',flush=True)


def main(stage='all'):
    current=read(P/'Content/ColdSteelData/modular_outfits.json')['items'][ITEM]
    if current.get('appearance_family') in ('ChainmailInterlace20260929','ChainmailCloth20260929','ChainmailSharedSway20260929'):
        raise RuntimeError('Use the current interlace/cloth importer; this relief entry is historical.')
    if stage in ('material','all'):
        ensure_authoring()
        material()
    if stage in ('publish','all'):
        from publish_chainmail_relief import main as publish_saved_materials
        publish_saved_materials()


if __name__=='__main__':main()
