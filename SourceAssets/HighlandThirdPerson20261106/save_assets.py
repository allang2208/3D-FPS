"""Save the twelve fitted full-body takes; keep original actions recoverable."""
from pathlib import Path
import hashlib, json
import unreal as u

P=Path(__file__).resolve().parent
DEST='/Game/Weapons/HighlandClaymore20260922/ThirdPerson20261106'
AUTHOR='HighlandThirdPerson20261106'
lib=u.EditorAssetLibrary
manifest=json.loads((P/'authored-manifest.json').read_text())
if manifest['script_sha256']!=hashlib.sha256((P/'author.py').read_bytes()).hexdigest():raise RuntimeError('Authoring batch is incomplete')
for filename,digest in manifest['files'].items():
    if hashlib.sha256((P/filename).read_bytes()).hexdigest()!=digest:raise RuntimeError('Mixed authoring revision: '+filename)
saved={}
for kind in ['Jason','Kaitlin']:
    saved[kind]={}
    for grip in ['Standard','LongGrip']:
        saved[kind][grip]={}
        for role in ['RidgeThrust','Sweep','SweepReady']:
            source=P/f'{kind}_{grip}_{role}.json'
            data=json.loads(source.read_text())
            mesh=u.load_asset(data['mesh'])
            if not mesh:raise RuntimeError(data['mesh'])
            name=f'A_Highland3P_{kind}_{grip}_{role}'
            path=DEST+'/'+name
            exists=lib.does_asset_exist(path)
            if exists:
                seq=u.load_asset(path)
                if lib.get_metadata_tag(seq,'Highland.Author')!=AUTHOR:raise RuntimeError('Preserving '+path)
            else:
                factory=u.AnimSequenceFactory()
                factory.set_editor_property('target_skeleton',mesh.get_editor_property('skeleton'))
                seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
            if not seq:raise RuntimeError(path)
            ctl=seq.get_editor_property('controller')
            ctl.open_bracket('Fit Highland full-body paired contact',False)
            try:
                ctl.set_frame_rate(u.FrameRate(data['fps'],1),False)
                ctl.set_number_of_frames(u.FrameNumber(len(next(iter(data['tracks'].values())))-1),False)
                for bone,rows in data['tracks'].items():
                    if not exists:ctl.add_bone_curve(bone,False)
                    if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],
                            [u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:10]) for v in rows],False):
                        raise RuntimeError(path+' '+bone)
            finally:ctl.close_bracket(False)
            seq.set_preview_skeletal_mesh(mesh)
            # These local tracks were fitted on this mesh's proportions. Using
            # the shared skeleton's default retarget source rescales Kaitlin's
            # arms again and separates the support palm from the hilt.
            seq.set_retarget_source_asset(mesh)
            seq.update_retarget_source_asset_data()
            seq.set_editor_property('enable_root_motion',False)
            seq.set_editor_property('force_root_lock',True)
            if not exists:
                u.AnimationLibrary.add_animation_notify_track(seq,'HighlandTiming')
                contact,release=(42/120,48/120) if role=='RidgeThrust' else (.30,.47)
                for marker,time in [('NativeSwordGrip',0),('HighlandSupportedGrip',0),('Contact',contact),('Release',release)]:
                    u.AnimationLibrary.add_animation_sync_marker(seq,marker,time,'HighlandTiming')
            lib.set_metadata_tag(seq,'Highland.Author',AUTHOR)
            lib.set_metadata_tag(seq,'Highland.SourceSHA256',hashlib.sha256(source.read_bytes()).hexdigest())
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):raise RuntimeError('Finalizing '+path)
            if not lib.save_loaded_asset(seq,False):raise RuntimeError('Saving '+path)
            saved[kind][grip][role]=seq.get_path_name()
            (P/'saved-assets.json').write_text(json.dumps(saved,indent=2))
            print('HIGHLAND_BODY_SAVED',seq.get_path_name(),seq.get_play_length())
print('HIGHLAND_BODY_ASSETS_COMPLETE')
