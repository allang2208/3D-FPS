import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(R.parents[2]/'assets/models/wolf_quaternius.gltf'))
a=next(o for o in s.objects if o.type=='ARMATURE')
m=next(o for o in s.objects if o.type=='MESH')
for tr in a.animation_data.nla_tracks:tr.mute=True
a.animation_data.action=None
from mathutils import Matrix
for b in a.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
report={'armature':a.name,'mesh':m.name,'mesh_transform':[list(row) for row in m.matrix_world],
 'vertices':len(m.data.vertices),'polygons':len(m.data.polygons),'uv_layers':len(m.data.uv_layers),
 'local_bounds':[[min(v.co[i] for v in m.data.vertices),max(v.co[i] for v in m.data.vertices)] for i in range(3)],
 'materials':[x.name for x in m.data.materials],
 'bones':[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local)} for b in a.data.bones],
 'clips':{x.name:(x.frame_range[1]-x.frame_range[0])/30 for x in bpy.data.actions}}
(R/'source-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'source-wolf.blend'))
print('WOLF_SOURCE_REPORT',json.dumps({k:v for k,v in report.items() if k!='bones'}))
