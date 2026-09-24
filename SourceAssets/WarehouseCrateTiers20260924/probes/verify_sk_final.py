import json, unreal as u
SKEL = '/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid_Skeleton.warehouse_chest_rigid_Skeleton'
DST = '/Game/Props/WarehouseCrateTiers20260924/Skeletal'
TIERS = {
 'T1_Wood':{'Gold_PBR':'Crate_WoodDark','White_Marble_PBR':'Crate_Wood','Navy_Velvet':'Crate_WoodDark','Interior_Magic_Blue':'Crate_WoodDark','Sapphire_PBR':'Crate_WoodDark','Brass_Frame':'Crate_WoodDark','Brass_Hardware':'Crate_IronDark','Ritual_Champagne':'Crate_WoodDark','Ritual_Gunmetal':'Crate_Wood','Ritual_Engraving':'Crate_IronDark','Brass_Strap':'Crate_WoodDark'},
 'T2_StoneWood':{'Gold_PBR':'Crate_Stone','White_Marble_PBR':'Crate_Wood','Navy_Velvet':'Crate_WoodDark','Interior_Magic_Blue':'Crate_WoodDark','Sapphire_PBR':'Crate_IronDark','Brass_Frame':'Crate_Stone','Brass_Hardware':'Crate_Iron','Ritual_Champagne':'Crate_Stone','Ritual_Gunmetal':'Crate_Stone','Ritual_Engraving':'Crate_IronDark','Brass_Strap':'Crate_Stone'},
 'T3_Iron':{'Gold_PBR':'Crate_IronDark','White_Marble_PBR':'Crate_Iron','Navy_Velvet':'Crate_IronDark','Interior_Magic_Blue':'Crate_IronDark','Sapphire_PBR':'Crate_IronDark','Brass_Frame':'Crate_Iron','Brass_Hardware':'Crate_IronDark','Ritual_Champagne':'Crate_Iron','Ritual_Gunmetal':'Crate_IronDark','Ritual_Engraving':'Crate_IronDark','Brass_Strap':'Crate_Iron'},
 'T4_IronGold':{'Gold_PBR':'Crate_Gold','White_Marble_PBR':'Crate_Iron','Navy_Velvet':'Crate_IronDark','Interior_Magic_Blue':'Crate_IronDark','Sapphire_PBR':'Crate_IronDark','Brass_Frame':'Crate_Gold','Brass_Hardware':'Crate_Gold','Ritual_Champagne':'Crate_Gold','Ritual_Gunmetal':'Crate_IronDark','Ritual_Engraving':'Crate_Gold','Brass_Strap':'Crate_Gold'},
 'T5_SilverGem':{'Gold_PBR':'Crate_Gold','White_Marble_PBR':'Crate_Silver','Navy_Velvet':'Crate_IronDark','Interior_Magic_Blue':'Crate_IronDark','Sapphire_PBR':'Crate_Gem','Brass_Frame':'Crate_Gold','Brass_Hardware':'Crate_Gold','Ritual_Champagne':'Crate_Gold','Ritual_Gunmetal':'Crate_Silver','Ritual_Engraving':'Crate_Gold','Brass_Strap':'Crate_Gold'},
}
oc = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidOpen')
cc = u.load_asset('/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigidClose')
res = {'clips_on_shared_skeleton': oc.get_editor_property('skeleton').get_path_name()==SKEL and cc.get_editor_property('skeleton').get_path_name()==SKEL, 'variants':{}}
allok = True
for t, exp in TIERS.items():
    m = u.load_asset('%s/SK_WarehouseCrate_%s' % (DST, t))
    skel_ok = m.get_editor_property('skeleton').get_path_name()==SKEL
    slots = {str(s.get_editor_property('material_slot_name')): (s.get_editor_property('material_interface').get_name() if s.get_editor_property('material_interface') else None) for s in m.get_editor_property('materials')}
    mism = {k: (slots.get(k), 'M_'+v) for k, v in exp.items() if slots.get(k) != 'M_'+v}
    res['variants'][t] = {'skeleton_shared': skel_ok, 'slot_count': len(slots), 'mismatches': mism}
    if not skel_ok or mism: allok = False
res['ALL_OK'] = allok
open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/probes/sk_final.json','w').write(json.dumps(res, indent=1))
