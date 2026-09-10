import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Holographic20260909')
bpy.ops.wm.open_mainfile(filepath=str(out/'holo_source.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rows=[]
for i,m in enumerate(obj.data.materials):
 pts=[obj.matrix_world@obj.data.vertices[j].co for p in obj.data.polygons if p.material_index==i for j in p.vertices]
 rows.append(dict(material=m.name,bounds=[[min(p[a] for p in pts),max(p[a] for p in pts)] for a in range(3)]))
(out/'material-bounds.json').write_text(json.dumps(rows,indent=2))
# Keep source metres and orientation for the first review.
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review');scene.world.color=(.25,.25,.25)
for mat in obj.data.materials:
 if mat.use_nodes:
  for n in mat.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.image:
    path=Path('D:/FPS3D/FPSGAME/Content/holographicpacked.fbm')/Path(n.image.filepath.replace('\\','/')).name
    if path.exists():n.image.filepath=str(path);n.image.reload()
for p in [(0.1,-.2,.25),(-.1,.1,.2)]:
 bpy.ops.object.light_add(type='AREA',location=p);bpy.context.object.data.energy=10;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=.2
bpy.ops.object.camera_add(location=(-.19,-.17,.13));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.036))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.17;scene.camera=cam
scene.render.filepath=str(out/'holo-source.png');bpy.ops.render.render(write_still=True)
# Normalize pivot to mounting base, X along the sight axis; UE import converts metres to cm.
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
obj.name='SM_M4_Holographic'
bpy.ops.export_scene.fbx(filepath=str(out/'SM_M4_Holographic.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'M4_Holographic_Editable.blend'))
