"""Publish HK416 weather/outfit references and resume after geometry saves."""
import unreal as u,json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/HK416/Reworked20260930'
report=json.loads((O/'import_receipt.json').read_text());E=u.EditorAssetLibrary
wetmap={path:u.load_asset(path) for name,path in report['materials'].items() if 'Glass' not in name and 'Reticle' not in name}
path=ROOT+'/DA_HK416_WetMaterials';library=u.load_asset(path)
if not library:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    library=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_HK416_WetMaterials',ROOT,u.WeatherPresentationAssets,factory)
current={str(k):v.get_path_name() for k,v in library.get_editor_property('wet_materials').items()}
# Preserve published accessory pairs and the unified instances' self mappings.
wetmap={**dict(library.get_editor_property('wet_materials')),**wetmap}
expected={k:v.get_path_name() for k,v in wetmap.items()}
# UV-only reimports do not change the saved material library. Keep the existing
# package instead of attempting an unnecessary rewrite of a loaded data asset.
if current!=expected:
    library.set_editor_property('wet_materials',wetmap)
    if not E.save_loaded_asset(library,only_if_is_dirty=False):raise RuntimeError('Cannot save HK416 wet library')
if library.get_path_name() not in report['saved']:report['saved'].append(library.get_path_name())
file=P/'Content/ColdSteelData/modular_outfits.json';original=file.read_text(encoding='utf-8-sig')
start=original.index('{',original.index('"profiles"'));profiles,length=json.JSONDecoder().raw_decode(original[start:])
profile=copy.deepcopy(profiles.get(report['mesh']) or next(v for v in profiles.values() if v.get('rig_profile')=='M4'))
profile.update(native_bare_arms=True,hide_source_materials=report['arm_materials']);profile.pop('original_gloved_source',None)
if profiles.get(report['mesh'])!=profile:
    profiles[report['mesh']]=profile
    if file.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Outfit catalog changed during publication')
    file.write_text(original[:start]+json.dumps(profiles,ensure_ascii=False,indent=2)+original[start+length:],encoding='utf-8')
report['status']='hk416_assets_imported_and_saved';(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
print('HK416_ASSETS_IMPORTED_AND_SAVED')
