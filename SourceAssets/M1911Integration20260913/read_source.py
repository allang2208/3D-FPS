import bpy,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M1911Integration20260913')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/VaultCache/FabLibrary/M1911__FREE_-77247d26/fbx/source_extracted/Rigged_M1911.fbx')
info={'objects':[],'images':[{'name':i.name,'path':i.filepath,'packed':bool(i.packed_file)} for i in bpy.data.images],'actions':[{'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions]}
for ob in bpy.context.scene.objects:
 d={'name':ob.name,'type':ob.type,'world':[list(x) for x in ob.matrix_world],'bounds':[list(ob.matrix_world@__import__('mathutils').Vector(v)) for v in ob.bound_box]}
 if ob.type=='ARMATURE':d['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in ob.data.bones]
 if ob.type=='MESH':d.update(verts=len(ob.data.vertices),groups=[g.name for g in ob.vertex_groups],materials=[m.name for m in ob.data.materials])
 info['objects'].append(d)
(O/'model_source.json').write_text(json.dumps(info,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Source.blend'))
print(json.dumps(info))
