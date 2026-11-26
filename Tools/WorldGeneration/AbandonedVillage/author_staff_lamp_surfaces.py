"""Build shop-local copies of the lantern, fire cards and particle surfaces."""
import json
from pathlib import Path

import unreal as u
from shop_staff_light import EMBER, FOLDER, HEARTH_FIRE, TORCH_CARD, TORCH_FIRE, WICK

assets = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
emissive = u.MaterialProperty.MP_EMISSIVE_COLOR
marker = 'Staff G exposure-corrected emission'
lantern = '/Game/UnrealNormandy/MaterialInstances/MI_Lantern_00A'
card = '/Game/WorldGeneration/TemperateHills/VillageHerbalist/Lighting/M_HerbalistTorchFlame'
coal = '/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearthEmber'


def duplicate(src, dst):
    obj = assets.load_asset(dst) if assets.does_asset_exist(dst) else assets.duplicate_asset(src,dst)
    if not obj:
        raise RuntimeError('Could not create '+dst+' from '+src)
    return obj


def save(obj):
    if not assets.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def set_shop_appearance(tint, amount):
    tint.set_editor_property('constant',u.VillageInteriorLighting.glow_tint())
    amount.set_editor_property('default_value',u.VillageInteriorLighting.get_emission_strength())


def retune_existing(material, mask):
    names = [str(pin.get_editor_property('input_name')) for pin in mask.get_editor_property('inputs')]
    inputs = dict(zip(names,edit.get_inputs_for_material_expression(material,mask)))
    tint,amount = inputs['Tint'],inputs['Strength']
    if not isinstance(tint,u.MaterialExpressionConstant3Vector) or not isinstance(amount,u.MaterialExpressionScalarParameter):
        raise RuntimeError('Unexpected village lamp emission inputs on '+material.get_path_name())
    material.modify()
    set_shop_appearance(tint,amount)
    edit.recompile_material(material)
    save(material)


def retune_saved_surfaces():
    updated=[]
    for path in assets.list_assets(FOLDER.rstrip('/'),recursive=False,include_folder=False):
        if not str(path).rsplit('/',1)[-1].startswith('M_'):
            continue
        material=assets.load_asset(path)
        mask=edit.get_material_property_input_node(material,emissive)
        if mask and str(mask.get_editor_property('desc'))==marker:
            retune_existing(material,mask)
            updated.append(material.get_path_name())
    return updated


def wrap(material, gain, wick=False):
    old = edit.get_material_property_input_node(material,emissive)
    if not old:
        raise RuntimeError('No emissive branch on '+material.get_path_name())
    if str(old.get_editor_property('desc'))==marker:
        retune_existing(material,old)
        return
    output = edit.get_material_property_input_node_output_name(material,emissive)
    if wick:
        # Use the donor's powered flame mask before its exterior brightness and colour.
        nodes=list(edit.get_material_expressions(material))
        multiplier, = [n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='TS00_Emissive_Multiplier']
        stage, = [n for n in nodes if isinstance(n,u.MaterialExpressionMultiply) and multiplier in edit.get_inputs_for_material_expression(material,n)]
        old, = [n for n in edit.get_inputs_for_material_expression(material,stage) if n and n!=multiplier]
        output=''
    elif isinstance(old,u.MaterialExpressionEyeAdaptationInverse):
        # The campfire already compensates exposure at its output. Use its raw input.
        old=edit.get_inputs_for_material_expression(material,old)[0]
        output=''
    def node(cls,x,y):
        return edit.create_material_expression(material,cls,x,y)
    mask=node(u.MaterialExpressionCustom,100,-400)
    mask.set_editor_property('description',marker)
    mask.set_editor_property('desc',marker)
    mask.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    mask.set_editor_property('code','float3 sampleRGB = Source; float core = saturate(max(sampleRGB.r,max(sampleRGB.g,sampleRGB.b))); return Tint.rgb * core * Strength * SurfaceGain * InvExposure;')
    amount=node(u.MaterialExpressionScalarParameter,-420,-210)
    amount.set_editor_property('parameter_name','StaffLightAmount')
    scale=node(u.MaterialExpressionScalarParameter,-420,-80)
    scale.set_editor_property('parameter_name','QuartzLampSurfaceGain')
    scale.set_editor_property('default_value',gain)
    tint=node(u.MaterialExpressionConstant3Vector,-420,50)
    set_shop_appearance(tint,amount)
    inverse=node(u.MaterialExpressionEyeAdaptationInverse,-420,165)
    pins=(('Source',old,output),('Tint',tint,''),('Strength',amount,''),('SurfaceGain',scale,''),('InvExposure',inverse,''))
    inputs=[]
    for name,_,_ in pins:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',name)
        inputs.append(pin)
    mask.set_editor_property('inputs',inputs)
    for name,src,pin in pins:
        if not edit.connect_material_expressions(src,pin,mask,name):
            raise RuntimeError('Could not bind '+name+' on '+material.get_name())
    if not edit.connect_material_property(mask,'',emissive):
        raise RuntimeError('Could not bind emission on '+material.get_name())
    if wick or material.get_path_name().startswith(EMBER+'.'):
        material.set_editor_property('used_with_instanced_static_meshes',True)
    edit.recompile_material(material)
    save(material)


def make_surfaces():
    root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
    params=json.loads((root/'SourceAssets/ApprenticeStaff20260927/QuartzPolishV41/parameters.json').read_text(encoding='utf8'))
    gain=params['light_surface_gain']
    assets.make_directory(FOLDER.rstrip('/'))
    cache={}
    def copy_surface(original, forced=None):
        path=original.get_path_name().split('.')[0]
        if path in cache: return cache[path]
        dest=forced or FOLDER+('MI_Staff_' if isinstance(original,u.MaterialInstanceConstant) else 'M_Staff_')+original.get_name()
        copy=duplicate(path,dest)
        if isinstance(original,u.MaterialInstanceConstant):
            parent=copy_surface(original.get_editor_property('parent'))
            edit.set_material_instance_parent(copy,parent)
            edit.update_material_instance(copy)
            save(copy)
        else:
            wrap(copy,gain,original.get_name()=='M_Master_Base')
        cache[path]=copy
        return copy
    for src,dst in ((lantern,WICK),(card,TORCH_CARD),(coal,EMBER)):
        copy_surface(assets.load_asset(src),dst)
    systems={}
    for src,dest in (('/Game/Props/RomanColumn20260915/NS_TorchFlame',TORCH_FIRE),
                     ('/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire',HEARTH_FIRE)):
        system=duplicate(src,dest)
        bindings=[]
        for renderer in u.ObjectIterator(u.NiagaraSpriteRendererProperties):
            owner=renderer.get_outer()
            while owner and owner!=system: owner=owner.get_outer()
            if not owner: continue
            source=renderer.get_editor_property('material')
            if not source: continue
            if source.get_path_name().startswith(FOLDER):
                bindings.append(source.get_name())
                continue
            if not edit.get_material_property_input_node(source.get_base_material(),emissive): continue
            shader=copy_surface(source)
            renderer.modify()
            renderer.set_editor_property('material',shader)
            bindings.append(shader.get_name())
        if not bindings:
            raise RuntimeError('No flame renderer on '+dest)
        system.modify()
        save(system)
        systems[dest]=bindings
    return dict(surfaces=[v.get_path_name() for v in cache.values()],systems=systems,gain=gain)

