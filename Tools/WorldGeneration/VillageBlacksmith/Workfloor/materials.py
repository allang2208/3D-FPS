"""Local surface graphs for the smith. Match the sampler to each saved texture resource."""
import unreal as u
from author_shop import require
from Workfloor.dressing import MAT

assets=u.EditorAssetLibrary
edit=u.MaterialEditingLibrary
chapel='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
normandy='/Game/UnrealNormandy/Textures/T_MetalRust_00A_'
metal_mask='/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/T_CarpenterMetal_RHAOM'
kiln='/Game/Props/BlastFurnace20260923/Textures/T_BlastFurnace_'
hide='/Game/Building/GunWorkbenchMedieval20260928/Textures/T_GWM_leather_'


def surface(key, color, normal, roughness, ao, tint, lift, rough_range, metallic):
    path=MAT+key
    folder,name=path.rsplit('/',1)
    material=(require(path) if assets.does_asset_exist(path) else
              u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew()))
    edit.delete_all_material_expressions(material)
    for usage in ('used_with_instanced_static_meshes','used_with_nanite'):
        material.set_editor_property(usage,True)
    def node(kind):return edit.create_material_expression(material,getattr(u,'MaterialExpression'+kind))
    def wire(out,dest,pin):
        if not edit.connect_material_expressions(out[0],out[1],dest,pin):raise RuntimeError(name+' '+pin)
    def prop(out,key):
        if not edit.connect_material_property(out[0],out[1],getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError(name+' '+key)
    def value(x):
        if isinstance(x,tuple):
            n=node('Constant3Vector');n.constant=u.LinearColor(*x,1.)
        else:
            n=node('Constant');n.r=x
        return (n,'')
    def op(kind,a,b):
        n=node(kind);wire(a,n,'A');wire(b,n,'B')
        return (n,'')
    sampled={}
    def sample(path):
        if path not in sampled:
            tex=require(path)
            setting=tex.compression_settings
            kind={u.TextureCompressionSettings.TC_NORMALMAP:'NORMAL',u.TextureCompressionSettings.TC_MASKS:'MASKS',
                  u.TextureCompressionSettings.TC_GRAYSCALE:'GRAYSCALE' if tex.srgb else 'LINEAR_GRAYSCALE',
                  u.TextureCompressionSettings.TC_ALPHA:'ALPHA'}.get(setting,'COLOR' if tex.srgb else 'LINEAR_COLOR')
            if tex.virtual_texture_streaming:kind='VIRTUAL_'+kind
            n=node('TextureSample')
            n.texture=tex
            n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
            sampled[path]=n
        return sampled[path]
    tone=op('Add',op('Multiply',(sample(color),'RGB'),value(tint)),value(lift))
    r0,r1=rough_range
    rough=op('Add',op('Multiply',(sample(roughness[0]),roughness[1]),value(r1-r0)),value(r0))
    if key=='QuenchOak':
        # Existing stave vertex green encodes the damp interior and the lower waterline.
        wet=(node('VertexColor'),'G')
        damp=node('LinearInterpolate')
        wire(tone,damp,'A');wire(op('Multiply',tone,value(.55)),damp,'B');wire(wet,damp,'Alpha')
        tone=(damp,'')
        rough=op('Subtract',rough,op('Multiply',wet,value(.16)))
    prop(tone,'BASE_COLOR')
    norm=sample(normal)
    if norm.texture.compression_settings==u.TextureCompressionSettings.TC_NORMALMAP:
        prop((norm,'RGB'),'NORMAL')
    else:
        prop(op('Subtract',op('Multiply',(norm,'RGB'),value(2.)),value(1.)),'NORMAL')
    prop(rough,'ROUGHNESS')
    prop(value(metallic),'METALLIC')
    if ao:prop((sample(ao[0]),ao[1]),'AMBIENT_OCCLUSION')
    edit.layout_material_expressions(material)
    edit.recompile_material(material)
    if not assets.save_loaded_asset(material,False):raise RuntimeError('Could not save '+path)
    return material


def build():
    oak=surface('QuenchOak',chapel+'Color',chapel+'NormalDX',(chapel+'ARH','G'),(chapel+'ARH','R'),
                (.84,.68,.51),(.025,.016,.008),(.48,.88),0.)
    iron=surface('ScaleIron',normandy+'BaseColor',normandy+'Normal',(metal_mask,'R'),(metal_mask,'B'),
                 (.27,.23,.20),(.045,.045,.043),(.46,.79),.69)
    mats={'Oak':require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
          'Endgrain':require('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterCut'),
          'Iron':iron,'QuenchOak':oak}
    for key,suffix,source,tint,lift in [
            ('Stone','HearthStone','Masonry',(.65,.62,.55),(.014,.013,.010)),
            ('Brick','FiredBrick','Firebrick',(.78,.61,.48),(.025,.012,.007))]:
        prefix=kiln+source+'_'
        mats[key]=surface(suffix,prefix+'BaseColor',prefix+'Normal',(prefix+'Roughness','R'),(prefix+'AO','R'),
                          tint,lift,(.61,.95),0.)
    mats['Leather']=surface('BellowsLeather',hide+'basecolor',hide+'normal',(hide+'rough','R'),None,
                            (.63,.43,.32),(.029,.013,.008),(.48,.82),0.)
    for key in ('Coal','Ash'):
        mats[key]=require('/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearth'+key)
    return mats

