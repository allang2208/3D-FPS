"""Prepare the stock-only mesh reimport and exact exported material bindings."""
from pathlib import Path
O=Path(__file__).parent
text=(O.parent/'Refinement03/import_surfaces.py').read_text(encoding='utf-8')
text=text.replace("P='/Game/Weapons/A762/Refinement03'","P='/Game/Weapons/A762/Refinement04'")
text=text.replace("['SK_A762_Manny','SM_A762_RearSight']","['SK_A762_Manny']")
text=text.replace("[('SK_A762_Manny',True),('SM_A762_RearSight',False)]","[('SK_A762_Manny',True)]")
text=text.replace("opt.import_materials=False; opt.import_textures=False; opt.create_physics_asset=False", "opt.import_materials=False; opt.import_textures=False; opt.create_physics_asset=False\n        opt.set_editor_property('reset_to_fbx_on_material_conflict',True)")
text=text.replace("slotname=str(slot.material_slot_name); binding=materials.get(slotname) or bindings.get(slotname)","slotname=str(slot.material_slot_name); binding=materials.get(slotname)\n            if not binding and slotname in auth['inherited_material_paths']: binding=u.load_asset(auth['inherited_material_paths'][slotname])\n            if not binding: binding=bindings.get(slotname)")
text=text.replace('A762_REFINEMENT03_IMPORTED_AND_SAVED','A762_STOCKJOINT04_IMPORTED_AND_SAVED')
(O/'import_stock.py').write_text(text,encoding='utf-8')
print('Prepared stock mesh import')
