import unreal as u
P='/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny'
m=u.load_asset(P)
slots=list(m.get_editor_property('materials'))
for i,s in enumerate(slots):
    n=str(s.material_slot_name)
    if n.startswith('Manny_Arms_'):
        s.material_slot_name=u.Name('MI_Manny_'+n.rsplit('_',1)[-1])
        slots[i]=s          # structs are value types: write the copy back
m.set_editor_property('materials',slots)
ok=u.EditorAssetLibrary.save_loaded_asset(m, only_if_is_dirty=False)
print('RESTORED', ok, [str(s.material_slot_name) for s in m.get_editor_property('materials')][:3], flush=True)
