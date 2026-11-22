"""Bronze wall torches for the plaza apothecary. Distances are in room-local cm."""
import math

import unreal as u

from author_shop import pose, require
from shop_staff_light import TORCH_CARD, configure


BODY = '/Game/Props/RomanColumn20260915/SM_BronzeTorch'
BRONZE = '/Game/Props/RomanColumn20260915/M_Bronze'
IRON = '/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'
ATLAS = '/Game/TorchFire/Texture/T_TorchFire'
DEST = '/Game/WorldGeneration/TemperateHills/VillageHerbalist/Lighting'
MATERIAL = 'M_HerbalistTorchFlame'
SCALE = .9
# Bracket pivots and inward yaw in the shop frame.
TORCHES = (((-279.,-344.,176.),90.), ((346.,10.,184.),180.))


def offset(anchor,yaw,forward,rise):
    a = math.radians(yaw)
    return (anchor[0]+math.cos(a)*forward,anchor[1]+math.sin(a)*forward,anchor[2]+rise)


def add_fixtures(house,add):
    for index,(anchor,yaw) in enumerate(TORCHES):
        # Donor arm extends +X from local x=16 to its cup at x=50.
        # A forged socket seats the straight shank in the rough masonry.
        state = 'Common' if index == 0 else 'Repaired'
        socket_center = pose(house,*offset(anchor,yaw,23.,0.)).translation
        socket = u.Transform(location=socket_center,
                             rotation=u.Rotator(pitch=90.,yaw=house[5]+yaw),
                             scale=[.14,.14,.17])
        add(state,'/Engine/BasicShapes/Cylinder',socket,(IRON,),profile='NoCollision')
        if index == 0:
            add('Ruined',BODY,pose(house,*anchor,yaw,SCALE),(IRON,),profile='NoCollision')
        add('Repaired',BODY,pose(house,*anchor,yaw,SCALE),(BRONZE,),profile='NoCollision')


# Reuse the project's 8x8 RGB-masked fire flipbook on a single camera-facing
# card per cup. Time is evaluated by the visible material; hidden fires have
# no emitter or particle light running in the ruined shop.
FLAME_COLOR = """
float frame = frac(Clock * (18.0 / 64.0) + frac(dot(Location.xy,float2(.00071,.00119)))) * 64.0;
float first = floor(frame);
float second = fmod(first + 1.0,64.0);
float2 uv = clamp(CardUV,.008,.992);
float2 a = (uv + float2(fmod(first,8.0),floor(first / 8.0))) / 8.0;
float2 b = (uv + float2(fmod(second,8.0),floor(second / 8.0))) / 8.0;
float3 masks = lerp(Texture2DSample(Sheet,SheetSampler,a).rgb,
                    Texture2DSample(Sheet,SheetSampler,b).rgb,frac(frame));
float edge = smoothstep(.008,.045,min(min(uv.x,1.0-uv.x),min(uv.y,1.0-uv.y)));
float flame = smoothstep(.018,.85,max(masks.g,masks.b));
return edge * (float3(5.3,.78,.045)*flame +
               float3(9.2,5.2,1.34)*pow(saturate(masks.g),2.5));
"""


def flame_material():
    library = u.EditorAssetLibrary
    path = DEST+'/'+MATERIAL
    if library.does_asset_exist(path):
        return require(path)
    tools = u.AssetToolsHelpers.get_asset_tools()
    edit = u.MaterialEditingLibrary
    mat = tools.create_asset(MATERIAL,DEST,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    atlas = require(ATLAS)
    tex = edit.create_material_expression(mat,u.MaterialExpressionTextureObject,-600,-200)
    tex.texture = atlas
    if atlas.compression_settings == u.TextureCompressionSettings.TC_MASKS:
        tex.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_MASKS
    else:
        tex.sampler_type = (u.MaterialSamplerType.SAMPLERTYPE_COLOR if atlas.srgb
                            else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    sources = (
        ('Sheet',tex),
        ('CardUV',edit.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-600,-50)),
        ('Clock',edit.create_material_expression(mat,u.MaterialExpressionTime,-600,80)),
        ('Location',edit.create_material_expression(mat,u.MaterialExpressionObjectPositionWS,-600,210)),
    )
    flame = edit.create_material_expression(mat,u.MaterialExpressionCustom,-260,0)
    pins = []
    for name,_ in sources:
        pin = u.CustomInput()
        pin.set_editor_property('input_name',name)
        pins.append(pin)
    flame.set_editor_property('inputs',pins)
    flame.set_editor_property('code',FLAME_COLOR)
    flame.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    for name,source in sources:
        if not edit.connect_material_expressions(source,'',flame,name):
            raise RuntimeError('Could not connect torch flipbook input '+name)
    if not edit.connect_material_property(flame,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Could not connect torch emissive')
    edit.recompile_material(mat)
    if not library.save_loaded_asset(mat,False):
        raise RuntimeError('Could not save '+path)
    return mat


def add_lighting(house,repaired_actor,component):
    mat = require(TORCH_CARD)
    for anchor,yaw in TORCHES:
        # The donor's cup lip is at (50,0,42.6). Put the card's base inside
        # the lip and the light at the flame's centre, above the opaque bowl.
        flame_pos = pose(house,*offset(anchor,yaw,50*SCALE,62*SCALE)).translation
        card = component(repaired_actor,u.MaterialBillboardComponent)
        card.set_mobility(u.ComponentMobility.STATIC)
        card.set_world_location(flame_pos,False,True)
        # MaterialBillboard renders UV.V along its BaseSizeX half-extent.
        card.add_element(mat,None,False,25.,22.,None)
        card.set_cast_shadow(False)
        card.set_collision_profile_name('NoCollision')
        card.set_editor_property('ld_max_draw_distance',2600.)

        light = component(repaired_actor,u.PointLightComponent)
        light.set_mobility(u.ComponentMobility.MOVABLE)
        light.set_world_location(flame_pos,False,True)
        configure(light)
        light.set_max_draw_distance(2600.)
        light.set_max_distance_fade_range(500.)
        for part in (card,light):
            part.component_tags = ['VillageHerbalist.Repaired','VillageHerbalist.NoCollision']
            part.set_visibility(False)
            part.set_hidden_in_game(True)
    return len(TORCHES)
