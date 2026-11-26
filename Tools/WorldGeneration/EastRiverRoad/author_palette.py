"""Keep PCG-selected assets available to the cooker, including the dynamically named scans."""
import unreal as u
from pathlib import Path

root='/Game/WorldGeneration/TemperateHills/EastRiverRoad'
name='PAL_EastRiverRoad'
lib=u.EditorAssetLibrary
path=root+'/'+name
factory=u.DataAssetFactory()
factory.set_editor_property('data_asset_class',u.PrimaryAssetLabel)
label=u.load_asset(path) if lib.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,root,u.PrimaryAssetLabel,factory)
paths=[root+'/SM_CommonHazel_Forest_01',root+'/SM_CommonHazel_Forest_02',root+'/MI_EastRiverRoad',
       root+'/M_EastRoad_MossPatch',root+'/M_EastRoad_SoilPatch']
for key,tier in [('xjiifd1',1),('xjijdiz',1),('relu7',3),('rioqm',3)]:
    mesh=f'{key}_tier_{tier}'
    paths.append(f'/Game/ForestPathStudy/Scans/{key}/{mesh}/StaticMeshes/{mesh}')
for key in ('slqlwtd','tdipmjh'):
    paths.append(f'/Game/ForestPathStudy/Scans/{key}/M_{key}_Decal')
assets=[u.load_asset(p) for p in paths]
if not all(assets):raise RuntimeError([p for a,p in zip(assets,paths) if not a])
rules=label.get_editor_property('rules')
rules.set_editor_property('cook_rule',u.PrimaryAssetCookRule.ALWAYS_COOK)
label.set_editor_property('rules',rules)
label.set_editor_property('explicit_assets',assets)
if not lib.save_loaded_asset(label,False):raise RuntimeError(path)

# Bake dimensions for placement so an unloaded roadside cell need not load its scans.
floor=assets[:2]+assets[5:9]
rows=[]
for mesh in floor:
    bounds=mesh.get_bounds()
    o,e=bounds.origin,bounds.box_extent
    span=max(2*e.x,2*e.y)
    rows.append('    {%.4f, %.4f, %.4f, %.4f, %.4f}, // %s' %
                (span,2*e.z,o.x,o.y,o.z-e.z,mesh.get_name()))
Path(__file__).with_name('EastRiverRoadFloorPalette.inl').write_text(
    '// Authored from the imported mesh bounds by author_palette.py\n'+'\n'.join(rows)+'\n')

