from pathlib import Path
P=Path(__file__).resolve().parent;V2=P.parent/'StormDriveTrimV2'
s=(V2/'import_assets.py').read_text('utf-8')
s=s.replace('StormDriveV2','StormDriveV3').replace('StormDriveTrimV2','StormDriveRuneV3')
s=s.replace('T_StormDrive_ClosedTrim_','T_StormDrive_RunePlate_').replace('M_StormDrive_ClosedSilverTrim','M_StormDrive_RunePlate_V3')
s=s.replace("materials={name:mat}","materials={name:mat}\nmaterials['M_StormDrive_ClosedSilverTrim']=u.load_asset('/Game/Weapons/CommonHammerSeats20261025/StormDriveV2/M_StormDrive_ClosedSilverTrim')\nif not materials['M_StormDrive_ClosedSilverTrim']:raise RuntimeError('Missing retained V2 crown material')")
s=s.replace('trim_shader_instructions','rune_shader_instructions').replace('STORM_DRIVE_TRIM_V2_SAVED','STORM_DRIVE_FINE_RUNE_V3_SAVED')
(P/'import_assets.py').write_text(s,encoding='utf-8')
s=(V2/'publish.py').read_text('utf-8').replace('StormDriveTrimV2','StormDriveRuneV3').replace('storm-drive-trim-v2','storm-drive-rune-v3').replace('STORM_DRIVE_TRIM_V2_PUBLISHED','STORM_DRIVE_FINE_RUNE_V3_PUBLISHED')
s=s.replace("'blender_crown_inspected':True","'blender_crown_inspected':True,'blender_fine_rune_inspected':True")
(P/'publish.py').write_text(s,encoding='utf-8')
(P/'import_background.ps1').write_text((V2/'import_background.ps1').read_text('utf-8-sig'),encoding='utf-8-sig')
