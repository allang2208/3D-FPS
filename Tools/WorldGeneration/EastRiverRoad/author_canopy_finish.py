"""Bind the accepted reference wind slots to the two harvestable hornbeams."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

root='/Game/WorldGeneration/TemperateHills/EastRiverRoad/CanopyR2'
lib=u.EditorAssetLibrary
ed=u.MaterialEditingLibrary
slots=json.loads(Path(os.environ['EAST_ROAD_WINDSLOTS']).read_text(encoding='utf-8-sig'))
copies={}
def save(obj):
    if not lib.save_loaded_asset(obj,False):raise RuntimeError(obj.get_path_name())
def compatible(src):
    path=src.get_path_name()
    if path in copies:return copies[path]
    dest=root+'/Wind/'+src.get_name()+'_'+hashlib.sha1(path.encode()).hexdigest()[:6]
    obj=u.load_asset(dest) if lib.does_asset_exist(dest) else lib.duplicate_asset(path,dest)
    if isinstance(obj,u.MaterialInstanceConstant):
        ed.set_material_instance_parent(obj,compatible(src.get_editor_property('parent')))
        ed.update_material_instance(obj)
    else:
        ed.set_material_usage(obj,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        ed.recompile_material(obj)
    save(obj)
    copies[path]=obj
    return obj
trees=[]
for form in ('04','05'):
    tree=u.load_asset(root+'/SK_RoadHornbeam_'+form)
    materials=list(tree.get_editor_property('materials'))
    paths=slots['SM_EuropeanHornbeam_Forest_'+form]
    if len(materials)!=len(paths):raise RuntimeError(f'{form}: changed source material slots')
    for material,path in zip(materials,paths):
        material.set_editor_property('material_interface',compatible(u.load_asset(path)))
    tree.set_editor_property('materials',materials)
    settings=tree.get_editor_property('nanite_settings')
    settings.set_editor_property('enabled',True)
    tree.set_editor_property('nanite_settings',settings)
    save(tree)
    trees.append(tree)
labelpath=root+'/PAL_RoadHornbeam'
factory=u.DataAssetFactory()
factory.set_editor_property('data_asset_class',u.PrimaryAssetLabel)
label=u.load_asset(labelpath) if lib.does_asset_exist(labelpath) else u.AssetToolsHelpers.get_asset_tools().create_asset('PAL_RoadHornbeam',root,u.PrimaryAssetLabel,factory)
rules=label.get_editor_property('rules')
rules.set_editor_property('cook_rule',u.PrimaryAssetCookRule.ALWAYS_COOK)
label.set_editor_property('rules',rules)
weeds=[u.load_asset('/Game/ForestPathStudy/Scans/rbcuh/rbcuh_tier_1/StaticMeshes/SM_rbcuh_VarA'),
       u.load_asset('/Game/ForestPathStudy/Scans/rbpir/rbpiR_tier_1/StaticMeshes/SM_rbpiR_VarB')]
if not all(weeds):raise RuntimeError('Missing reference understory')
label.set_editor_property('explicit_assets',trees+weeds)
save(label)
