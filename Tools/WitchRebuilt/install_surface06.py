"""A calmer, UV0-aligned woven surface for the upper garment and lining."""
import unreal as u,json
from pathlib import Path
DEST='/Game/Monsters/WitchRebuilt';L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Surface import requires editor mode')
def make(name,lining=False):
    path=DEST+'/Materials/'+name
    mat=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if L.get_metadata_tag(mat,'WitchSurfaceRevision')=='Surface06: UV0-aligned normal detail, reduced facet contrast':return mat
    for p in ('two_sided','used_with_skeletal_mesh','used_with_clothing'):mat.set_editor_property(p,True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    def node(cls):return M.create_material_expression(mat,cls)
    def link(a,b,p,output=''):M.connect_material_expressions(a,output,b,p)
    def con(v):
        n=node(u.MaterialExpressionConstant3Vector if isinstance(v,tuple) else u.MaterialExpressionConstant)
        n.set_editor_property('constant' if isinstance(v,tuple) else 'r',u.LinearColor(*v,1) if isinstance(v,tuple) else v);return n
    def tex(path,normal=False,mask=False,uv=None):
        n=node(u.MaterialExpressionTextureSample);n.texture=u.load_asset(path)
        if not n.texture:raise RuntimeError('Missing surface input '+path)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_MASKS if mask else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if uv:link(uv,n,'Coordinates')
        return n
    slab=node(u.MaterialExpressionSubstrateShadingModels)
    uv=node(u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0;uv.u_tiling=32.;uv.v_tiling=32.
    detail=tex(DEST+'/Textures/Detail/T_Witch_FabricDetail_N',normal=True,uv=uv)
    roughdetail=tex(DEST+'/Textures/Detail/T_Witch_FabricDetail_R',mask=True,uv=uv)
    base=con((0.,0.,1.)) if lining else tex('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_normal',normal=True)
    normal=node(u.MaterialExpressionCustom);normal.set_editor_property('code','float3 n=normalize(lerp(float3(0,0,1),Base,0.24)); return normalize(float3(n.xy+Detail.xy*0.09,n.z*max(Detail.z,0.7)));')
    normal.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name in ('Base','Detail'):
        entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
    normal.set_editor_property('inputs',inputs)
    link(base,normal,'Base','' if lining else 'RGB');link(detail,normal,'Detail','RGB')
    if lining:color=con((.05,.042,.029))
    else:
        color=node(u.MaterialExpressionLinearInterpolate)
        link(tex('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_base_color'),color,'A','RGB')
        link(con((.12,.10,.068)),color,'B');link(con(.28),color,'Alpha')
    scale=node(u.MaterialExpressionMultiply);link(roughdetail,scale,'A','R');link(con(.1),scale,'B')
    rough=node(u.MaterialExpressionAdd);link(scale,rough,'A');link(con(.82),rough,'B')
    for n,prop,pin in ((color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(normal,u.MaterialProperty.MP_NORMAL,'Normal'),(rough,u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(con(.18),u.MaterialProperty.MP_SPECULAR,'Specular'),(con(0.),u.MaterialProperty.MP_METALLIC,'Metallic')):
        M.connect_material_property(n,'',prop);link(n,slab,pin)
    M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);M.recompile_material(mat)
    L.set_metadata_tag(mat,'WitchSurfaceRevision','Surface06: UV0-aligned normal detail, reduced facet contrast')
    if not L.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
    return mat
upper=make('M_WitchRebuilt_UpperFabric06');lining=make('M_WitchRebuilt_Lining06',True)
mesh=u.load_asset(DEST+'/SK_WitchRebuilt');slots=list(mesh.get_editor_property('materials'))
for slot in slots:
    name=str(slot.get_editor_property('imported_material_slot_name'))
    if 'UpperRobe' in name:slot.material_interface=upper
    elif 'Lining' in name:slot.material_interface=lining
mesh.set_editor_property('materials',slots)
if not L.save_loaded_asset(mesh,False):raise RuntimeError('Surface assignment save failed')
print('Surface06 saved: '+upper.get_path_name()+'; '+lining.get_path_name())
