from pathlib import Path
import json,shutil,unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
DEST=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';ASSET='/Game/ColdSteelData/AttachmentIcons20260913'
sources={**{'blade_material_'+i:P/'Icons'/(i+'.png') for i in ('folded_steel','dark_iron','mithril')},
 'category_blade_material':DEST/'ue_rune_sword_category_blade_1.png',
 'ue_rune_sword_blade_material_false':DEST/'ue_rune_sword_blade_1_false.png'}
saved=[]
for name,source in sources.items():
    destination=DEST/(name+'.png')
    if destination.exists():
        backup=P/'BeforeIcons'/destination.name;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(destination,backup)
    shutil.copy2(source,destination)
    task=u.AssetImportTask();task.filename=str(destination);task.destination_path=ASSET;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(ASSET+'/'+name)
    if not tex:raise RuntimeError('Icon import failed '+name)
    for key,value in [('lod_group',u.TextureGroup.TEXTUREGROUP_UI),('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON),
                      ('srgb',True),('never_stream',True),('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)]:tex.set_editor_property(key,value)
    if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed '+name)
    saved.append({'asset':tex.get_path_name(),'png':str(destination),'source':str(source)})
(P/'icon-receipt.json').write_text(json.dumps({'saved':saved,'mode':'built-in imagegen; existing factory image reused'},indent=2)+'\n',encoding='utf8')
print('BLADE_MATERIAL_ICONS_SAVED',len(saved))
