"""Save the V04 pressure-wave material and four sound cues; no game/preview."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/PresentationV04')
DEST='/Game/Monsters/BellowSacLobber/V04'
LIB=u.MaterialEditingLibrary
EL=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
record={'saved':[],'gameplay_tested':False,'auditioned':False,'rendered':False}
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved V04 asset changes')

def save(asset):
    if not EL.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    record['saved'].append(asset.get_path_name())
    (ROOT/'ue_assets_saved.json').write_text(json.dumps(record,indent=2),encoding='utf-8')

manifest=json.loads((ROOT/'audio_manifest.json').read_text(encoding='utf-8'))
for name,params in manifest['cues'].items():
    task=u.AssetImportTask()
    task.filename=str(ROOT/(name+'.wav'));task.destination_path=DEST+'/Audio';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    TOOLS.import_asset_tasks([task])
    sound=u.load_asset(DEST+'/Audio/'+name)
    sound.set_editor_property('volume',1.)
    sound.set_editor_property('pitch',1.)
    sound.set_editor_property('looping',params['loop'])
    EL.set_metadata_tag(sound,'Bellow.Audio','Source peak -2.5 dBFS; runtime gain 1.25; mono spatial, loud near field')
    save(sound)

name='M_BellowPressureWave';path=DEST+'/FX/'+name
source='/Game/Monsters/Mutant3Meshy/Effects/M_Mutant3LandingWave'
material=u.load_asset(path) if EL.does_asset_exist(path) else EL.duplicate_asset(source,path)
material.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
material.set_editor_property('refraction_depth_bias',2.)
material.set_editor_property('output_translucent_velocity',False)
material.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)

def connect(a,b,pin,output=''):
    if not LIB.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material pin '+pin)

def custom(code,key,node,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    expr=LIB.create_material_expression(material,u.MaterialExpressionCustom)
    inp=u.CustomInput();inp.set_editor_property('input_name',key)
    expr.set_editor_property('inputs',[inp]);expr.set_editor_property('code',code);expr.set_editor_property('output_type',kind)
    connect(node,expr,key);return expr

expressions=LIB.get_material_expressions(material)
surface=next(e for e in expressions if isinstance(e,u.MaterialExpressionSubstrateShadingModels))
depth=next(e for e in expressions if isinstance(e,u.MaterialExpressionDepthFade))
opacity=custom('return Mask*.045;','Mask',depth)
refraction=custom('return 1+Mask*.052;','Mask',depth)
normal=LIB.create_material_expression(material,u.MaterialExpressionTextureSample)
normal.set_editor_property('texture',u.load_asset('/Game/Vefects/Easy_Impact_Frames/VFX/Extras/Textures/Shockwaves/T_VFX_Easy_Shockwaves_Noise_01_Normal'))
normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
connect(opacity,surface,'Opacity')
connect(normal,surface,'Normal','RGB')
LIB.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
LIB.connect_material_property(refraction,'',u.MaterialProperty.MP_REFRACTION)
LIB.connect_material_property(normal,'RGB',u.MaterialProperty.MP_NORMAL)
EL.set_metadata_tag(material,'Source','Derived from owned Easy Impact Frames noise / Mutant3 pooled ground-wave contract; per-instance pressure refraction')
errors=LIB.recompile_material(material)
if errors:raise RuntimeError('Material compilation: '+str(errors))
save(material)
record['status']='saved'
(ROOT/'ue_assets_saved.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('BELLOW_PRESENTATION_V04_SAVED '+json.dumps(record),flush=True)
