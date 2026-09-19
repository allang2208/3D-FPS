"""Render exported engine mesh with the engine-computed mount (diagnosis only)."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'diagnostic_engine_ASH.fbx'),use_custom_normals=True)
info=json.loads((O/'engine_mount_frame.json').read_text());F=info['sight_frame']
C=Matrix.Diagonal((1,-1,1,1))
def converted(t):
    x,y,z,w=t['rotation'];m=Quaternion((w,x,y,z)).to_matrix().to_4x4();m.translation=Vector(t['position'])*.01
    return C@m@C
frame=converted(F);inverse=frame.inverted()
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
report=[]
for ob in obs:
    import bmesh
    bm=bmesh.new();bm.from_mesh(ob.data)
    reject=[f for f in bm.faces if 'ASH12' not in ob.data.materials[f.material_index].name]
    bmesh.ops.delete(bm,geom=reject,context='FACES');bm.to_mesh(ob.data);bm.free()
    report.append({'object':ob.name,'materials':[m.name for m in ob.data.materials],'vertices':len(ob.data.vertices)})
    world=ob.matrix_world.copy();ob.parent=None;ob.modifiers.clear();ob.matrix_world=Matrix.Identity(4)
    ob.data.transform(inverse@world)
for ob in list(bpy.context.scene.objects):
    if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
mat=bpy.data.materials.new('Diagnostic grey');mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.24,.27,.30,1);p.inputs['Metallic'].default_value=.15;p.inputs['Roughness'].default_value=.6
for ob in obs:
    ob.data.materials.clear();ob.data.materials.append(mat)
    for f in ob.data.polygons:f.material_index=0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=840;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Diagnostic world');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.12,.12,.12,1)
def aim(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power in [('key',(.2,.6,.6),70),('rim',(.1,-.5,.2),55)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=.6;l=bpy.data.objects.new(name,d);scene.collection.objects.link(l);l.location=pos;aim(l,(.2,0,-.07))
d=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO';d.ortho_scale=.48
camera.location=(.22,.8,-.015);aim(camera,(.245,0,-.055))
scene.render.filepath=str(O/'engine_bare_left.png');bpy.ops.render.render(write_still=True)
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'SM_ASH12_flashlight.fbx'))
for ob in [o for o in bpy.data.objects if o not in before and o.type=='MESH']:
    world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=Matrix.Identity(4)
    ob.data.transform(world);ob.matrix_world=inverse@converted(info['mount_component'])
    ob.data.materials.clear();ob.data.materials.append(mat)
    for f in ob.data.polygons:f.material_index=0
scene.render.filepath=str(O/'engine_current_flashlight.png');bpy.ops.render.render(write_still=True)
(O/'engine_render_objects.json').write_text(json.dumps(report,indent=2));print('ENGINE_ASSEMBLY_RENDERED',flush=True)
