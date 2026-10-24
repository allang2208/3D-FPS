"""Save new reload assets, then publish only the six owned clip keys."""
import json,runpy,hashlib
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).parent
DEST='/Game/Characters/JasonPlayer20261003/GitHubSinglePistol20261022/Retargeted/Refined20261023'
d=json.loads((OUT/'refined-fk.json').read_text());lib=u.EditorAssetLibrary
mesh=u.load_asset(d['target']['mesh']);factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton);factory.set_editor_property('preview_skeletal_mesh',mesh)
saved={}
for role,c in d['clips'].items():
    name='J_Pistol_'+role.replace('.','_');path=DEST+'/'+name
    clip=u.load_asset(path+'.'+name) if lib.does_asset_exist(path) else None
    created=clip is None
    if clip is None:
        clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    digest=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if lib.get_metadata_tag(clip,'AuthoringSHA256')!=digest:
        ctl=clip.get_editor_property('controller');frames=c['frames'];ctl.open_bracket('Repair source FK discontinuities',False)
        try:
            ctl.set_frame_rate(u.FrameRate(30,1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
            for j,bone in enumerate(d['target']['names']):
                if created:ctl.add_bone_curve(bone,False)
                keys=[f[j] for f in frames]
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):raise RuntimeError(bone)
        finally:ctl.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        lib.set_metadata_tag(clip,'SourceAsset',c['source']);lib.set_metadata_tag(clip,'Refinement',d['provenance'])
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize '+path)
        lib.set_metadata_tag(clip,'AuthoringSHA256',digest)
        if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save '+path)
    saved['SinglePistol.Source.'+role]=clip.get_path_name()
    (OUT/'refined-saved.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
if cfg['body_mesh']!=d['target']['mesh']:raise RuntimeError('Active body changed; no route was published')
cfg['clips'].update(saved)
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
r=commit(path,before,cfg,owned_paths=[('clips',k) for k in saved],producer=__file__)
(OUT/'refined-published.json').write_text(json.dumps({'clips':saved,'config_write':r,'assets_saved':True},indent=2),encoding='utf8')
print('REFINED_RELOAD_SAVED_AND_PUBLISHED',len(saved))
