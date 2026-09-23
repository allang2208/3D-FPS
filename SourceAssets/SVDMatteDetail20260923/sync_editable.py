"""Carry the refined magazine into five editable action families; no rebake."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
# The finalized mesh is already in armature-local authoring coordinates.
records=[]
for family in ['base','vertical','canted','prism','angled']:
 source=O.parent/'SVDMagazineFit20260923'/f'SVD_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source))
 original=bpy.data.objects['SM_SVD_Magazine'];rig=bpy.data.objects['SK_M4_Infima']
 with bpy.data.libraries.load(str(O/'SVD_MatteDetail_Editable.blend'),link=False) as (src,dst):
  dst.objects=['SM_SVD_Magazine']
 replacement=dst.objects[0];bpy.context.collection.objects.link(replacement)
 transform=original.matrix_world.copy();parent=original.parent;inv=original.matrix_parent_inverse.copy()
 bpy.data.objects.remove(original,do_unlink=True)
 interior=bpy.data.objects.get('SM_SVD_MagazineInterior')
 if interior:bpy.data.objects.remove(interior,do_unlink=True)
 replacement.name='SM_SVD_Magazine';replacement.parent=parent;replacement.matrix_parent_inverse=inv;replacement.matrix_world=transform
 for mod in replacement.modifiers:
  if mod.type=='ARMATURE':mod.object=rig
 # Appended dependencies can contain an unused source rig. Only the existing
 # family rig remains in the scene and drives the new magazine.
 replacement.hide_render=False;replacement.hide_set(False)
 for image in bpy.data.images:
  if image.filepath and 'SVDMatteDetail20260923' in image.filepath:image.filepath=str(O/'Textures'/Path(image.filepath).name)
 dest=O/f'SVD_{family}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
 records.append({'family':family,'source':str(source),'saved':str(dest),'animation_rebaked':False})
(O/'editable_sources.json').write_text(json.dumps(records,indent=2))
print('SVD_MATTE_EDITABLE_SAVED',len(records),flush=True)
