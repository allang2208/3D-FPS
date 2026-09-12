"""Check the persisted cuff material and the actual M4/AKM material hosts."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).parent
SOURCE='/Game/Weapons/M4InfimaV3'
mi=u.load_asset(SOURCE+'/MI_Manny_02');assert mi
assert mi.parent.get_path_name()=='/Game/Characters/ArmsGloveCuff3cmCandidate/M_Manny_RolledCuff3cm_02.M_Manny_RolledCuff3cm_02'
L=u.MaterialEditingLibrary
start=L.get_material_instance_scalar_parameter_value(mi,'GloveCuffStart')
scatter=L.get_material_instance_scalar_parameter_value(mi,'SkinScatterStrength')
assert abs(start-0.8899122968)<.0001,start
assert abs(scatter-.18)<.0001,scatter
cuff_field=u.load_asset('/Game/Characters/ArmsGloveCuff3cmCandidate/T_Manny_Cuff3cmField');assert cuff_field
assert cuff_field.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_GRAYSCALE
assert not cuff_field.get_editor_property('srgb')
roll=u.load_asset('/Game/Characters/ArmsGloveCuff3cmCandidate/T_Manny_Cuff3cmRollNormal');assert roll
assert roll.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_NORMALMAP
assert not roll.get_editor_property('flip_green_channel')
sleeve=u.load_asset(SOURCE+'/MI_Manny_01')
assert sleeve.parent.get_path_name()=='/Game/Characters/ArmsSkinSleeveCandidate/M_Manny_Sleeve_01.M_Manny_Sleeve_01'
akm_paths=['/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative',
           '/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative']
akm=next((p for p in akm_paths if u.EditorAssetLibrary.does_asset_exist(p)),None);assert akm
meshes=[]
for path in ['/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',akm]:
    mesh=u.load_asset(path);assert mesh
    mats=[m.material_interface.get_path_name() for m in mesh.materials if m.material_interface]
    assert mi.get_path_name() in mats,(path,mats)
    meshes.append({'mesh':mesh.get_path_name(),'material':mi.get_path_name()})
textures=[]
leather='/Game/Characters/ArmsLeatherCandidate/Textures/'
for path,compression,srgb,flip in [
    (leather+'T_Fab_Leather_BaseColor',u.TextureCompressionSettings.TC_DEFAULT,True,None),
    (leather+'T_Fab_Leather_Normal',u.TextureCompressionSettings.TC_NORMALMAP,False,True),
    (leather+'T_Fab_Leather_Roughness',u.TextureCompressionSettings.TC_MASKS,False,None),
    (leather+'T_Manny_LeatherRegions',u.TextureCompressionSettings.TC_MASKS,False,None),
    (leather+'T_Manny_StitchNormal',u.TextureCompressionSettings.TC_NORMALMAP,False,False),
    ('/Game/Characters/ArmsSkinSleeveCandidate/T_Manny_ForearmRegions',u.TextureCompressionSettings.TC_MASKS,False,None),
    ('/Game/Characters/ArmsGloveCuff3cmCandidate/T_Manny_Cuff3cmField',u.TextureCompressionSettings.TC_GRAYSCALE,False,None),
    ('/Game/Characters/ArmsGloveCuff3cmCandidate/T_Manny_Cuff3cmRollNormal',u.TextureCompressionSettings.TC_NORMALMAP,False,False),
]:
    tex=u.load_asset(path);assert tex,path
    assert tex.get_editor_property('compression_settings')==compression,path
    assert tex.get_editor_property('srgb')==srgb,path
    if flip is not None:assert tex.get_editor_property('flip_green_channel')==flip,path
    files=list(tex.get_editor_property('asset_import_data').extract_filenames())
    assert files and all(Path(f).is_file() and Path(f).resolve().is_relative_to(OUT.resolve()) for f in files),(path,files)
    textures.append({'asset':path,'compression':str(compression),'srgb':srgb,'flip_green':flip,'source_files':files})
report={'parent':mi.parent.get_path_name(),'cuff_start':start,'skin_scattering':scatter,
        'cuff_field':cuff_field.get_path_name(),'cuff_field_encoding':'Uncompressed linear G8 local distance, t=0.8849122968+R*0.0450000000',
        'sleeve_parent':sleeve.parent.get_path_name(),'hosts':meshes,'textures':textures}
(OUT/'verification_report.json').write_text(json.dumps(report,indent=2))
u.log('GLOVE_CUFF3CM_SAVED_VERIFY_PASS')
