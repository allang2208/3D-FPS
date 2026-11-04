"""Import the accepted blue-flame bar and save the animated runtime UI material."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeHUD20261103'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving charge HUD')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved HUD assets: '+str(dirty))
E.make_directory(DEST)
task=u.AssetImportTask()
task.set_editor_properties(dict(filename=str(P/'T_StarMarrowChargeBar.png'),destination_path=DEST,
    destination_name='T_StarMarrowChargeBar',automated=True,replace_existing=True,save=False))
A.import_asset_tasks([task])
texture=E.load_asset(DEST+'/T_StarMarrowChargeBar')
if not texture:raise RuntimeError('Charge bar import failed')
texture.set_editor_properties(dict(compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
    lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    srgb=True,never_stream=True,max_texture_size=2048,address_x=u.TextureAddress.TA_CLAMP,
    address_y=u.TextureAddress.TA_CLAMP,filter=u.TextureFilter.TF_BILINEAR))
name='M_StarMarrowChargeHUD';path=DEST+'/'+name
mat=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
if not mat:raise RuntimeError('Charge HUD material creation failed')
for n in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,n)
mat.set_editor_properties(dict(material_domain=u.MaterialDomain.MD_UI,blend_mode=u.BlendMode.BLEND_TRANSLUCENT))
def node(cls,**props):
    n=L.create_material_expression(mat,cls);n.set_editor_properties(props);return n
def wire(src,out,dst,pin):
    if not L.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Cannot connect '+pin)
uv=node(u.MaterialExpressionTextureCoordinate)
texture_node=node(u.MaterialExpressionTextureObjectParameter,parameter_name='ChargeArt',texture=texture)
progress=node(u.MaterialExpressionScalarParameter,parameter_name='ChargeProgress',default_value=1.)
time=node(u.MaterialExpressionTime)
shader=node(u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
    code=(P/'charge_bar.hlsl').read_text(encoding='utf8'),description='Accepted blue bar: independent frame, energy, flames and sparks')
inputs={'UV':uv,'ArtTexture':texture_node,'Progress':progress,'T':time}
pins=[]
for key in inputs:
    pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
shader.set_editor_property('inputs',pins)
for key,n in inputs.items():wire(n,'',shader,key)
for alpha,prop in [(False,u.MaterialProperty.MP_EMISSIVE_COLOR),(True,u.MaterialProperty.MP_OPACITY)]:
    mask=node(u.MaterialExpressionComponentMask,r=not alpha,g=not alpha,b=not alpha,a=alpha)
    wire(shader,'',mask,'')
    if not L.connect_material_property(mask,'',prop):raise RuntimeError('Cannot connect UI output')
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Charge HUD shader compile failed: '+str(errors))
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
saved=[]
for obj in [texture,mat]:
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    saved.append(obj.get_path_name())
(P/'import-receipt.json').write_text(json.dumps({'complete':True,'saved_assets':saved,
    'source_size':[2172,724],'alpha':True,'gameplay_tested':False,'visual_tested':False},indent=2),encoding='utf8')
print('STAR_MARROW_CHARGE_HUD_SAVED',saved)
