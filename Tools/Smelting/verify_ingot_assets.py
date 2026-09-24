import unreal
EAL=unreal.EditorAssetLibrary
MEL=unreal.MaterialEditingLibrary
paths=['/Game/Items/Smelting/M_Ingot','/Game/Items/Smelting/M_Ore_Tinted','/Game/Items/Smelting/Ingot/SM_Ingot',
 '/Game/Items/Smelting/Ingot/MI_ironIngot','/Game/Items/Smelting/Ingot/MI_copperIngot',
 '/Game/Items/Smelting/Ingot/MI_silverIngot','/Game/Items/Smelting/Ingot/MI_goldIngot',
 '/Game/Items/Smelting/Ore/MI_iron_ore','/Game/Items/Smelting/Ore/MI_copper_ore',
 '/Game/Items/Smelting/Ore/MI_silver_ore','/Game/Items/Smelting/Ore/MI_gold_ore']
ok=[]
for p in paths:
    a=EAL.load_asset(p) if EAL.does_asset_exist(p) else None
    if a is None: ok.append((p,'MISSING')); continue
    if isinstance(a,unreal.MaterialInterface):
        a.get_material_render_data() if hasattr(a,'get_material_render_data') else None
        unreal.MaterialEditingLibrary.update_material(a) if hasattr(MEL,'update_material') else None
    ok.append((p,'LOADED '+a.get_class().get_name()))
for p,s in ok: print('VERIFY',p,s)
print('VERIFY_DONE')
