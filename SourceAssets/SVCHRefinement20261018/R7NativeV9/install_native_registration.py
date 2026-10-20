"""Save the native-joint registration in the existing SVCH profile; native V9 skin stays untouched."""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();before=O/'Before';before.mkdir(exist_ok=True)
path='/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip'
disk=P/'Content/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip.uasset'
if (before/disk.name).exists():raise RuntimeError('Preserve the prior install receipt and backup; use a new attempt')
old_hash=hashlib.sha256(disk.read_bytes()).hexdigest();shutil.copy2(disk,before/disk.name)
profile=u.load_asset(path);source=O/'shared_profile_native_v9.json'
if not profile.set_shared_clips_from_json(source.read_text()):raise RuntimeError('Invalid native registration')
u.EditorAssetLibrary.set_metadata_tag(profile,'SVCHRightArm','Approved V9 source joints; rigid registration; V9 leaf twist 100/50; no local hand/finger edits')
if not u.EditorAssetLibrary.save_loaded_asset(profile,False):raise RuntimeError('Profile save failed')
cfg=P/'Content/ColdSteelData/modular_outfits.json';data=json.loads(cfg.read_text(encoding='utf-8-sig'))
mesh='/Game/Weapons/SVCH/Refined20261018/R5/SK_SVCH_Refined_R5.SK_SVCH_Refined_R5';entry=data['profiles'][mesh]
(before/'outfit_profile.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2))
native='/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.SK_SVD_BareArmsV7'
if not u.load_asset(native):raise RuntimeError('Missing installed native V9 skin')
entry.update(native_bare_arms=False,native_bare_skin=native,base=native,hide_source_materials=[9,10],shirt_covers=[0,1],glove_covers=[2])
cfg.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'saved':True,'profile':profile.get_path_name(),'previous_profile_sha256':old_hash,'profile_sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'native_v9_skin':native,'source_animation_assets_modified':False,'native_v9_mesh_modified':False}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_NATIVE_REGISTRATION_SAVED',json.dumps(receipt),flush=True)
