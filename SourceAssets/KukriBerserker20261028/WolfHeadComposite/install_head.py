"""Publish the generated wolf-head crown and cut only the original bar's upper cap."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/WolfHeadComposite/install_head.py').resolve().parent
BASE='/Game/Weapons/Kukri20261020/Berserker20261028'
DEST=BASE+'/WolfHeadComposite'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
# Material/texture-only authoring is safe in an existing editor. Do not start or
# stop gameplay, replace Actors, or alter any player state for this import.
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if BASE+'/M_BerserkerEnergyHud' in dirty or any(p.startswith(DEST) for p in dirty):
    raise RuntimeError('Preserve unsaved HUD packages')
code=(P/'BerserkerWolfHeadHud.hlsl').read_text('utf-8')
receipt={'complete':False,'saved_assets':[],'runtime_tested':False,
    'design':'Original lower column retained; upper cap removed; generated dimensional wolf head joined at neck',
    'reference':'AzureDragon20261004/HudV10 layered concept-image HUD',
    'hlsl_sha256':hashlib.sha256(code.encode()).hexdigest()}
def record(): (P/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());record()
record()
t=u.AssetImportTask();t.filename=str(P/'Art/WolfHead_Crown.png')
t.destination_path=DEST+'/Textures';t.destination_name='T_BerserkerWolfHead'
t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
tex=u.load_asset(t.destination_path+'/'+t.destination_name)
if not tex:raise RuntimeError('Wolf head import failed')
tex.set_editor_properties({'srgb':False,'never_stream':True,'max_texture_size':2048,
    'compression_settings':u.TextureCompressionSettings.TC_BC7,
    'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'address_x':u.TextureAddress.TA_CLAMP,'address_y':u.TextureAddress.TA_CLAMP})
save(tex)
hud=u.load_asset(BASE+'/M_BerserkerEnergyHud')
if not hud:raise RuntimeError('Missing active berserker HUD material')
receipt['previous_authoring']=E.get_metadata_tag(hud,'SourceAuthoring')
expressions=L.get_material_expressions(hud)
custom=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom))
retired={'VesselEmptyTex','VesselFullTex','VesselMaskTex','WolfTex','WolfReliefTex'}
pins=[p for p in custom.get_editor_property('inputs') if str(p.get_editor_property('input_name')) not in retired]
if not any(str(p.get_editor_property('input_name'))=='WolfHeadTex' for p in pins):
    pin=u.CustomInput();pin.set_editor_property('input_name','WolfHeadTex');pins.append(pin)
custom.set_editor_property('inputs',pins)
for n in expressions:
    if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name')) in retired:
        L.delete_material_expression(hud,n)
obj=next((n for n in L.get_material_expressions(hud) if isinstance(n,u.MaterialExpressionTextureObjectParameter)
          and str(n.get_editor_property('parameter_name'))=='WolfHeadTex'),None)
if obj is None:
    obj=L.create_material_expression(hud,u.MaterialExpressionTextureObjectParameter)
    obj.set_editor_property('parameter_name','WolfHeadTex')
obj.set_editor_properties({'texture':tex,'sampler_type':u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR})
if not L.connect_material_expressions(obj,'',custom,'WolfHeadTex'):raise RuntimeError('Wolf head texture connection failed')
custom.set_editor_properties({'code':code,'description':'BerserkerWolfHeadComposite'})
hud.set_editor_properties({'material_domain':u.MaterialDomain.MD_UI,'blend_mode':u.BlendMode.BLEND_TRANSLUCENT})
E.set_metadata_tag(hud,'SourceAuthoring','KukriBerserker20261028/WolfHeadComposite')
E.set_metadata_tag(hud,'EnergyBarDesign','OriginalLowerColumn_CutUpperCap_GeneratedWolfHead')
E.set_metadata_tag(hud,'HelixPresentation','DiscreteSparkFlowAndDriftV1')
errors=L.recompile_material(hud)
if errors:raise RuntimeError('HUD material compilation failed: '+str(errors))
if not u.PoisonMaggotMonster.compile_material_assets([hud]):raise RuntimeError('HUD material compilation failed')
save(hud)
receipt['complete']=True;record()
print('WOLF_HEAD_COMPOSITE_SAVED',len(receipt['saved_assets']))
