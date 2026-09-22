import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Refinement20260922')
DEST='/Game/Monsters/WitchRebuilt';L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=ROOT.parents[2]/'FPSGAME.uproject':
    raise RuntimeError('Connected editor is not FPSGAME')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop the current game session before material import')
for f in (ROOT/'Textures').glob('*.png'):
    existing=DEST+'/Textures/Detail/'+f.stem
    if L.does_asset_exist(existing):continue
    t=u.AssetImportTask();t.filename=str(f);t.destination_path=DEST+'/Textures/Detail';t.automated=True;t.replace_existing=True;t.save=False
    AT.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+f.stem)
    tex.set_editor_property('srgb',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if f.stem.endswith('_N') else u.TextureCompressionSettings.TC_MASKS)
    if not L.save_loaded_asset(tex,False):raise RuntimeError('Detail texture save failed')
def material(name,kind,lining=False):
    path=DEST+'/Materials/'+name
    m=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    # Existing loaded expressions may be rooted by a material editor in UE 5.8.
    # Versioned materials avoid DeleteAllMaterialExpressions and preserve originals.
    if L.get_metadata_tag(m,'WitchDetailRevision')=='Refinement03':
        changed=False
        for expression in M.get_material_expressions(m):
            if isinstance(expression,u.MaterialExpressionTextureSample) and expression.texture:
                if '/WitchRebuilt/Textures/Detail/' in expression.texture.get_path_name() and expression.texture.get_name().endswith('_R'):
                    if expression.get_editor_property('sampler_type')!=u.MaterialSamplerType.SAMPLERTYPE_MASKS:
                        expression.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS);changed=True
        if changed:
            M.recompile_material(m)
            if not L.save_loaded_asset(m,False):raise RuntimeError('Detail sampler correction save failed')
        return m.get_path_name()
    for k,v in [('two_sided',True),('used_with_skeletal_mesh',True),('used_with_clothing',True)]:m.set_editor_property(k,v)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    slab=M.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
    def node(cls):return M.create_material_expression(m,cls)
    def con(value):
        n=node(u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
        n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value);return n
    def link(a,b,p,output=''):M.connect_material_expressions(a,output,b,p)
    def output(n,prop,pin):M.connect_material_property(n,'',prop);link(n,slab,pin)
    def sample(path,normal=False,linear=False,uv=None):
        n=node(u.MaterialExpressionTextureSample);n.texture=u.load_asset(path)
        if not n.texture:raise RuntimeError('Missing texture '+path)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_MASKS if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if uv:link(uv,n,'Coordinates')
        return n
    uv=node(u.MaterialExpressionTextureCoordinate);uv.coordinate_index=1
    detail=sample(DEST+'/Textures/Detail/T_Witch_'+kind+'Detail_N',True,uv=uv)
    roughdetail=sample(DEST+'/Textures/Detail/T_Witch_'+kind+'Detail_R',linear=True,uv=uv)
    color=con((.045,.037,.026)) if lining else sample('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_base_color')
    base=con((0.,0.,1.)) if lining else sample('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_normal',True)
    normal=node(u.MaterialExpressionCustom)
    normal.set_editor_property('code','float3 n=normalize(lerp(float3(0,0,1), Base, BaseStrength)); return normalize(float3(n.xy + Detail.xy*DetailStrength, n.z*max(Detail.z,0.5)));')
    normal.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name in ('Base','Detail','BaseStrength','DetailStrength'):
        entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
    normal.set_editor_property('inputs',inputs)
    link(base,normal,'Base','RGB' if not lining else '');link(detail,normal,'Detail','RGB')
    link(con(.65 if kind=='Fabric' else .85),normal,'BaseStrength');link(con(.32 if kind=='Fabric' else .20),normal,'DetailStrength')
    rough=node(u.MaterialExpressionMultiply);link(con(.25),rough,'B');link(roughdetail,rough,'A','R')
    bias=node(u.MaterialExpressionAdd);link(con(.58 if kind=='Fabric' else .43),bias,'B');link(rough,bias,'A')
    output(color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');output(normal,u.MaterialProperty.MP_NORMAL,'Normal')
    output(bias,u.MaterialProperty.MP_ROUGHNESS,'Roughness');output(con(.27 if kind=='Fabric' else .32),u.MaterialProperty.MP_SPECULAR,'Specular')
    output(con(0.),u.MaterialProperty.MP_METALLIC,'Metallic');M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    M.recompile_material(m)
    L.set_metadata_tag(m,'WitchDetailRevision','Refinement03')
    if not L.save_loaded_asset(m,False):raise RuntimeError('Detail material save failed')
    return m.get_path_name()
result=[material('M_WitchRebuilt_FabricDetail03','Fabric'),material('M_WitchRebuilt_LiningDetail03','Fabric',True),
        material('M_WitchRebuilt_HatDetail03','Fabric'),material('M_WitchRebuilt_HeadDetail03','Skin')]
(ROOT/'material_result.json').write_text(json.dumps({'materials':result,'detail_resolution':1024,'source':'Original procedural weave and pore microdetail','runtime_tested':False},indent=2),encoding='utf-8')
print('Saved detailed fabric, lining, hat and face materials')
