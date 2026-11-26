"""Editable complete character containing the restored face and reference hairstyle."""
import bpy,json
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'FaceOriginalRestoreR6';O=R/'Authored'
bpy.ops.wm.open_mainfile(filepath=str(N/'HairReferenceR5/Authored/ChapelNun_ReferenceHair_R5.blend'))
rig=bpy.data.objects['Kaitlin_Nun_Rig']
for file,name in [('head.json','SK_NunHead'),('trim.json','SK_Nun_CollarCross')]:
 d=json.loads((O/file).read_text());old=bpy.data.objects[name];mats=list(old.data.materials);bpy.data.objects.remove(old,do_unlink=True)
 me=bpy.data.meshes.new(name+'_Restored');me.from_pydata(d['positions'],[],[t[::-1] for t in d['triangles']]);me.update();me.uv_layers.new(name='UVMap')
 for mat in mats:me.materials.append(mat)
 for f,uv,mi in zip(me.polygons,d['uv'],d['triangle_materials']):
  f.use_smooth=True;f.material_index=mi
  for li,xy in zip(f.loop_indices,uv[::-1]):me.uv_layers.active.data[li].uv=(xy[0],1-xy[1])
 me.normals_split_custom_set([n for ns in d['normals'] for n in ns[::-1]])
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for bone in d['bones']:ob.vertex_groups.new(name=bone['name'])
 for i,weights in enumerate(d['weights']):
  for bi,w in weights:ob.vertex_groups[int(bi)].add([i],w,'REPLACE')
 mod=ob.modifiers.new('NativeFemaleBinding','ARMATURE');mod.object=rig;ob.parent=rig
bpy.context.scene['surface_revision']='FaceOriginalRestoreR6; Meshy facial geometry unchanged above the lower neck'
bpy.context.scene['hair_revision']='HairReferenceR5'
for image in bpy.data.images:
 if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ChapelNun_OriginalFace_ReferenceHair_R6.blend'))
print('RESTORED_CHARACTER_SOURCE_SAVED',flush=True)
