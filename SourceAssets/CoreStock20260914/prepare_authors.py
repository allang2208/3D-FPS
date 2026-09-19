"""Freeze the prior authoring tools locally and adapt them for the new stock ID."""
from pathlib import Path
P=Path(__file__).resolve().parent;OLD=P.parent/'ReferenceSkeletonStock5080_20260913/Refined'
text=(OLD/'author_variants.py').read_text(encoding='utf-8')
text=text.replace("P/'SkeletonStock_Game_Low_Editable.blend'","P/'CoreStock_Canonical_Editable.blend'")
text=text.replace("if kind=='Adapter':","if kind in {'Adapter','FrontPolymer','FrontMetal'}:")
text=text.replace("    return m\n","    if kind=='FrontPolymer':\n        bs.inputs['Base Color'].default_value=(.025,.026,.028,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.56\n    return m\n")
text=text.replace("['Metal','Polymer','Rubber','Adapter']","['Metal','Polymer','Rubber','Adapter','FrontPolymer','FrontMetal']")
text=text.replace("labels.append(2 if rubber else 1 if polymer else 0)","labels.append(4 if f.material_index==1 else 5 if f.material_index==2 else 2 if rubber else 1 if polymer else 0)")
text=text.replace("'SM_SkeletonStock'","'SM_CoreStock'").replace('SM_SkeletonStock.fbx','SM_CoreStock.fbx')
text=text.replace('SkeletonStock_Game_Editable.blend','CoreStock_Game_Editable.blend').replace('SkeletonStock_Game.glb','CoreStock_Game.glb')
text=text.replace('/Game/Weapons/ReferenceStock5080/Refined91379/','/Game/Weapons/CoreStock20260914/')
text=text.replace("'SkeletonStock_Game_Low_Editable.blend'","'CoreStock_Canonical_Editable.blend'")
# The mount ring is the prior regular geometry; smooth its side strips while
# retaining the annular caps so the front connector has no faceted shading.
text=text.replace("ring=bpy.data.objects.new('Gun_side_annular_transition',mesh);bpy.context.collection.objects.link(ring);parts.append(ring)","ring=bpy.data.objects.new('Gun_side_annular_transition',mesh);bpy.context.collection.objects.link(ring);parts.append(ring)\n    for f in ring.data.polygons:f.use_smooth=f.index<2*(len(xs)-1)*n")
(P/'author_variants.py').write_text(text,encoding='utf-8')
text=(OLD/'import_assets.py').read_text(encoding='utf-8')
text=text.replace("D='/Game/Weapons/ReferenceStock5080/Refined91379'","D='/Game/Weapons/CoreStock20260914'")
text=text.replace('T_SkeletonStock_','T_CoreStock_').replace('M_SkeletonStock_','M_CoreStock_').replace('SM_SkeletonStock','SM_CoreStock')
text=text.replace("for family in ['M4','AKM','QBZ191']:\n",'''front=material('M_CoreStock_FrontPolymer',D)
c=M.create_material_expression(front,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(.025,.026,.028,1);M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
for value,prop in [(.56,u.MaterialProperty.MP_ROUGHNESS),(0.,u.MaterialProperty.MP_METALLIC)]:
    c=M.create_material_expression(front,u.MaterialExpressionConstant);c.r=value;M.connect_material_property(c,'',prop)
M.recompile_material(front);save(front)

for family in ['M4','AKM','QBZ191']:
''')
text=text.replace("name=str(slot.material_slot_name);mesh.set_material(i,nonmetal['Polymer'] if 'Polymer' in name else nonmetal['Rubber'] if 'Rubber' in name else adapter if 'Adapter' in name else metal)","name=str(slot.material_slot_name);mesh.set_material(i,front if 'FrontPolymer' in name else adapter if 'FrontMetal' in name or 'Adapter' in name else nonmetal['Polymer'] if 'Polymer' in name else nonmetal['Rubber'] if 'Rubber' in name else metal)")
text=text.replace('Local repairs, low mesh, baked normals, per-rifle mounting; not runtime tested','Independent core_stock option with rebuilt smooth front and retained rear bakes; not runtime tested')
text=text.replace('STOCK_REFINED91379_IMPORT_COMPLETE','CORE_STOCK_IMPORT_COMPLETE')
(P/'import_assets.py').write_text(text,encoding='utf-8')
print('CORE_STOCK_AUTHORS_PREPARED')
