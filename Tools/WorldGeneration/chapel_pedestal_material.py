"""Dedicated opaque UV stone for the chapel pedestal; no ground projection."""
import unreal as u

DEST='/Game/WorldGeneration/HillsNightRaid'
NAME='M_ChapelShrinePedestalStone'
OWNER='ChapelShrineSupportFixR2_20261116'

def build():
    e,l=u.EditorAssetLibrary,u.MaterialEditingLibrary
    path=DEST+'/'+NAME
    mat=u.load_asset(path) if e.does_asset_exist(path) else None
    if mat and e.get_metadata_tag(mat,'ChapelShrineMaterialOwner')!=OWNER:
        raise RuntimeError('Preserve unowned material '+path)
    if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(NAME,DEST,u.Material,u.MaterialFactoryNew())
    mat.modify()
    # UE 5.8's delete-all iterates the collection it mutates; snapshot it first.
    for expression in list(l.get_material_expressions(mat)):
        l.delete_material_expression(mat,expression)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_SURFACE)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('material_decal_response',u.MaterialDecalResponse.MDR_NONE)
    def node(cls):return l.create_material_expression(mat,getattr(u,'MaterialExpression'+cls))
    def wire(a,b,pin,output=''):
        if not l.connect_material_expressions(a,output,b,pin):raise RuntimeError(pin)
    def output(a,prop,pin=''):
        if not l.connect_material_property(a,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
    uv=node('TextureCoordinate')
    uv.set_editor_property('coordinate_index',0)
    def sample(suffix):
        texture=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_01A_'+suffix)
        if not texture:raise RuntimeError('Missing fieldstone '+suffix)
        n=node('TextureSample');n.set_editor_property('texture',texture)
        kind='NORMAL' if texture.compression_settings==u.TextureCompressionSettings.TC_NORMALMAP else (
             'MASKS' if texture.compression_settings==u.TextureCompressionSettings.TC_MASKS else
             'COLOR' if texture.srgb else 'LINEAR_COLOR')
        if texture.compression_settings==u.TextureCompressionSettings.TC_GRAYSCALE:
            kind='GRAYSCALE' if texture.srgb else 'LINEAR_GRAYSCALE'
        elif texture.compression_settings==u.TextureCompressionSettings.TC_ALPHA:kind='ALPHA'
        if texture.virtual_texture_streaming:kind='VIRTUAL_'+kind
        n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
        n.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        wire(uv,n,'UVs')
        return n
    base,normal,packed=sample('BaseColor'),sample('Normal'),sample('RHAOM')
    height=sample('Height')
    bump=node('BumpOffset');bump.set_editor_property('height_ratio',.006);bump.set_editor_property('reference_plane',.55)
    wire(uv,bump,'Coordinate');wire(height,bump,'Height','R')
    for tex in (base,normal,packed):wire(bump,tex,'UVs')
    tint=node('Constant3Vector');tint.set_editor_property('constant',u.LinearColor(.78,.79,.76,1.))
    color=node('Multiply');wire(base,color,'A','RGB');wire(tint,color,'B')
    variation=node('VertexColor');finished=node('Multiply');wire(color,finished,'A');wire(variation,finished,'B')
    rough=node('Clamp');rough.set_editor_property('min_default',.66);rough.set_editor_property('max_default',.95)
    wire(packed,rough,'','R')
    spec=node('Constant');spec.set_editor_property('r',.23)
    output(finished,'BASE_COLOR');output(normal,'NORMAL','RGB');output(rough,'ROUGHNESS')
    output(packed,'AMBIENT_OCCLUSION','B');output(spec,'SPECULAR')
    e.set_metadata_tag(mat,'ChapelShrineMaterialOwner',OWNER)
    errors=l.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    l.get_statistics(mat)
    if not e.save_loaded_asset(mat,False):raise RuntimeError('Stone material save failed')
    return mat
