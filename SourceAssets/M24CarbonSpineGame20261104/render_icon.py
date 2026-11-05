"""Render both gunsmith icon sizes using the actual fitted stock, pointing left."""
from pathlib import Path
import bpy,math
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'M24_CarbonSpine_Fitted.blend'))
scene=bpy.context.scene
stock=[o for o in bpy.data.collections['Native | fitted to M24'].objects if not o.name.startswith('Donor receiver')]
for o in scene.objects:
    if o.type=='MESH':o.hide_render=o not in stock
helper=P.parents[1]/'skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py'
palette={};exec(compile(helper.read_text(),str(helper),'exec'),palette)
palette['apply_grayscale'](stock)
for ob in stock:
    for mat in ob.data.materials:
        if mat and mat.use_nodes:
            for n in mat.node_tree.nodes:
                if n.type=='BUMP' and n.inputs['Distance'].default_value>.0001:
                    n.inputs['Distance'].default_value=.00026
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
palette['neutral_output'](scene)
if not scene.world:scene.world=bpy.data.worlds.new('Studio')
scene.world.color=(.3,.3,.3)
coords=[o.matrix_world@v.co for o in stock for v in o.data.vertices]
mid=Vector([(min(v[i] for v in coords)+max(v[i] for v in coords))*.5 for i in range(3)])
bpy.ops.object.camera_add(location=mid+Vector((-.75,0,0)))
cam=bpy.context.object;cam.rotation_euler=(mid-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.ortho_scale=.368;scene.camera=cam
def lamp(name,loc,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    ob.location=mid+Vector(loc);ob.rotation_euler=(mid-ob.location).to_track_quat('-Z','Y').to_euler()
lamp('Long key',(-.35,.20,.46),8,.43)
lamp('Soft fill',(-.23,-.30,.05),4,.32)
lamp('Edge',(.23,.05,.31),9,.30)
png='ue_m24_stock_m24_carbon_spine_stock.png'
directory=P.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
framed=directory/'FramedFirearms'
scene.render.filepath=str(directory/png)
bpy.ops.render.render(write_still=True)
rotation=cam.rotation_euler.to_matrix()
bpy.context.view_layer.update()
points=[cam.matrix_world.inverted()@p for p in coords]
radius=max(math.hypot(v.x,v.y) for v in points)
half=radius/.74;back=min(v.z for v in points)-half*.06
# Use the same beveled stock-catalog frame as existing locally authored optics.
def material(name,shade,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=140;noise.inputs['Detail'].default_value=3
    l.new(coord.outputs['Generated'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(shade*.67,)*3+(1,);ramp.color_ramp.elements[1].color=(shade*1.12,)*3+(1,)
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.008*half
    l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

steel=material('Frame brushed silver',.37,.85,.30)
edge=material('Frame polished edges',.62,.90,.24)
plate=material('Recessed charcoal plate',.025,.55,.5)
dark=material('Frame seams',.012,.65,.48)

def finish(obj,name,mat):
    obj.name=name;obj.data.materials.append(mat)
    bevel=obj.modifiers.new('Machined rounded edge','BEVEL');bevel.width=.012*half;bevel.segments=3
    obj.modifiers.new('Weighted normal','WEIGHTED_NORMAL')
    return obj

def polygon_ring(name,outer,inner,z,depth,mat):
    n=len(outer);vertices=[(x,y,zz) for points,zz in [(outer,z),(outer,z-depth),(inner,z),(inner,z-depth)] for x,y in points]
    faces=[]
    for i in range(n):
        j=(i+1)%n;faces.extend([(i,j,2*n+j,2*n+i),(i,n+i,n+j,j),(2*n+i,2*n+j,3*n+j,3*n+i),(n+j,n+i,3*n+i,3*n+j)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    o.location=cam.location;o.rotation_euler=cam.rotation_euler;return finish(o,name,mat)

def octagon(r,cut):return [(-r+cut,-r),(r-cut,-r),(r,-r+cut),(r,r-cut),(r-cut,r),(-r+cut,r),(-r,r-cut),(-r,-r+cut)]
def circle(r):return [(r*math.cos(i*math.tau/160),r*math.sin(i*math.tau/160)) for i in range(160)]

polygon_ring('Thick beveled square frame',octagon(half,.15*half),octagon(.87*half,.12*half),back+.04*half,.12*half,steel)
polygon_ring('Outer silver bevel',octagon(.995*half,.15*half),octagon(.965*half,.14*half),back+.065*half,.04*half,edge)
polygon_ring('Inside frame bevel',octagon(.90*half,.12*half),octagon(.87*half,.12*half),back+.045*half,.04*half,edge)
polygon_ring('Silver inner circular ring',circle(.855*half),circle(.805*half),back+.05*half,.045*half,edge)
polygon_ring('Circular dark groove',circle(.87*half),circle(.86*half),back+.035*half,.03*half,dark)

bpy.ops.mesh.primitive_cube_add(size=1)
board=bpy.context.object;board.location=cam.location+rotation@Vector((0,0,back-.065*half));board.rotation_euler=cam.rotation_euler
board.scale=(1.88*half,1.88*half,.10*half);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
finish(board,'Recessed dark backing',plate)
for x in [-.81,.81]:
    for y in [-.81,.81]:
        p=cam.location+rotation@Vector((x*half,y*half,back+.075*half))
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.117*half,depth=.045*half,location=p,rotation=cam.rotation_euler)
        finish(bpy.context.object,'Rivet silver shoulder',edge)
        p=cam.location+rotation@Vector((x*half,y*half,back+.115*half))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.079*half,location=p)
        rivet=bpy.context.object;rivet.rotation_euler=cam.rotation_euler;rivet.scale=(1,1,.48)
        for f in rivet.data.polygons:f.use_smooth=True
        rivet.data.materials.append(steel);rivet.name='Corner rivet'

cam.data.ortho_scale=2.045*half

cam.data.ortho_scale=2.045*half
scene.render.filepath=str(framed/png)
bpy.ops.render.render(write_still=True)
print('M24_CARBON_ICONS_WRITTEN', flush=True)
