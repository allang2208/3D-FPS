"""Import 12 blade-specific masks, preserving the current PBR parents and colors."""
import json, shutil, sys
from pathlib import Path
import unreal as u

P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriRuneNatural20261027')
PROJECT=P.parents[1]
sys.path.insert(0,str(P.parent/'KukriAssetRepair20261026'))
from kukri_mesh_import import require_authoring_context
require_authoring_context()
SOURCE_ROOT='/Game/Weapons/Kukri20261020/ComponentVariants20261026/Runes'
ROOT=SOURCE_ROOT+'/Natural20261027'
entries=json.loads((P/'runes.json').read_text(encoding='utf-8'))['runes']
targets=[]
for entry in entries:
    for blade,filename in entry['blade_masks'].items():
        targets.extend((ROOT+'/Textures/'+Path(filename).stem,
                        ROOT+'/Materials/MI_KukriMark_'+blade+'_'+entry['kind']))
dirty={package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts=dirty.intersection(targets)
if conflicts:raise RuntimeError('Unsaved target packages: '+', '.join(sorted(conflicts)))
for package in targets:
    source=PROJECT/'Content'/(package.removeprefix('/Game/')+'.uasset')
    before=P/'Before'/'Assets'/source.relative_to(PROJECT/'Content')
    if source.exists() and not before.exists():
        before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,before)
tools=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
previous=json.loads((P.parent/'KukriComponentVariants20261026/rune_import_receipt.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved_assets':[],'runtime_tested':False,'pbr_parents_preserved':True,
         'rune_surfaces':{},'root_materials':previous['root_materials']}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Failed to save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    (P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
for entry in entries:
    receipt['rune_surfaces'][entry['id']]={}
    for blade,filename in entry['blade_masks'].items():
        name=Path(filename).stem
        task=u.AssetImportTask();task.filename=filename;task.destination_path=ROOT+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        tools.import_asset_tasks([task])
        texture=u.load_asset(ROOT+'/Textures/'+name)
        if not texture:raise RuntimeError('Missing texture: '+name)
        texture.set_editor_property('srgb',False)
        texture.set_editor_property('never_stream',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR)
        texture.set_editor_property('max_texture_size',2048)
        save(texture)
        source_path=SOURCE_ROOT+'/Materials/MI_KukriMark_'+blade+'_'+entry['kind']
        target_path=ROOT+'/Materials/MI_KukriMark_'+blade+'_'+entry['kind']
        instance=u.load_asset(target_path) if u.EditorAssetLibrary.does_asset_exist(target_path) else u.EditorAssetLibrary.duplicate_asset(source_path,target_path)
        if not instance:raise RuntimeError('Missing existing rune material: '+blade+' '+entry['kind'])
        edit.set_material_instance_texture_parameter_value(instance,'RuneMask',texture)
        edit.update_material_instance(instance)
        save(instance)
        slot=next(iter(previous['root_materials']['factory' if blade=='Factory' else {
            'Swift':'swift_blade','HeavyBack':'heavy_back_blade','FoldedBalanced':'folded_balanced_blade'}[blade]]['materials']))
        receipt['rune_surfaces'][entry['id']][slot]=instance.get_path_name()
receipt['complete']=True
(P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
(P.parent/'KukriComponentVariants20261026/rune_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_NATURAL_RUNES_SAVED '+str(len(receipt['saved_assets'])))
