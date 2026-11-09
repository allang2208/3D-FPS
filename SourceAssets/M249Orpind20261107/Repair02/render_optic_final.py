"""Focused offline inspection of the assembled optical path; never saves the blend."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'M249_Editable.blend'),use_scripts=False)
def point(x,y,z):return Vector((.0545+y/100,.286-x/100,z/100-.053))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('M249_') and 'Replacement' not in o.name]
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.hide_render=o not in parts
glass=[]
for o in parts:
    for m in o.data.materials:
        if m is None:continue
        if 'Glass' in m.name:
            glass.append(o.name)
            nodes=m.node_tree.nodes;nodes.clear()
            out=nodes.new('ShaderNodeOutputMaterial');transparent=nodes.new('ShaderNodeBsdfTransparent')
            transparent.inputs[0].default_value=(.965,.98,.98,1)
            m.node_tree.links.new(transparent.outputs[0],out.inputs['Surface'])
        elif 'Reticle' in m.name:
            nodes=m.node_tree.nodes;nodes.clear()
            out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission')
            em.inputs[0].default_value=(1,.008,.003,1);em.inputs[1].default_value=2
            m.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
# Nine lines through the aperture, omitting the intentionally visible red reticle.
trees=[]
for o in parts:
    if any(m and ('Glass' in m.name or 'Reticle' in m.name) for m in o.data.materials):continue
    trees.append((o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[p.vertices[:] for p in o.data.polygons])))
rays=[]
for dy,dz in [(0,0)]+[(.5*math.cos(a),.5*math.sin(a)) for a in [i*math.pi/4 for i in range(8)]]:
    origin=point(40.85,.156+dy,13.696+dz)
    hits=[]
    for name,tree in trees:
        location,normal,index,distance=tree.ray_cast(origin,Vector((0,1,0)),.6)
        if location is not None:hits.append(dict(part=name,distance_cm=distance*100))
    rays.append(dict(offset_cm=[dy,dz],opaque_hits=hits))
(root/'optic_clearance.json').write_text(json.dumps(dict(rays=rays,glass_parts=glass),indent=2))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('OpticCheckWorld');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.32,.32,.32,1)
for pos,power in (((.3,-.1,.5),28),((-.2,.1,.3),14)):
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.size=.4
    obj=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(point(15,.156,11)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=1.5,location=point(-20,.156,13.696),rotation=(math.pi/2,0,0))
back=bpy.context.object;back.name='InspectionBackdrop'
m=bpy.data.materials.new('Checker');m.use_nodes=True;nodes=m.node_tree.nodes
checker=nodes.new('ShaderNodeTexChecker');checker.inputs['Color1'].default_value=(.7,.7,.65,1);checker.inputs['Color2'].default_value=(.1,.22,.32,1);checker.inputs['Scale'].default_value=24
m.node_tree.links.new(checker.outputs['Color'],next(n for n in nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color']);back.data.materials.append(m)
camdata=bpy.data.cameras.new('InspectionCamera');cam=bpy.data.objects.new('InspectionCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.clip_start=.001;camdata.clip_end=100
for label,position,target,scale in [('side',(.55,.10,.23),point(14,.156,11),.33),('ads',point(40.85,.156,13.696),point(5.548,.156,13.696),None)]:
    cam.location=position;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO' if scale else 'PERSP'
    if scale:camdata.ortho_scale=scale
    else:camdata.lens=90
    scene.render.filepath=str(root/('optic_final_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('OPTIC_CLEARANCE',json.dumps(rays),flush=True)
