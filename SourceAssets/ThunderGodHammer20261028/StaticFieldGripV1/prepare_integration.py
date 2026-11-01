"""Adapt the existing background UE importer for this new, separately owned revision."""
from pathlib import Path
P=Path(__file__).resolve().parent
source=P.parent/'JiLeiInlaidLightningV14/Integration20261031'
s=(source/'import_assets.py').read_text(encoding='utf-8')
s=s.replace('Save the approved JiLei V14 mesh, PBR materials, and production icon in UE.','Save Static Field grip, PBR materials, and actual-model production icon in UE.')
s=s.replace('S = P.parent','S = P').replace('R = P.parents[3]','R = P.parents[2]')
s=s.replace('/JiLeiInlaidLightningV14','/StaticFieldGripV1').replace('T_JiLei14_','T_StaticField_')
s=s.replace('ue_thunder_god_hammer_head_mount_ji_lei_seat','ue_thunder_god_hammer_grip_static_field')
s=s.replace("id='ji_lei_seat'","id='static_field_grip'").replace('ji_lei_seat_framed.png','static_field_grip_framed.png')
s=s.replace('jilei-v14-pending','static-field-pending').replace('JILEI_V14_ASSETS_SAVED','STATIC_FIELD_ASSETS_SAVED')
s=s.replace("generator='built-in imagegen',prompt=str(P/'icon_prompt.txt')","generator='Blender render of current model; imagegen unavailable',source_scene=str(P/'StaticField_Icon.blend')")
s=s.replace('# Replace only the JiLei production icon, with a recoverable copy of its old files.','# Install this exclusive grip icon, preserving any existing owned revision.')
(P/'import_assets.py').write_text(s,encoding='utf-8')
s=(source/'install.ps1').read_text(encoding='utf-8').replace('JiLei import commandlet failed','Static Field import commandlet failed')
(P/'install.ps1').write_text(s,encoding='utf-8')
print('STATIC_FIELD_IMPORT_SCRIPTS_READY')
