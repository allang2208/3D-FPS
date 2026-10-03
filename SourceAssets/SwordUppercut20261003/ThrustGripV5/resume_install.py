"""Save our already-authored Standard package after ending PIE, then continue."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
L = u.EditorAssetLibrary
target = '/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard'
asset = u.load_asset(target)
source = P/'Standard/editable_keys.json'
owner = L.get_metadata_tag(asset,'SwordUppercut.AuthorSource')
if Path(owner) not in (P.parent/'LowerRightV4/Standard/editable_keys.json',source):
    raise RuntimeError('Pending package ownership changed: '+owner)
patch = json.loads(source.read_text('utf-8'))
L.set_metadata_tag(asset,'SwordUppercut.AuthorSource',str(source))
L.set_metadata_tag(asset,'SwordUppercut.Revision','ThrustGripRisingCutV5')
L.set_metadata_tag(asset,'SwordUppercut.Provenance',
    'Current third-combo thrust articulation; original shoulder-led rising trajectory; no paid motion')
fbx = P/'Standard/A_Sword_UppercutV5_Standard.fbx'
task = u.AssetExportTask()
for key,value in dict(object=asset,filename=str(fbx),automated=True,prompt=False,replace_identical=True).items():
    task.set_editor_property(key,value)
task.options = u.FbxExportOption()
task.options.ascii = False
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Pending FBX export failed')
asset.get_editor_property('asset_import_data').update_filename_only(str(fbx))
if not L.save_loaded_asset(asset,False):
    raise RuntimeError('Pending Standard save failed')
receipt = dict(revision='ThrustGripRisingCutV5',runtime_tested=False,rendered=False,paid_motion_used=False,
    animations={target:dict(asset=asset.get_path_name(),seconds=patch['seconds'],keys=str(source),fbx=str(fbx))})
(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('UPPERCUT_V5_PENDING_STANDARD_SAVED')
runpy.run_path(str(P/'install_uppercut_v5.py'),init_globals={'INSTALL_TARGETS':[('LongGrip',False),('Standard',True)]})
