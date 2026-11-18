"""Reuse chapel PBR wood with quiet weathering; no projected ground material."""
import unreal as u
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Materials'
name='M_ShutterWeatheredOak'
mat=u.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
mat.modify();L.delete_all_material_expressions(mat)
def node(kind):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError(pin)
def prop(a,out,p):
    if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError(p)
def scalar(value):n=node('Constant');n.r=value;return n
def vector(value):n=node('Constant3Vector');n.constant=u.LinearColor(*value,1);return n
def texture(suffix,kind):
    t=node('TextureSample');t.texture=u.load_asset('/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'+suffix)
    if not t.texture:raise RuntimeError(suffix)
    t.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind);return t
color=texture('Color','COLOR');normal=texture('NormalDX','NORMAL');packed=texture('ARH','MASKS')
# Preserve the scanned grain and broad colour variation; cool, faded outer oak.
tone=node('Multiply');link(color,'RGB',tone,'A');link(vector((.72,.69,.62)),'',tone,'B')
prop(tone,'','BASE_COLOR');prop(normal,'RGB','NORMAL');prop(packed,'R','AMBIENT_OCCLUSION')
rough=node('Max');link(packed,'G',rough,'A');link(scalar(.68),'',rough,'B');prop(rough,'','ROUGHNESS')
prop(scalar(.25),'','SPECULAR')
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
L.recompile_material(mat)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Save shutter wood')
