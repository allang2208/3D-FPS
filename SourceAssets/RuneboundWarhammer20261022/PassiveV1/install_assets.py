"""Create/save passive-only materials in the existing UE editor through its batch bridge."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/PassiveV1'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
TAG='RuneboundPassiveOwner';OWNER='RuneboundPassiveV1_20261022'
receipt={'complete':False,'assets':[],'runtime_tested':False,'rendered':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def owned(path):
    asset=u.load_asset(path) if E.does_asset_exist(path) else None
    dirty=any(str(pkg.get_name())==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:raise RuntimeError('Preserve unsaved package '+path)
    if asset and E.get_metadata_tag(asset,TAG)!=OWNER:raise RuntimeError('Preserve unowned package '+path)
    return asset
def save(asset):
    E.set_metadata_tag(asset,TAG,OWNER)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record();return asset
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin,out=''):
    if isinstance(pin,int):pin=str(L.get_material_expression_input_names(dst)[pin])
    if not L.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Cannot wire '+str(pin))
def finish(mat):
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compile failed '+str(errors))
    return save(mat)
def custom_output(mat,code,inputs):
    c=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    c.set_editor_property('inputs',pins)
    for key,expr in inputs.items():wire(expr,c,key)
    rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(c,rgb,0);wire(c,alpha,0)
    L.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)

if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('PIE is running; asset write deferred')
record()
mask=owned(D+'/T_RuneboundNativeRuneMask')
if not mask:
    task=u.AssetImportTask();task.filename=str(P/'Export/T_RuneboundNativeRuneMask.png')
    task.destination_path=D;task.destination_name='T_RuneboundNativeRuneMask';task.automated=True;task.save=False
    A.import_asset_tasks([task]);mask=u.load_asset(D+'/T_RuneboundNativeRuneMask')
if not mask:raise RuntimeError('Rune mask import failed')
mask.set_editor_property('srgb',False);mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
save(mask)

name='M_RuneboundAwakeSurface';surface=owned(D+'/'+name)
if not surface:
    source=u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/Materials/M_RuneboundWarhammerSurface')
    surface=A.duplicate_asset(name,D,source)
    E.set_metadata_tag(surface,TAG,OWNER)
    nmask=node(surface,u.MaterialExpressionTextureSample,texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    awake=node(surface,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.)
    strength=node(surface,u.MaterialExpressionMultiply);wire(nmask,strength,'A','R');wire(awake,strength,'B')
    blue=node(surface,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.45,3.0,9.0,1.))
    emission=node(surface,u.MaterialExpressionMultiply);wire(strength,emission,'A');wire(blue,emission,'B')
    substrate=next(x for x in L.get_material_expressions(surface) if isinstance(x,u.MaterialExpressionSubstrateShadingModels))
    emissive_pin=next(str(pin) for pin in L.get_material_expression_input_names(substrate)
        if str(pin).replace(' ','').lower().startswith('emissive'))
    wire(emission,substrate,emissive_pin)
    L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
surface.set_editor_property('used_with_skeletal_mesh',False);surface.set_editor_property('used_with_nanite',True)
finish(surface)

name='M_RuneboundEnergyHud';hud=owned(D+'/'+name)
if not hud:
    hud=A.duplicate_asset(name,D,u.load_asset('/Game/Weapons/AzureDragon20261004/HudV10/Materials/M_AzureDragonHudV10'))
if not hud:raise RuntimeError('HUD donor material missing')
custom=next(x for x in L.get_material_expressions(hud) if isinstance(x,u.MaterialExpressionCustom))
custom.set_editor_property('code',(P/'RuneboundEnergyHud.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description','Runebound blue energy vessel, rune seal, no dragon head, floating motes')
finish(hud)

name='M_RuneboundMote';mote=owned(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mote)
for key,value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True).items():mote.set_editor_property(key,value)
custom_output(mote,(P/'RuneboundMote.hlsl').read_text(encoding='utf-8'),{
    'UV':node(mote,u.MaterialExpressionTextureCoordinate),
    'Strength':node(mote,u.MaterialExpressionScalarParameter,parameter_name='Strength',default_value=0.)})
finish(mote)
slots={}
for file in ('exports.json','adapted_exports.json'):
    for row in json.loads((P.parent/'ModulesV1'/file).read_text(encoding='utf-8-sig'))['parts']:
        path='/Game/Weapons/RuneboundWarhammer20261022/ModulesV1/'+row['mesh']
        mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Cannot bind passive to missing module '+path)
        slots[mesh.get_path_name()]=[str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')
            if s.material_interface and s.material_interface.get_path_name().startswith('/Game/Weapons/RuneboundWarhammer20261022/Materials/M_RuneboundWarhammerSurface.')]
receipt['native_material_slots']=slots
receipt['complete']=True;record()
print('RUNEBOUND_PASSIVE_ASSETS_SAVED '+json.dumps(receipt))
