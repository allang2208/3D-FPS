"""Import the approved alpine cutout and author/save its UI reveal material."""
from pathlib import Path
import json
import unreal as u

HERE=Path(__file__).resolve().parent
DEST='/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAlpineV23'
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
task.filename=str(HERE/'T_MountainEcho_Alpine.png')
task.destination_path=DEST
task.destination_name='T_MountainEcho_Alpine'
task.automated=True
task.replace_existing=True
task.save=False
TOOLS.import_asset_tasks([task])
texture=u.load_asset(DEST+'/T_MountainEcho_Alpine')
if not isinstance(texture,u.Texture2D):raise RuntimeError('Alpine texture import did not create Texture2D')
for key,value in {
    'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
    'lod_group':u.TextureGroup.TEXTUREGROUP_UI,
    'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'srgb':True,'never_stream':True,'max_texture_size':1024,
    'address_x':u.TextureAddress.TA_CLAMP,'address_y':u.TextureAddress.TA_CLAMP,
    'filter':u.TextureFilter.TF_BILINEAR
}.items():texture.set_editor_property(key,value)

name='M_MountainEcho_AlpineHUD'
mat=u.load_asset(DEST+'/'+name) or TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
# Delete from a snapshot: this engine's bulk-delete mutates its iterated array.
for expression in list(LIB.get_material_expressions(mat)):
    LIB.delete_material_expression(mat,expression)
mat.set_editor_property('material_domain',u.MaterialDomain.MD_UI)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
tex=LIB.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
tex.set_editor_property('parameter_name','AlpineTexture')
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
float lit=p<=0.0001?0:(p>=0.9999?1:1-smoothstep(p-0.0075,p+0.0075,UV.x));
float alpha=pow(saturate(Alpha),1.12)*(1-smoothstep(0.69,0.88,UV.y));
float luma=dot(RGB,float3(0.2126,0.7152,0.0722));
// Keep fractional-alpha fringe in the same gold family; opaque rock stays intact.
float edge=1-smoothstep(0.20,0.75,Alpha);
float3 stone=lerp(RGB,luma*float3(1.18,0.87,0.48),edge);
float3 dormant=lerp(stone*0.23,float3(0.26,0.205,0.12)*sqrt(max(0,luma)),0.34);
float3 active=stone*(0.94+0.06*Breath);
float crest=smoothstep(0.10,0.65,max(stone.r,max(stone.g,stone.b)));
float front=exp(-pow((UV.x-p)/0.025,2));
active+=float3(0.95,0.63,0.22)*crest*(0.22*Gain*front+0.12*Pulse+0.018*Breath);
return float4(lerp(dormant,active,lit),alpha*lerp(0.58,0.96,lit));
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
         'source':'T_MountainEcho_Alpine.png','rgba':True,'max_texture_size':1024,
         'ui_material':True,'dynamic_parameter':'ResonanceState',
         'progress':'0 / 1/3 / 2/3 / 1; continuous animated reveal',
         'runtime_tested':False,'viewport_rendered':False}
(HERE/'import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_ALPINE_HUD_SAVED '+json.dumps(receipt))
