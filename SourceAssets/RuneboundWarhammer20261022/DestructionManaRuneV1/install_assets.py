"""Author a host-only Substrate rune surface, leaving the original materials intact."""
import json,os
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/DestructionManaRuneV1'
OWNER='RuneboundDestructionManaRune20261022';TAG='DestructionManaRuneOwner'
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
if os.environ.get('RUNEBOUND_NEW_ASSETS_ONLY')=='1':
    for asset in ('M_RuneboundDestructionRuneSurface','M_RuneboundDestructionMote','T_DestructionManaRuneIcon'):
        if E.does_asset_exist(D+'/'+asset):raise RuntimeError('Use owning editor for existing asset '+asset)
record();name='M_RuneboundDestructionRuneSurface';path=D+'/'+name
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
    custom=node(mat,u.MaterialExpressionCustom,code=(P/'DestructionRune.hlsl').read_text(encoding='utf-8'),
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=pins,description='Destruction Mana: native rune converging waves, violet core and blue-white fracture pulses')
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
custom.set_editor_property('code',(P/'DestructionRune.hlsl').read_text(encoding='utf-8'))
mat.set_editor_property('used_with_skeletal_mesh',False);mat.set_editor_property('used_with_nanite',True)
L.layout_material_expressions(mat)
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Destruction rune material compile failed '+str(errors))
E.set_metadata_tag(mat,TAG,OWNER)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Save failed '+path)
receipt.update(assets=[mat.get_path_name()],source_material='/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundAwakeSurface')

# A separate bounded-pool shard material leaves the blue base particles intact.
name='M_RuneboundDestructionMote';path=D+'/'+name
if any(str(pkg.get_name())==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve dirty '+path)
mote=u.load_asset(path) if E.does_asset_exist(path) else None
if mote and E.get_metadata_tag(mote,TAG)!=OWNER:raise RuntimeError('Preserve unowned '+path)
if not mote:mote=A.duplicate_asset(name,D,u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundMote'))
custom=next(n for n in L.get_material_expressions(mote) if isinstance(n,u.MaterialExpressionCustom))
custom.set_editor_property('code',(P/'DestructionMote.hlsl').read_text(encoding='utf-8'))
if L.recompile_material(mote):raise RuntimeError('Destruction mote material compile failed')
E.set_metadata_tag(mote,TAG,OWNER)
if not E.save_loaded_asset(mote,False):raise RuntimeError('Mote save failed')
receipt['assets'].append(mote.get_path_name());record()
name='T_DestructionManaRuneIcon';path=D+'/'+name
if E.does_asset_exist(path):
    tex=u.load_asset(path)
    if E.get_metadata_tag(tex,TAG)!=OWNER:raise RuntimeError('Preserve unowned '+path)
else:
    task=u.AssetImportTask();task.filename=str(P/'Export/ue_runebound_warhammer_blade_2_destruction_mana_rune.png')
    task.destination_path=D;task.destination_name=name;task.automated=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(path)
if not tex:raise RuntimeError('Rune icon import failed')
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
E.set_metadata_tag(tex,TAG,OWNER)
if not E.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed')
receipt['assets'].append(tex.get_path_name());receipt['complete']=True
record();print('RUNEBOUND_DESTRUCTION_MANA_MATERIAL_SAVED '+json.dumps(receipt))
