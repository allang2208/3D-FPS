"""Author a host-only Substrate rune surface, leaving the original materials intact."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/SwiftManaRuneV1'
OWNER='RuneboundSwiftManaRune20261022';TAG='SwiftManaRuneOwner'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'tested':False,'rendered_acceptance':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def wire(source,out,target,pin):
    if not L.connect_material_expressions(source,out,target,pin):raise RuntimeError('Cannot wire '+pin)

if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('PIE active; preserve editor state')
record();name='M_RuneboundSwiftRuneSurface';path=D+'/'+name
if any(str(pkg.get_name())==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve dirty '+path)
mat=u.load_asset(path) if E.does_asset_exist(path) else None
if mat and E.get_metadata_tag(mat,TAG)!=OWNER:raise RuntimeError('Preserve unowned '+path)
if not mat:
    source=u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundAwakeSurface')
    if not source:raise RuntimeError('Native awake surface missing')
    mat=A.duplicate_asset(name,D,source)
    E.set_metadata_tag(mat,TAG,OWNER)
    old=list(L.get_material_expressions(mat))
    awake=next(n for n in old if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='RuneAwake')
    surface=next(n for n in old if isinstance(n,u.MaterialExpressionSubstrateShadingModels))
    mask=u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/T_RuneboundNativeRuneMask')
    inputs={'UV':node(mat,u.MaterialExpressionTextureCoordinate),'T':node(mat,u.MaterialExpressionTime),
        'RuneAwake':awake,'NativeMask':node(mat,u.MaterialExpressionTextureObject,texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)}
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom=node(mat,u.MaterialExpressionCustom,code=(P/'SwiftRune.hlsl').read_text(encoding='utf-8'),
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=pins,description='Swift Mana: original native rune UVs, blue traveling light, stronger awakening')
    for key,value in inputs.items():wire(value,'',custom,key)
    emissive=next(str(pin) for pin in L.get_material_expression_input_names(surface) if str(pin).replace(' ','').lower().startswith('emissive'))
    wire(custom,'',surface,emissive)
    if not L.connect_material_property(custom,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Legacy emissive connection failed')
custom=next(n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom))
preview=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionScalarParameter)
    and str(n.get_editor_property('parameter_name'))=='PreviewTime'),None)
if not preview:preview=node(mat,u.MaterialExpressionScalarParameter,parameter_name='PreviewTime',default_value=-1.)
pins=list(custom.get_editor_property('inputs'))
if not any(str(pin.get_editor_property('input_name'))=='PreviewTime' for pin in pins):
    pin=u.CustomInput();pin.set_editor_property('input_name','PreviewTime');pins.append(pin);custom.set_editor_property('inputs',pins)
wire(preview,'',custom,'PreviewTime')
custom.set_editor_property('code',(P/'SwiftRune.hlsl').read_text(encoding='utf-8'))
mat.set_editor_property('used_with_skeletal_mesh',False);mat.set_editor_property('used_with_nanite',True)
L.layout_material_expressions(mat)
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Swift rune material compile failed '+str(errors))
E.set_metadata_tag(mat,TAG,OWNER)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Save failed '+path)
receipt.update(complete=True,assets=[mat.get_path_name()],source_material='/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundAwakeSurface')
record();print('RUNEBOUND_SWIFT_MANA_MATERIAL_SAVED '+json.dumps(receipt))
