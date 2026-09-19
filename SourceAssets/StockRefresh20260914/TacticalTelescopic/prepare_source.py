import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Source/Meshy_AdjustableStock.fbx'))
report={'meshes':[],'materials':[],'images':[]}
allpoints=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    pts=np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices]);allpoints.extend(pts)
    report['meshes'].append({'name':o.name,'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'min':pts.min(axis=0).tolist(),'max':pts.max(axis=0).tolist(),'uvs':[uv.name for uv in o.data.uv_layers],'custom_normals':o.data.has_custom_normals})
for m in bpy.data.materials:
    report['materials'].append({'name':m.name,'nodes':[(n.type,n.image.filepath if n.type=='TEX_IMAGE' and n.image else n.name) for n in m.node_tree.nodes] if m.use_nodes else []})
for im in bpy.data.images:report['images'].append({'name':im.name,'path':im.filepath,'size':list(im.size),'packed':bool(im.packed_file)})
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Imported_Source.blend'))
pts=np.array(allpoints);lo=pts.min(axis=0);hi=pts.max(axis=0);center=Vector((lo+hi)*.5)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('SourceReviewWorld');scene.world.use_nodes=True;bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.3,.3,1);bg.inputs[1].default_value=.7
for xyz,power,size in [((-.5,-3,4),500,4),((2,2,2),650,3),((-3,-1,.5),160,2)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(xyz));light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=center+Vector((0,-5,0)));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=float(max(hi[0]-lo[0],hi[2]-lo[2])*1.2);scene.camera=cam
scene.render.filepath=str(P/'source_side.png');bpy.ops.render.render(write_still=True)
cam.location=center+Vector((-3,-5,1.4));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(P/'source_angle.png');bpy.ops.render.render(write_still=True)
(P/'source_report.json').write_text(json.dumps(report,indent=2))
