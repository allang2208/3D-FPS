"""Save new meteor/dragon fuel variants through the current editor batch gate.

Copies keep the running PIE's original systems and R6 materials intact.
No gameplay, preview or acceptance run is performed.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/AdvancedMagicRange20261019'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if hasattr(u,'DragonBreathAuthorLibrary'):
    u.RainAssetEditor=u.DragonBreathAuthorLibrary
from meteor_ground_sources import build_sources as meteor_sources
from dragon_fluid_source import build_sources as dragon_sources

TARGETS=[
    ('/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1/NS_MeteorGroundVolume',
     '/Game/Skills/FireMagic20260921/MeteorFilledVolumeV2/NS_MeteorGroundVolume',meteor_sources),
    ('/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume',
     '/Game/Skills/DragonBreath20261013/Range2x20261019/NS_DragonVolume',dragon_sources),
]


def run():
    eal=u.EditorAssetLibrary
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(dst for src,dst,builder in TARGETS):
        raise RuntimeError('Preserve unsaved target edits')
    receipt={'complete':False,'saved_assets':[],'gameplay_tested':False,'rendered':False}
    OUT.mkdir(parents=True,exist_ok=True)
    for source,destination,builder in TARGETS:
        folder,name=destination.rsplit('/',1)
        eal.make_directory(folder)
        system=u.load_asset(destination) if eal.does_asset_exist(destination) else u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,folder,u.load_asset(source))
        if not system:raise RuntimeError('Cannot create '+destination)
        builder(system)
        eal.set_metadata_tag(system,'AdvancedMagic.Revision','FilledMeteor_Range2x_20261019')
        eal.set_metadata_tag(system,'AdvancedMagic.Source',source)
        if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('Niagara compilation failed: '+destination)
        if not eal.save_loaded_asset(system,False):raise RuntimeError('Save failed: '+destination)
        receipt['saved_assets'].append(system.get_path_name())
        (OUT/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print('ADVANCED_MAGIC_SAVED '+system.get_path_name())
    receipt['complete']=True
    receipt['meteor']={'source_rate_max':460,'source_lifetime_max':.85,'core_fuel_fraction':.2,
                       'grid_axis_local':128,'grid_axis_remote':96,'visible_sprites':0}
    receipt['dragon']={'source_rate':360,'travel_follows_range':True,'grid_axis_max':160}
    (OUT/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':run()
