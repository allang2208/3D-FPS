import unreal as u
paths = ['/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/M_Ritual_Metal',
 '/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/MI_Ritual_Frame',
 '/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/MI_Ritual_Champagne',
 '/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/M_Ritual_Sapphire',
 '/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble/M_Chest_Ziarat',
 '/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble/MI_Chest_Ziarat_4K',
 '/Game/ColdSteelUI/Warehouse20260909/DirtyMetal/M_Chest_DirtyMetal',
 '/Game/ColdSteelUI/Warehouse20260909/DirtyMetal/MI_Chest_DirtyMetal_Brass']
for p in paths:
    m = (u.load_asset(p) or u.EditorAssetLibrary.load_asset(p))
    if m is None:
        print('MISSING', p, flush=True); continue
    print('TS', p.split('/')[-1], m.get_editor_property('two_sided'), flush=True)

