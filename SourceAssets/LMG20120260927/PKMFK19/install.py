"""Save only two 201 belt reloads, with exact rollback packages and provenance."""
import json, hashlib, shutil
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[2];E=u.EditorAssetLibrary
d=json.loads((O/'keys.json').read_text())
def package(asset):return P/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(asset):return hashlib.sha256(package(asset).read_bytes()).hexdigest()
loaded=[]
for name,spec in d['clips'].items():
    if sha(spec['asset'])!=spec['expected_source_sha256']:raise RuntimeError('Target changed since authoring '+name)
    if sha(spec['donor'])!=spec['donor_sha256']:raise RuntimeError('PKM donor changed since authoring')
    clip=u.load_asset(spec['asset'])
    if not clip:raise RuntimeError('Missing runtime clip '+name)
    backup=O/'Before'/package(spec['asset']).relative_to(P)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(package(spec['asset']),backup)
    loaded.append((name,spec,clip))
receipt={'revision':'PKMFK19','runtime_tested':False,'assets':{},'ik_used':False,'mesh_changed':False}
for name,spec,clip in loaded:
    model=clip.get_editor_property('data_model_interface');c=clip.get_editor_property('controller')
    c.open_bracket('201: preserve complete native PKM FK; adapt weapon placement',False)
    try:
        for n,keys in spec['tracks'].items():
            if not model.is_valid_bone_track_name(n):raise RuntimeError('Missing FK track '+n)
            if not c.set_bone_track_keys(n,[u.Vector(*v['p']) for v in keys],
                [u.Quat(*v['q']) for v in keys],[u.Vector(*v['s']) for v in keys],False):raise RuntimeError('Failed track '+n)
    finally:c.close_bracket(False)
    for tag in ('201ReloadRevision','201UpperArmRevision','201ArmBindingRevision'):
        E.set_metadata_tag(clip,tag,'PKMFK19: native PKM complete FK arms; contact matched by weapon/right-arm translation; no IK/twist rewriting')
    E.set_metadata_tag(clip,'NativeAnimationDonor',spec['donor'])
    E.set_metadata_tag(clip,'NativeAnimationDonorSHA256',spec['donor_sha256'])
    E.set_metadata_tag(clip,'201AuthoringSource',str(O/'LMG201_PKMFK19_Editable.blend'))
    u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
    if not E.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed '+name)
    receipt['assets'][name]={'asset':spec['asset'],'saved':True,'sha256':sha(spec['asset']),
        'before_sha256':spec['expected_source_sha256'],'donor':spec['donor'],'donor_sha256':spec['donor_sha256'],
        'seconds':clip.get_play_length(),'keys':spec['keys'],'tracks':list(spec['tracks'])}
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('PKMFK19_SAVED '+name,flush=True)
print('PKMFK19_COMPLETE',flush=True)
