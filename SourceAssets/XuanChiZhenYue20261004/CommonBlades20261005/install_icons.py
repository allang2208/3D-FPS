"""Publish shared framed icon keys and remove only the obsolete host PNG overrides."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
ASSET='/Game/ColdSteelData/AttachmentIcons20260913'
before=P/'Before/Icons';before.mkdir(parents=True,exist_ok=True)
retired=ROOT/'trash/xuanchi-common-blade-icons-20261005';retired.mkdir(parents=True,exist_ok=True)
receipt={'complete':False,'assets':[],'retired_overrides':[],'game_tested':False}
def record():(P/'Icons/import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
options=['extended_edge','heavy_spine','feather_edge']
for option in options:
    name='blade_1_'+option;target=D/(name+'.png')
    for old in [target,D/(name+'.uasset')]:
        if old.exists() and not (before/old.name).exists():shutil.copy2(old,before/old.name)
    shutil.copy2(P/'Icons'/(option+'_framed.png'),target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ASSET;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(ASSET+'/'+name)
    if not tex or not task.imported_object_paths:raise RuntimeError('Icon import failed: '+name)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):
        raise RuntimeError('Could not save shared icon: '+name)
    receipt['assets'].append(tex.get_path_name());record()
    # M4GunsmithLayout already falls back to this common key when no host PNG
    # exists. Retain factory/category icons and every other weapon override.
    obsolete=D/('ue_xuanchi_zhenyue_'+name+'.png')
    if obsolete.exists():
        dest=retired/obsolete.name
        digest=hashlib.sha256(obsolete.read_bytes()).hexdigest()
        if not dest.exists():shutil.copy2(obsolete,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Retirement destination already contains different icon: '+str(dest))
        obsolete.unlink()
        receipt['retired_overrides'].append({'file':str(obsolete),'retained_at':str(dest),'sha256':digest,
            'reason':'Factory-only pictogram superseded by physical common blade icon','replacement':str(target)})
        record()

deployment=P.parent/'ModelV1/Icons/deployments.json'
jobs=json.loads(deployment.read_text(encoding='utf-8'))
for job in jobs:
    for option in options:
        if Path(job['file']).stem=='ue_xuanchi_zhenyue_blade_1_'+option:
            name='blade_1_'+option
            job.update(source=str(P/'Icons'/(option+'_framed.png')),file=str(D/(name+'.png')),asset=ASSET+'/'+name)
deployment.write_text(json.dumps(jobs,indent=2)+'\n',encoding='utf-8')
(retired/'manifest.json').write_text(json.dumps(receipt['retired_overrides'],indent=2)+'\n')
receipt['complete']=True;record()
print('XUANCHI_SHARED_BLADE_ICONS_SAVED '+json.dumps(receipt))
