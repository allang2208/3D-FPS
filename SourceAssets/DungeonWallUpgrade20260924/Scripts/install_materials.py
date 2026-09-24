"""Build only the new candidate assets; live dungeon bindings are preserved."""
import hashlib,json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/WallUpgrade20260924'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
REPORT={'stage':'starting','textures':[],'materials':{},'runtime_tested':False,'production_replacement':False}
RECEIPT=ROOT/'Receipts/material-install.json';RECEIPT.parent.mkdir(parents=True,exist_ok=True)
def record():RECEIPT.write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Asset save failed '+obj.get_path_name())
def install():
    if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
    data=json.loads((ROOT/'Authored/materials.json').read_text());textures={}
    for name,entry in data['textures'].items():
        path=BASE+'/Textures/T_'+name;tex=u.load_asset(path)
        if not tex:
            task=u.AssetImportTask();task.filename=entry['file'];task.destination_path=BASE+'/Textures';task.destination_name='T_'+name
            task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(path)
            if not tex:raise RuntimeError('Import failed '+name)
            is_normal=name.endswith('_Normal');is_height=name.endswith('_Height');is_color=name.endswith('_BaseColor')
            tex.set_editor_property('srgb',is_color)
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if is_normal else u.TextureCompressionSettings.TC_HALF_FLOAT if is_height else u.TextureCompressionSettings.TC_DEFAULT if is_color else u.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property('never_stream',False);tex.set_editor_property('lod_bias',0)
            if is_normal:tex.set_editor_property('flip_green_channel',False)
            E.set_metadata_tag(tex,'WallUpgradeSourceSHA256',entry['sha256']);save(tex)
        elif E.get_metadata_tag(tex,'WallUpgradeSourceSHA256')!=entry['sha256']:
            raise RuntimeError('Candidate texture source changed; use a new asset revision '+name)
        textures[name]=tex;REPORT['textures'].append(path);record()
    def make_master(wall=False):
        name='M_WallScanned' if wall else 'M_MineralScanned';path=BASE+'/Materials/'+name
        code=(ROOT/'Scripts/mineral_surface.ush').read_text()
        if wall:
            code=code.replace('// WALL_HORIZONTAL_FALLBACK','''
float2 oldX=ddx(OriginalUV),oldY=ddy(OriginalUV);
float3 posX=ddx(Position),posY=ddy(Position);
[branch] if(an.z>.8){
    float3 oldC=Texture2DSampleGrad(OriginalColor,OriginalColorSampler,OriginalUV,oldX,oldY).rgb;
    float2 oldXY=Texture2DSampleGrad(OriginalNormal,OriginalNormalSampler,OriginalUV,oldX,oldY).rg*2-1;
    float det=oldX.x*oldY.y-oldX.y*oldY.x;
    float3 oldT=normalize((posX*oldY.y-posY*oldX.y)*(det>=0?1:-1)+1e-7);
    float3 oldB=normalize((posY*oldX.x-posX*oldY.x)*(det>=0?1:-1)+1e-7);
    NormalLocal=normalize(oldT*oldXY.x+oldB*oldXY.y+n*sqrt(max(1-dot(oldXY,oldXY),.01)));
    AO=1;Specular=.5;
    return float4(oldC,Texture2DSampleGrad(OriginalRoughness,OriginalRoughnessSampler,OriginalUV,oldX,oldY).r);
}''')
        signature=hashlib.sha256(code.encode()).hexdigest();mat=u.load_asset(path)
        if mat:
            if E.get_metadata_tag(mat,'WallUpgradeGraph')!=signature:raise RuntimeError('Preserve existing candidate graph '+path)
            return mat
        mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('tangent_space_normal',False)
        mat.set_editor_property('used_with_instanced_static_meshes',True);mat.set_editor_property('used_with_nanite',True)
        def node(kind,**props):
            n=L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
            for k,v in props.items():n.set_editor_property(k,v)
            return n
        def wire(a,b,pin='',output=''):
            if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Connection '+pin)
        world=node('WorldPosition');pos=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE);wire(world,pos)
        def local(src):
            dst=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE);wire(src,dst);return dst
        dist=node('Distance');wire(world,dist,'A');wire(node('CameraPositionWS'),dist,'B')
        inputs={'Position':pos,'SurfaceNormal':local(node('VertexNormalWS')),'ViewLocal':local(node('CameraVectorWS')),'DistanceCm':dist}
        for k,v in {'TileCm':200.,'DepthCm':.18,'NormalStrength':.7,'GrainTileCm':32.,'GrainStrength':.75,'Brightness':1.,'RoughnessScale':1.}.items():inputs[k]=node('ScalarParameter',parameter_name=k,default_value=v)
        inputs['Tint']=node('VectorParameter',parameter_name='Tint',default_value=u.LinearColor(1,1,1,1))
        sources={'ColorTex':'Wall_BaseColor','NormalTex':'Wall_Normal','SurfaceTex':'Wall_ORM','HeightTex':'Wall_Height','GrainNormal':'Grain_Normal','GrainSurface':'Grain_Surface'}
        for pin,texname in sources.items():
            sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if texname.endswith('_Normal') else u.MaterialSamplerType.SAMPLERTYPE_COLOR if texname.endswith('_BaseColor') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if texname.endswith('_Height') else u.MaterialSamplerType.SAMPLERTYPE_MASKS
            inputs[pin]=node('TextureObjectParameter',parameter_name=pin,texture=textures[texname],sampler_type=sampler)
        if wall:
            inputs['OriginalUV']=node('TextureCoordinate')
            for pin,suffix,sampler in [('OriginalColor','BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('OriginalNormal','Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('OriginalRoughness','Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
                inputs[pin]=node('TextureObject',texture=u.load_asset('/Game/Dungeons/AtmosphereV2/Textures/T_Concrete_'+suffix),sampler_type=sampler)
        custom=node('Custom',code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,desc='Scanned mineral surface with physical grit and bounded shallow POM')
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        custom.set_editor_property('inputs',pins);outputs=[]
        for key,kind in [('NormalLocal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Specular',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
            o=u.CustomOutput();o.set_editor_property('output_name',key);o.set_editor_property('output_type',kind);outputs.append(o)
        custom.set_editor_property('additional_outputs',outputs)
        for key,src in inputs.items():wire(src,custom,key)
        col=node('ComponentMask',r=True,g=True,b=True,a=False);wire(custom,col)
        rough=node('ComponentMask',r=False,g=False,b=False,a=True);wire(custom,rough)
        normal=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire(custom,normal,output='NormalLocal')
        for src,pin,prop in [(col,'','BASE_COLOR'),(rough,'','ROUGHNESS'),(normal,'','NORMAL'),(custom,'AO','AMBIENT_OCCLUSION'),(custom,'Specular','SPECULAR'),(node('Constant',r=0.),'','METALLIC')]:
            if not L.connect_material_property(src,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError(str(errors))
        L.layout_material_expressions(mat);E.set_metadata_tag(mat,'WallUpgradeGraph',signature);save(mat)
        return mat
    masters=[make_master(True),make_master(False)]
    rows=[('MI_WallConcrete',masters[0],'Wall',200,.18,.7,.65),
          ('MI_ExposedMortar',masters[1],'Mortar',96,.26,.95,1.1),
          ('MI_BondingMortar',masters[1],'Mortar',110,.08,.45,.5),
          ('MI_BrokenConcrete',masters[1],'FabSection',65,0.,.85,.85)]
    for name,parent,family,tile,depth,normal,grain in rows:
        path=BASE+'/Materials/'+name;mi=u.load_asset(path) or A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,parent)
        for pin,channel in [('ColorTex','BaseColor'),('NormalTex','Normal'),('SurfaceTex','ORM')]:L.set_material_instance_texture_parameter_value(mi,pin,textures[family+'_'+channel])
        if family!='FabSection':L.set_material_instance_texture_parameter_value(mi,'HeightTex',textures[family+'_Height'])
        for key,value in {'TileCm':tile,'DepthCm':depth,'NormalStrength':normal,'GrainStrength':grain}.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
        L.update_material_instance(mi);save(mi)
        REPORT['materials'][name]={'path':path,'parent':parent.get_path_name(),'tile_cm':tile,'depth_cm':depth,'grain_strength':grain};record()
    # Required shader build: actual D3D12 commandlet, no scene render or gameplay.
    for mat in masters:
        stats=L.get_statistics(mat)
        REPORT.setdefault('shader_build',{})[mat.get_name()]={k:stats.get_editor_property(k) for k in ['num_pixel_shader_instructions','num_samplers']}
        save(mat);record()
    REPORT['stage']='candidate_materials_saved';record();print('WALL_UPGRADE_MATERIALS_SAVED',json.dumps(REPORT),flush=True)

if __name__=='__main__':install()
