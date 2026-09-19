"""User-requested placement diagnosis: render the actual bare ASH left surface."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
I=json.loads((S/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];old=bpy.data.objects['ASH12_Export']
me=old.data.copy();me.transform(Matrix(I['rail_frame']).inverted()@r.matrix_world.inverted()@old.matrix_world)
diagnostic=bpy.data.scenes.new('ASH left rail diagnosis');bpy.context.window.scene=diagnostic
ob=bpy.data.objects.new('Actual_ASH_reference_mesh',me);bpy.context.collection.objects.link(ob)
mat=bpy.data.materials.new('Neutral diagnostic coating');mat.diffuse_color=(.24,.27,.30,1);mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.24,.27,.30,1);p.inputs['Metallic'].default_value=.15;p.inputs['Roughness'].default_value=.6
ob.data.materials.clear();ob.data.materials.append(mat)
for f in ob.data.polygons:f.material_index=0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=840;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.12,.12,.12,1)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('key',(.2,.6,.6),70,.6),('rim',(.1,-.5,.2),55,.5)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    l=bpy.data.objects.new(name,d);scene.collection.objects.link(l);l.location=pos;aim(l,(.2,0,-.07))
d=bpy.data.cameras.new('Left_surface');camera=bpy.data.objects.new('Left_surface',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO'
for label,pos,target,scale in [('left_rail_close',(.22,.8,-.015),(.245,0,-.055),.48)]:
    camera.location=pos;aim(camera,target);d.ortho_scale=scale;scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(O/'SM_ASH12_flashlight.fbx'),use_custom_normals=True)
devices=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
device_points=[]
for device in devices:
    # UE FBX export imports as Blender x forward, y reversed, in metres.
    for mod in list(device.modifiers):device.modifiers.remove(mod)
    local=device.matrix_world.copy();device.parent=None;device.matrix_world=Matrix.Identity(4)
    device.data.transform(local)
    device_points.extend([list(v.co) for v in device.data.vertices])
    device.matrix_world=Matrix.Translation((.295,.0319,-.0825))@Matrix.Rotation(math.pi,4,'X')
    device.data.materials.clear();device.data.materials.append(mat)
    for f in device.data.polygons:f.material_index=0
(O/'fbx_diagnostic_bounds.json').write_text(json.dumps([[min(p[i] for p in device_points),max(p[i] for p in device_points)] for i in range(3)]))
camera.location=(.22,.8,-.015);aim(camera,(.245,0,-.055));d.ortho_scale=.48;scene.render.filepath=str(O/'left_current_flashlight.png');bpy.ops.render.render(write_still=True)
print('ASH_LEFT_REFERENCE_RENDERS_SAVED',flush=True)
