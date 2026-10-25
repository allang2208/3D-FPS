import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;OLD=P.parent/'StormDriveBuildV1'
report=[]
for label in ('Steel','Runebound'):
    bpy.ops.wm.open_mainfile(filepath=str(OLD/('StormDrive_'+label+'_Construction.blend')))
    deps=bpy.context.evaluated_depsgraph_get()
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('host_variant')==label]
    trims=[o for o in objects if o.name.startswith('Continuous_ivory_silver_edge')]
    verts=[];faces=[]
    for obj in objects:
        if obj in trims or 'GoldInlay' in str([m.name for m in obj.data.materials if m]):continue
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();mesh.calc_loop_triangles();base=len(verts)
        verts.extend([obj.matrix_world@v.co for v in mesh.vertices])
        faces.extend([tuple(base+i for i in tri.vertices) for tri in mesh.loop_triangles]);evaluated.to_mesh_clear()
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=True)
    entries=[]
    for obj in trims:
        bm=bmesh.new();bm.from_mesh(obj.data)
        top=sorted([obj.matrix_world@v.co for v in obj.data.vertices],key=lambda v:v.z)[-10:]
        entries.append({'object':obj.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),
            'upper_end_min_gap_mm':min(tree.find_nearest(v)[3] for v in top)*1000,
            'upper_end_max_gap_mm':max(tree.find_nearest(v)[3] for v in top)*1000})
        bm.free()
    report.append({'variant':label,'detached_trim_candidates':entries})
(P/'before_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.open_mainfile(filepath=str(OLD/'StormDriveSeats_Editable.blend'))
obj=bpy.data.objects['SM_SteelWarhammer_StormDrive_V1']
for other in bpy.context.scene.objects:other.hide_render=other!=obj
obj.hide_set(False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world.color=(.12,.12,.12)
center=Vector((0,0,.966))
bpy.ops.object.camera_add(location=(.12,-.30,1.075));cam=bpy.context.object
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.117;scene.camera=cam
for loc,power,size in (((-.14,-.17,1.11),5,.17),((.15,-.07,.98),3,.12),((0,.13,1.06),7,.12)):
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'top_before.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TopInspectionScene.blend'))
print('TOP_INSPECTION_DONE',flush=True)
