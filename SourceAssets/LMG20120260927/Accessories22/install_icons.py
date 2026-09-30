"""Save authoring output to the existing gunsmith icon pipeline."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[2];A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
report={'saved':[],'shared':{},'runtime_tested':False}
for job in json.loads((O/'icons.json').read_text()):
    key=job['key'];dest=P/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
    if dest.exists():
        backup=O/'Before'/dest.relative_to(P);backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(dest,backup)
    shutil.copy2(job['file'],dest)
    t=u.AssetImportTask();t.filename=str(dest);t.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+key)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);tex.set_editor_property('srgb',True)
    E.set_metadata_tag(tex,'ModificationIconPalette','neutral-grayscale-20260927')
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Icon save '+key)
    report['saved'].append(tex.get_path_name())
# Universal silhouettes are the same accepted shared bodies; host adapters are
# recorded in geometry.json. Factory stock/rear-grip art is 201-specific above.
d=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf8'));w=next(w for w in d['weapons'] if w['id']=='ue_lmg201')
for slot in ['underbarrel','stock','reargrip','tactical','optic']:
    for option in w['options'][slot]:
        key=slot+'_'+str(option['id']);path=P/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
        if path.exists():report['shared'][key]=str(path)
(O/'icon_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('LMG20122_ICONS_SAVED',len(report['saved']),flush=True)
