"""Promote existing framed artwork to shared keys, without generating per-weapon copies."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
UE='/Game/ColdSteelData/AttachmentIcons20260913'
before=P/'Before/Icons';before.mkdir(parents=True,exist_ok=True)
retired=ROOT/'trash/xuanchi-common-guard-icons-20261005';retired.mkdir(parents=True,exist_ok=True)
keys=['guard_'+s for s in ['bastion_guard','riposte_guard','light_guard']]
keys+=['blade_2_'+s for s in ['resonance_rune','erosion_rune','conduction_rune','auspicious_cloud_rune','mountain_rune']]
receipt={'complete':False,'icons':[],'retired_overrides':[],'new_images_generated':False,'game_tested':False}
def record():(P/'icon_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Exit PIE before icon import; no icon assets changed')
for key in keys:
    source=D/('ue_tang_dao_'+key+'.png');target=D/(key+'.png')
    for old in [target,target.with_suffix('.uasset')]:
        if old.exists() and not (before/old.name).exists():shutil.copy2(old,before/old.name)
    shutil.copy2(source,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=UE;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(UE+'/'+key)
    if not tex or not task.imported_object_paths:raise RuntimeError('Shared icon import failed: '+key)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Shared icon save failed: '+key)
    receipt['icons'].append({'source':str(source),'target':str(target),'asset':tex.get_path_name(),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'role':'Existing framed representative artwork for the shared modification ID'})
    record()
    obsolete=D/('ue_xuanchi_zhenyue_'+key+'.png')
    if key.startswith('guard_') and obsolete.exists():
        dest=retired/obsolete.name;digest=hashlib.sha256(obsolete.read_bytes()).hexdigest()
        if not dest.exists():shutil.copy2(obsolete,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:raise RuntimeError('Retirement destination differs: '+str(dest))
        obsolete.unlink()
        receipt['retired_overrides'].append({'file':str(obsolete),'retained_at':str(dest),'sha256':digest,'replacement':str(target)})
        record()
deployment=P.parent/'ModelV1/Icons/deployments.json'
jobs=json.loads(deployment.read_text(encoding='utf-8'))
for job in jobs:
    name=Path(job['file']).stem
    key=name.removeprefix('ue_xuanchi_zhenyue_')
    if key in keys:job.update(source=str(D/(key+'.png')),file=str(D/(key+'.png')),asset=UE+'/'+key)
deployment.write_text(json.dumps(jobs,indent=2)+'\n',encoding='utf-8')
(retired/'manifest.json').write_text(json.dumps(receipt['retired_overrides'],indent=2)+'\n')
receipt['complete']=True;record()
print('XUANCHI_SHARED_RUNE_GUARD_ICONS_SAVED',len(receipt['icons']),flush=True)
