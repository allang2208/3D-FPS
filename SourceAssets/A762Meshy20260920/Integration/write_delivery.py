import argparse,json
from datetime import datetime
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--compile-result',choices=['pending','succeeded','failed'],required=True)
p.add_argument('--build-method',default='editor Live Coding through project mutex bridge')
p.add_argument('--build-receipt',default='livecoding_compile_01.txt')
args=p.parse_args();O=Path(__file__).parent
author=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
geometry=json.loads((O/'geometry_import.json').read_text(encoding='utf-8'))
motion=json.loads((O/'motion_import.json').read_text(encoding='utf-8'))
delivery={
 'asset':'A762','definition':'ue_a762','updated_at':datetime.now().astimezone().isoformat(),
 'stage':'integrated_not_playtested' if args.compile_result=='succeeded' else 'imported_build_'+args.compile_result,
 'project':'D:/FPS3D/FPSGAME',
 'ue_asset_root':'/Game/Weapons/A762/Integrated20260920',
 'mesh':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny.SK_A762_Manny',
 'source_candidate':'../A762_Meshy_Candidate01_Editable.blend',
 'editable_source':'A762_Rigged_Editable.blend','export_directory':'Exports',
 'working_length_m':author['working_length_m'],'parts':author['parts'],
 'animations':motion,'animation_sources':author['animations'],
 'geometry_import':geometry,
 'gameplay':{'catalog':True,'equipment':True,'warehouse_once_per_profile':True,'save_path':'existing inventory and gunsmith profile',
             'pickup_drop':True,'dynamic_model_icon':True,'gunsmith_preview':True,'ammo':'ammo_762','capacity':30,
             'damage':35,'fire_interval_seconds':.1,'reload_seconds':3.333333,'reload_empty_seconds':4.291667,
             'attachment_geometry':['optic','muzzle'],'stock_magazine_grip':'factory'},
 'audio':{'mode':'direct reuse of current AKM assets','current_cues':'/Game/Weapons/AKM/VideoAudio20260921/S_AKM_*',
          'other_cues':'/Game/Weapons/AKM/Audio','suppressed_fire':'/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed'},
 'build':{'method':args.build_method,'result':args.compile_result,'receipt':args.build_receipt,
          'live_coding_attempt':'Unreal Editor exited with an unhandled exception during patch linking; native build used for delivery.'},
 'tested':False,'pie_started_for_acceptance':False,'acceptance_rendered':False,
 'acceptance':'User will test appearance, finger contact, motion, aim, attachments and gameplay.',
 'receipts':{'geometry':'ue_geometry_output_01.txt','motion':'ue_motion_output_03.txt'},
 'integration_sources':[
 'Source/FPSGAME/Weapons/A762WeaponAssets.h','Source/FPSGAME/FPSGAMECharacter.cpp',
 'Source/FPSGAME/FPSGAMECharacterProfile.cpp','Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',
 'Source/FPSGAME/Weapons/M4DrumVisual.cpp','Source/FPSGAME/Weapons/M4FoldingSights.cpp',
 'Source/FPSGAME/Weapons/M4GunsmithVisual.cpp','Source/FPSGAME/Weapons/M4MuzzleVisual.cpp',
 'Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp','Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp',
 'Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp','Source/FPSGAME/UI/ColdSteelPickupStudio.cpp',
 'Source/FPSGAME/UI/M4StandalonePreview.cpp','Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',
 'Content/ColdSteelData/items.json','Content/ColdSteelData/gunsmith.json','Config/DefaultGame.ini']}
(O/'DELIVERY.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
root=json.loads((O.parent/'DELIVERY.json').read_text(encoding='utf-8'))
root.update(user_selected=True,mechanical_parts_split=True,rigged=True,imported_into_ue=True,
            gameplay_integrated=args.compile_result=='succeeded',tested=False,
            integration_delivery='Integration/DELIVERY.json',integration_editable_source='Integration/A762_Rigged_Editable.blend',
            build_result=args.compile_result,
            visual_acceptance='User testing pending; no PIE, acceptance screenshot or local acceptance render performed')
(O.parent/'DELIVERY.json').write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Saved A762 integration delivery: '+delivery['stage'])
