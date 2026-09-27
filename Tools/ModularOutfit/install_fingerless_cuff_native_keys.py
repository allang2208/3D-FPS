"""Replace provisional IK delta baking with exact native-key fixed-hand solutions."""
import json,hashlib,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
for folder in ('CuffArmClearance','CuffShoulderClearance'):
    if os.environ.get('FINGERLESS_IK_FOLDER') and folder!=os.environ['FINGERLESS_IK_FOLDER']:continue
    root=R/folder;receipt_path=root/'installed.json';receipt=json.loads(receipt_path.read_text())
    for f in sorted((root/'NativeKeys').glob('*.json')):
        d=json.loads(f.read_text());path=d['asset'];disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=receipt[path]['after_sha256']:raise RuntimeError('Concurrent animation change '+path)
        asset=u.load_asset(path);controller=asset.get_editor_property('controller');controller.open_bracket('Exact fixed-hand cuff clearance at native keys',False)
        try:
            for bn,keys in d['tracks'].items():
                if not controller.set_bone_track_keys(bn,[u.Vector(*v['p']) for v in keys],[u.Quat(*v['q']) for v in keys],[u.Vector(*v['s']) for v in keys],False):raise RuntimeError('Cannot write '+bn)
        finally:controller.close_bracket(False)
        asset.modify()
        if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or u.EditorAssetLibrary.save_loaded_asset(asset,False)):raise RuntimeError('Cannot save '+path)
        receipt[path]['after_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();receipt[path]['exact_native_key_ik']=True;receipt_path.write_text(json.dumps(receipt,indent=2));print('NATIVE_CUFF_KEYS_SAVED',path,flush=True)
exec((P/'Tools/ModularOutfit/read_final_fingerless_clearance.py').read_text())
