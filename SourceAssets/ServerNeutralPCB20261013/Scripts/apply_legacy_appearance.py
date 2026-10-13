"""Refresh only the old color/roughness textures and icon files referenced by saved items."""
from pathlib import Path
import json,hashlib,shutil
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve():raise RuntimeError('Use the isolated import host')
models=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
published=json.loads((ROOT/'Receipts/publication.json').read_text('utf-8'))
icons=json.loads((ROOT/'inventory_icons.json').read_text('utf-8'))
report=dict(stage='preparing_legacy_appearance',textures=[],icons=[],backups=[],tests_run=False,native_code_required=False)
receipt=ROOT/'Receipts/legacy-appearance.json'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def backup(path):
    saved=ROOT/'PreviousRuntimeAppearance'/path.relative_to(PROJECT)
    saved.parent.mkdir(parents=True,exist_ok=True)
    if saved.exists():raise RuntimeError('Preserve original backup: '+str(saved))
    shutil.copy2(path,saved)
    entry=dict(path=str(path),backup=str(saved),sha256=digest(path))
    report['backups'].append(entry);record();return entry
dest='/Game/Items/SearchServerEquipment20261013/Textures'
transfers=[]
for key,spec in models['assets'].items():
    for kind in ('BaseColor','ORM'):
        name='T_SE_'+key+'_'+kind
        target=PROJECT/'Content/Items/SearchServerEquipment20261013/Textures'/(name+'.uasset')
        previous=backup(target)
        task=u.AssetImportTask();task.filename=spec['textures'][kind];task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.TextureFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture=u.load_asset(dest+'/'+name)
        if not texture:raise RuntimeError('Legacy texture import failed: '+name)
        texture.srgb=kind=='BaseColor'
        texture.compression_settings=u.TextureCompressionSettings.TC_BC7 if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
        texture.lod_group=u.TextureGroup.TEXTUREGROUP_WORLD;texture.never_stream=False
        texture.max_texture_size=spec['size'];texture.address_x=u.TextureAddress.TA_CLAMP;texture.address_y=u.TextureAddress.TA_CLAMP
        u.EditorAssetLibrary.set_metadata_tag(texture,'SearchServerEquipment.Owner','SearchServerEquipment20261013')
        u.EditorAssetLibrary.set_metadata_tag(texture,'ServerNeutralPCB.AppearanceRevision','20261013')
        if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Failed to save '+name)
        saved=ROOT/'UEImportHost/Content/Items/SearchServerEquipment20261013/Textures'/(name+'.uasset')
        transfers.append((saved,target,previous))
        report['textures'].append(texture.get_path_name());record()
for icon in icons['icons']:
    relative=published['before'][icon['id']]['ue_icon']
    target=PROJECT/'Content/ColdSteelData'/relative
    previous=backup(target);transfers.append((Path(icon['file']),target,previous))
    report['icons'].append(dict(id=icon['id'],path=str(target),source=icon['file']))
for source,target,previous in transfers:
    if digest(target)!=previous['sha256']:raise RuntimeError('Preserve parallel asset change: '+str(target))
report['stage']='installing_legacy_appearance';record()
for source,target,previous in transfers:
    pending=target.with_name(target.name+'.neutral-pcb-pending')
    with source.open('rb') as incoming,pending.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    pending.replace(target)
report.update(stage='legacy_appearance_installed',updated_files=len(transfers))
record();u.log('NEUTRAL_LEGACY_APPEARANCE_INSTALLED '+str(len(transfers)))
