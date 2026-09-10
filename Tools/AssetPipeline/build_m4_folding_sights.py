"""Split the authored sight heads; retain latest receiver skin and all existing bones."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/m4_source_imported.blend')
sources={n:np.array([list(bpy.data.objects[n].matrix_world@v.co) for v in bpy.data.objects[n].data.vertices]) for n in ['M4 Body','Handguard Kmode Unreal']}
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909/M4_EmptyReload_BoltRelease.blend')
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
meshes=[o for o in rig.children if o.type=='MESH'];heads=[];report=[]
def remove(obj,ids):
 bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in ids],context='VERTS');bm.to_mesh(obj.data);bm.free();obj.data.update()
def export(name,objects,types):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types=types,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
for name,source,groups,pivot,angle in [
 ('Rear','M4 Body','body-components.json',(.0369618,.12475,.069692),90),
 ('Front','Handguard Kmode Unreal','kmode-components.json',(.0369144,-.1893807,.070511),-90)]:
 obj=bpy.data.objects['M4_'+source+'_Export'];original_count=len(obj.data.vertices)
 src=sources[source];dst=np.array([list(v.co) for v in obj.data.vertices]);assert len(src)==len(dst)
 affine=np.linalg.lstsq(np.column_stack([src,np.ones(len(src))]),dst,rcond=None)[0]
 error=float(np.max(np.linalg.norm(np.column_stack([src,np.ones(len(src))])@affine-dst,axis=1)));assert error<1e-6,error
 hinge=Vector(np.append(pivot,1)@affine);axis=Vector(np.array([1,0,0,0])@affine).normalized()
 rows=json.loads((OUT/groups).read_text());ids=set(i for row in rows[:3] for i in row['indices'])
 head=bpy.data.objects.new('SM_M4_'+name+'Sight',obj.data.copy());bpy.context.scene.collection.objects.link(head)
 remove(head,set(range(original_count))-ids);head.vertex_groups.clear()
 head.data.transform(Matrix.Translation(-hinge));export(head.name,[head],{'MESH'})
 remove(obj,ids);assert len(obj.data.vertices)+len(head.data.vertices)==original_count
 head.location=hinge;heads.append((head,hinge,axis,angle))
 # FBX Unreal conversion is Blender X,-Y,Z; centimetre component coordinates.
 report.append(dict(name=name,vertices=len(ids),affine_error_m=error,hinge_cm=[hinge.x*100,-hinge.y*100,hinge.z*100],axis=[axis.x,-axis.y,axis.z],ue_angle=-angle,materials=[m.name for m in head.data.materials]))
export('SK_M4_FoldingSights',[rig,*meshes],{'ARMATURE','MESH'})
(OUT/'folding-sights.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_FoldingSights_Editable.blend'))
# Actual-mesh comparison in bind pose, no invented replacement geometry.
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1200;s.render.resolution_y=600;s.render.resolution_percentage=100
for o in s.objects:o.hide_render=o not in meshes and o not in [h[0] for h in heads]
for o in meshes:
 if 'Arms' in o.name:o.hide_render=True
center=sum((h[1] for h in heads),Vector())*.5
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.5
cam.location=center+Vector((.8,0,.28));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for offset in [(.5,.2,.5),(-.3,-.3,.4)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(offset));bpy.context.object.data.energy=40;bpy.context.object.data.size=.5
for state in ['upright','folded']:
 for head,hinge,axis,angle in heads:
  head.rotation_mode='AXIS_ANGLE';head.rotation_axis_angle=(math.radians(angle) if state=='folded' else 0,*axis)
 s.render.filepath=str(OUT/(state+'.png'));bpy.ops.render.render(write_still=True)
print('M4_FOLDING_BUILD_PASS',json.dumps(report))
