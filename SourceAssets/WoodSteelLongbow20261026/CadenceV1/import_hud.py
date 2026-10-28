"""Import the approved alpine cutout and author/save its UI reveal material."""
from pathlib import Path
import json
import unreal as u

HERE=Path(__file__).resolve().parent
DEST='/Game/Weapons/WoodSteelLongbow20261026/CadenceV1'
EAL=u.EditorAssetLibrary
LIB=u.MaterialEditingLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('Preserve the running Play session; finish Play before importing this HUD asset')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved alpine HUD packages: '+str(dirty))
EAL.make_directory(DEST)

task=u.AssetImportTask()
task.filename=str(HERE/'T_Cadence_HUD.png')
task.destination_path=DEST
task.destination_name='T_Cadence_HUD'
task.automated=True
task.replace_existing=True
task.save=False
TOOLS.import_asset_tasks([task])
texture=u.load_asset(DEST+'/T_Cadence_HUD')
if not isinstance(texture,u.Texture2D):raise RuntimeError('Alpine texture import did not create Texture2D')
for key,value in {
    'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
    'lod_group':u.TextureGroup.TEXTUREGROUP_UI,
    'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'srgb':True,'never_stream':True,'max_texture_size':1024,
    'address_x':u.TextureAddress.TA_CLAMP,'address_y':u.TextureAddress.TA_CLAMP,
    'filter':u.TextureFilter.TF_BILINEAR
}.items():texture.set_editor_property(key,value)

name='M_Cadence_HUD'
mat=u.load_asset(DEST+'/'+name) or TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
# Delete from a snapshot: this engine's bulk-delete mutates its iterated array.
for expression in list(LIB.get_material_expressions(mat)):
    LIB.delete_material_expression(mat,expression)
mat.set_editor_property('material_domain',u.MaterialDomain.MD_UI)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
tex=LIB.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
tex.set_editor_property('parameter_name','CadenceTexture')
tex.set_editor_property('texture',texture)
if not LIB.connect_material_expressions(uv,'',tex,'UVs'):
    raise RuntimeError('Failed to connect HUD texture coordinates')
state=LIB.create_material_expression(mat,u.MaterialExpressionVectorParameter)
state.set_editor_property('parameter_name','ResonanceState')
state.set_editor_property('default_value',u.LinearColor(0,0,0,0))
custom=LIB.create_material_expression(mat,u.MaterialExpressionCustom)
custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
custom.set_editor_property('code','''
float p=saturate(Progress);
float lit=p<=0.0001?0:(p>=0.9999?1:1-smoothstep(p-0.008,p+0.008,UV.x));
float full=smoothstep(0.99,1.0,p);
float alpha=pow(saturate(Alpha),1.25);
float luma=dot(RGB,float3(0.2126,0.7152,0.0722));
float3 silver=luma*float3(0.72,0.89,1.04);
float3 gold=luma*float3(1.14,0.97,0.67);
float3 dormant=luma*float3(0.20,0.25,0.29);
float front=exp(-pow((UV.x-p)/0.027,2));
float crest=smoothstep(0.35,0.95,luma);
float3 active=lerp(silver,gold,full)*(0.92+0.08*Breath);
active+=lerp(float3(0.55,0.80,1),float3(1,0.86,0.58),full)*crest*(0.35*Gain*front+full*(0.16*Pulse+0.065*Breath));
return float4(lerp(dormant,active,lit),alpha*lerp(0.62,1,lit));

''')
inputs={'UV':(uv,''),'RGB':(tex,'RGB'),'Alpha':(tex,'A'),
        'Progress':(state,'R'),'Gain':(state,'G'),'Breath':(state,'B'),'Pulse':(state,'A')}
pins=[]
for key in inputs:
    pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
custom.set_editor_property('inputs',pins)
for key,(node,output) in inputs.items():
    if not LIB.connect_material_expressions(node,output,custom,key):raise RuntimeError('Failed to wire '+key)
rgb=LIB.create_material_expression(mat,u.MaterialExpressionComponentMask)
opacity=LIB.create_material_expression(mat,u.MaterialExpressionComponentMask)
for node,channels in ((rgb,{'r':True,'g':True,'b':True,'a':False}),(opacity,{'r':False,'g':False,'b':False,'a':True})):
    for key,value in channels.items():node.set_editor_property(key,value)
    # ComponentMask uses an unnamed first input in UE 5.8, not "Input".
    if not LIB.connect_material_expressions(custom,'',node,''):
        raise RuntimeError('Failed to connect the HUD custom output to its component mask')
if not LIB.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Failed to connect HUD color output')
if not LIB.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Failed to connect HUD opacity output')
errors=LIB.recompile_material(mat)
if errors:raise RuntimeError('HUD material compilation failed: '+str(errors))
if '-nullrhi' not in u.SystemLibrary.get_command_line().lower():
    LIB.get_statistics(mat) # Finish this material's shader jobs before saving.
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost(),mat.get_outermost()],False):
    raise RuntimeError('Failed to save alpine HUD packages')
receipt={'complete':True,'saved_assets':[texture.get_path_name(),mat.get_path_name()],
         'source':'T_Cadence_HUD.png','rgba':True,'max_texture_size':1024,
         'ui_material':True,'dynamic_parameter':'ResonanceState',
         'progress':'0 / 1/5 / 2/5 / 3/5 / 4/5 / 1; animated reveal',
         'runtime_tested':False,'viewport_rendered':False}
(HERE/'hud-import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_ALPINE_HUD_SAVED '+json.dumps(receipt))
