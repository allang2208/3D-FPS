"""Save the left-hand side-feed sequences, matching grip layers and framed icon."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
report_path=r/'install_receipt.json';report=json.loads(report_path.read_text()) if report_path.exists() else dict(saved={},animations={},profiles={},icons=[],runtime_tested=False,editor_started=False)
report['complete']=False
before=json.loads((r/'before.json').read_text());inputs=json.loads((r/'inputs.json').read_text())
def disk(path):return p/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def record():report_path.write_text(json.dumps(report,indent=2))
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
    report['saved'][a.get_path_name().split('.')[0]]=hashlib.sha256(disk(a.get_path_name()).read_bytes()).hexdigest();record()
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; assets retained')
dirty={q.get_name() for q in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(before):raise RuntimeError('Unsaved target packages retained')
for path,sha in before.items():
    f=disk(path);now=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    if now!=report['saved'].get(path,sha):raise RuntimeError('Concurrent target change '+path)
for path,sha in inputs['hashes'].items():
    if path.split('.')[0] not in report['saved'] and hashlib.sha256(disk(path).read_bytes()).hexdigest()!=sha:raise RuntimeError('Author source changed '+path)
native=load('/Game/Weapons/M249/SK_M249_V7')
for f in sorted((r/'Motion').glob('*.json.gz')):
    data=json.loads(gzip.decompress(f.read_bytes()));clip=load(data['asset']);ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 left-hand extraction and side insertion',False)
    try:
        ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False);ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone,rows in data['tracks'].items():
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Track '+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation build '+clip.get_name())
    save(clip);report['animations'][f.name]=data['asset'];record();print('M249_LEFT_HAND_ACTION_SAVED',f.name,flush=True)
profiles={family:('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family) for family in ('base','vertical','canted','prism','angled')}
for family,path in profiles.items():
    profile=load(path);incoming=json.loads(gzip.decompress((r/(family+'.json.gz')).read_bytes()))['clips'];keys={c['base'].split('.')[0] for c in incoming};rows=[];kept=[]
    for c in profile.get_editor_property('clips'):
        base=c.get_editor_property('base');other=c.get_editor_property('retained')
        if base.get_path_name().split('.')[0] in keys:continue
        if other:kept.append((base,other));continue
        rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    if not profile.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
    for base,other in kept:profile.keep_clip(base,other)
    save(profile);report['profiles'][family]=path;record()
key='ue_m249_magazine_m249_side_mag_45';source=r/'Icons'/(key+'.png')
for suffix in ('FramedFirearms/',''):
    folder='ColdSteelData/AttachmentIcons20260913/'+suffix;live=p/'Content'/folder/source.name;live.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(source,live)
    t=u.AssetImportTask();t.filename=str(live);t.destination_path='/Game/'+folder.rstrip('/');t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
    a=load('/Game/'+folder+key);a.srgb=True;a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.never_stream=True;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(a);report['icons'].append(a.get_path_name());record()
report['complete']=True;record();print('M249_LEFT_RELOAD_AND_FRAMED_ICON_SAVED',len(report['saved']),flush=True)
