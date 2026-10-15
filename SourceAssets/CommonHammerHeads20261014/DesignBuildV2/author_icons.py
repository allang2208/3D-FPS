"""Production UI icons: actual factory modules in a reusable metal/rivet frame."""
import bpy,json,math,shutil
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];O=P/'Icons';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'CommonHammerHeads_DesignV2_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
modules=[bpy.data.objects[row['mesh']] for row in rows]
for obj in list(bpy.context.scene.objects):
    if obj not in modules:bpy.data.objects.remove(obj,do_unlink=True)
for obj in modules:obj.hide_render=True
for surface in {m for obj in modules for m in obj.data.materials}:
    bs=next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    link=next((link for link in surface.node_tree.links if link.to_socket==bs.inputs['Base Color']),None)
    if link:
        gray=surface.node_tree.nodes.new('ShaderNodeRGBToBW');surface.node_tree.links.new(link.from_socket,gray.inputs[0]);surface.node_tree.links.new(gray.outputs[0],bs.inputs['Base Color'])

def metal(name,value,roughness=.3):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(value,value,value,1);n.inputs['Metallic'].default_value=.85;n.inputs['Roughness'].default_value=roughness
    return mat

silver=metal('Icon silver steel',.38);dark=metal('Icon recessed graphite',.035,.5);bolt=metal('Icon rivets',.55)
def cube(name,center,scale,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    m=o.modifiers.new('machined bevel','BEVEL');m.width=bevel;m.segments=3
    o.modifiers.new('face normals','WEIGHTED_NORMAL');return o
cube('Recessed plate',(0,.25,0),(1.72,.08,1.72),dark,.06)
for x in (-.83,.83):cube('Vertical frame',(x,.14,0),(.16,.16,1.8),silver,.035)
for z in (-.83,.83):cube('Horizontal frame',(0,.14,z),(1.8,.16,.16),silver,.035)
bpy.ops.mesh.primitive_torus_add(major_radius=.69,minor_radius=.027,major_segments=96,minor_segments=12,location=(0,.13,0),rotation=(math.pi/2,0,0))
bpy.context.object.data.materials.append(silver)
for x in (-.81,.81):
    for z in (-.81,.81):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=.037,location=(x,.025,z));bpy.context.object.scale=(1,.45,1);bpy.context.object.data.materials.append(bolt)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.color=(.22,.22,.22)
bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.86;scene.camera=cam
for loc,power,size in [((-2,-3,3),350,3),((2,-2,1),220,2),((0,-1,-2),100,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for row,obj in zip(rows,modules):
    coords=[v.co for v in obj.data.vertices];lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    center=(lo+hi)*.5;size=hi-lo;scale=1.12/math.hypot(size.x,size.z)
    obj.scale=(scale,scale,scale);obj.location=-center*scale;obj.location.y=-.10-size.y*scale*.5;obj.hide_render=False
    scene.render.filepath=str(O/(row['id']+'.png'));bpy.ops.render.render(write_still=True);obj.hide_render=True
    dest=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';dest.mkdir(exist_ok=True)
    for key in ('hammer_heads_'+row['id'],):
        pass  # deployment is owned by import_design.py
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerHeads_DesignV2_Icons.blend'))
(P/'icon_receipt.json').write_text(json.dumps({'source':'CommonHammerHeads_DesignV2_Editable.blend','icons':[r['id'] for r in rows],
    'style':'grayscale PBR; square bevel steel frame, four rivets, circular silver rim','size':[1024,1024],'tested':False},indent=2),encoding='utf-8')
