"""Model-derived owner visor: forged slit walls and a stitched, full-frame liner.

Camera-space artwork has the concept's approximately 8.5:1 aperture. It is not
the external helmet placed on a gameplay camera; the output is straight-alpha.
"""
import bpy, math, json, bisect
from pathlib import Path
from mathutils import Vector

R=Path('D:/FPS3D/FPSGAME/SourceAssets/SteelArmet20261019/ReferenceMatchV5')
for folder in ('Exports','Renders','Textures'):(R/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene

def surface(name,family,normal_strength,tint=.47):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nodes,links=m.node_tree.nodes,m.node_tree.links;p=nodes.get('Principled BSDF')
    coord=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
    scale.inputs['Scale'].default_value=1 if family=='Steel' else 2
    links.new(coord.outputs['UV'],scale.inputs[0])
    for ch in ('BaseColor','Normal','ORM'):
        t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'Textures'/f'T_Armet_{family}_{ch}.png'));links.new(scale.outputs[0],t.inputs['Vector'])
        if ch=='BaseColor':
            # The interior steel is darkened by use; recessed leather fades into
            # the enclosed helmet rather than ending at a visible oval border.
            dark=nodes.new('ShaderNodeMixRGB');dark.blend_type='MULTIPLY';dark.inputs[0].default_value=1
            dark.inputs[2].default_value=(tint,tint,tint,1)
            links.new(t.outputs[0],dark.inputs[1])
            if family=='Leather':
                p.inputs['Specular IOR Level'].default_value=.18
                pos=nodes.new('ShaderNodeNewGeometry');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(pos.outputs['Position'],xyz.inputs[0])
                factors=[]
                for axis,start,end in [('Z',.30,1.02),('X',1.40,1.79)]:
                    absolute=nodes.new('ShaderNodeMath');absolute.operation='ABSOLUTE';links.new(xyz.outputs[axis],absolute.inputs[0])
                    fade=nodes.new('ShaderNodeMapRange');fade.clamp=True;fade.inputs['From Min'].default_value=start;fade.inputs['From Max'].default_value=end;fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=.015
                    links.new(absolute.outputs[0],fade.inputs['Value']);factors.append(fade)
                f=nodes.new('ShaderNodeMath');f.operation='MULTIPLY';links.new(factors[0].outputs[0],f.inputs[0]);links.new(factors[1].outputs[0],f.inputs[1])
                shade=nodes.new('ShaderNodeMixRGB');shade.blend_type='MULTIPLY';shade.inputs[0].default_value=1
                links.new(dark.outputs[0],shade.inputs[1]);links.new(f.outputs[0],shade.inputs[2]);links.new(shade.outputs[0],p.inputs['Base Color'])
            else:links.new(dark.outputs[0],p.inputs['Base Color'])
        elif ch=='Normal':
            t.image.colorspace_settings.name='Non-Color';n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=normal_strength
            links.new(t.outputs[0],n.inputs['Color']);links.new(n.outputs[0],p.inputs['Normal'])
        else:
            t.image.colorspace_settings.name='Non-Color';sep=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs[0],sep.inputs[0])
            links.new(sep.outputs['Green'],p.inputs['Roughness']);links.new(sep.outputs['Blue'],p.inputs['Metallic'])
    return m

steel=surface('Worn forged internal steel','Steel',.9)
cutsteel=surface('Ground steel aperture wall','Steel',.65,.76)
leather=surface('Oiled charcoal leather grain','Leather',.65,.18)
def plain(name,color,rough=.8,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
thread=plain('Muted flax waxed thread',(.071,.052,.030),.9)
seam=plain('Inset leather seam',(.002,.0017,.0013),.9)

# Cubic profile with uniformly spaced arc length. A powered superellipse has
# extreme vertex spacing at its axes, which showed faceted highlights close up.
curves=[
    [(-1.40,.178),(-.70,.187),(.70,.187),(1.40,.178)],
    [(1.40,.178),(1.535,.176264286),(1.60,.14),(1.60,.07)],
    [(1.60,.07),(1.60,.023),(1.60,-.023),(1.60,-.07)],
    [(1.60,-.07),(1.60,-.14),(1.535,-.178057143),(1.40,-.185)],
    [(1.40,-.185),(.70,-.221),(-.70,-.221),(-1.40,-.185)],
    [(-1.40,-.185),(-1.535,-.178057143),(-1.60,-.14),(-1.60,-.07)],
    [(-1.60,-.07),(-1.60,-.023),(-1.60,.023),(-1.60,.07)],
    [(-1.60,.07),(-1.60,.14),(-1.535,.176264286),(-1.40,.178)]
]
arc=[]
for row in curves:
    p=[Vector(x) for x in row]
    for i in range(256):
        t=i/256;s=1-t;arc.append(p[0]*s**3+p[1]*3*s*s*t+p[2]*3*s*t*t+p[3]*t**3)
arc.reverse();arc.append(arc[0]);lengths=[0.]
for i in range(1,len(arc)):lengths.append(lengths[-1]+(arc[i]-arc[i-1]).length)
def opening(a):
    d=(a%math.tau)/math.tau*lengths[-1];i=min(len(arc)-2,bisect.bisect_right(lengths,d)-1)
    return arc[i].lerp(arc[i+1],(d-lengths[i])/(lengths[i+1]-lengths[i]))

def edge(a,d):
    p=opening(a);t=opening(a+.0001)-opening(a-.0001)
    normal=Vector((t.y,-t.x)).normalized()
    return p+normal*d

def uv(ob):
    layer=ob.data.uv_layers.new(name='PhysicalInteriorUV')
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            p=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
            layer.data[li].uv=(p.x*.68,p.z*.68)

def ring(name,profile,material,soft=False):
    vs=[];N=1024
    for d,y in profile:
        for i in range(N):
            a=i/N*math.tau
            x,z=edge(a,d)
            # Small broad compression wrinkles in the padding, not a rubber rim.
            dent=.0032*math.sin(27*a+.7)*math.sin(11*a)*min(1,d/.12) if soft else 0
            vs.append((x,y+dent,z))
    fs=[(j*N+i,(j+1)*N+i,(j+1)*N+(i+1)%N,j*N+(i+1)%N) for j in range(len(profile)-1) for i in range(N)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    ob=bpy.data.objects.new(name,me);S.collection.objects.link(ob);me.materials.append(material)
    for poly in me.polygons:poly.use_smooth=True
    if not soft:
        # Smooth along the aperture, retain the distinct ground wall / bevel
        # normals across its thickness instead of shading it as a rubber tube.
        normals=[]
        for poly in me.polygons:
            row=poly.index//N
            for li in poly.loop_indices:
                i=me.loops[li].vertex_index%N
                radial=Vector(vs[(row+1)*N+i])-Vector(vs[row*N+i])
                tangent=Vector(vs[row*N+(i+1)%N])-Vector(vs[row*N+(i-1)%N])
                normals.append(radial.cross(tangent).normalized())
        me.normals_split_custom_set(normals)
    uv(ob);return ob

ring('01 Ground aperture inner wall',[(0,.10),(.006,.050),(.036,-.010)],cutsteel)
ring('01 Forged bevel and leather seat',[(.036,-.010),(.048,-.016),(.058,0),(.080,.025)],steel)
ring('02 Padded edge and continuous interior',[(.076,.023),(.093,-.005),(.123,-.028),(.168,-.035),(.228,-.024),(.338,.005),(.55,.020),(1.2,.035),(2.5,.035)],leather,True)

def cord(name,points,r,material):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=2
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for dest,p in zip(sp.points,points):dest.co=(*p,1)
    ob=bpy.data.objects.new(name,cu);S.collection.objects.link(ob);cu.materials.append(material);return ob

# Circumferential seam is recessed into the broad liner. Stitch lengths are
# measured along the projected contour so the ends do not bunch up.
contour=[]
for i in range(1025):
    a=i/1024*math.tau;x,z=edge(a,.20);contour.append(Vector((x,-.043,z)))
cord('03 Recessed seam channel',contour,.0026,seam)
distance=0.;next_stitch=.035
for i in range(1,len(contour)):
    segment=contour[i]-contour[i-1];length=segment.length
    while next_stitch<distance+length:
        p=contour[i-1]+segment*((next_stitch-distance)/length);t=segment.normalized()
        # Stitch sits on the surface and is broken into individual sunk ends.
        cord('Waxed hand stitch',[(p-t*.006+Vector((0,-.003,0))),p+Vector((0,-.006,0)),p+t*.006+Vector((0,-.003,0))],.0016,thread)
        next_stitch+=.030
    distance+=length

# Two seams/rivets on the lower cheek liner echo the reference's construction.
for side in (-1,1):
    x=side*.90
    cord('Lower liner panel joint',[(x,-.015,-.405),(x+side*.035,-.012,-.58),(x+side*.065,.005,-1.35)],.006,seam)
    for dx in (-.018,.018):
        for z in (-.47,-.52,-.57,-.62,-.67,-.72,-.77,-.82):
            cord('Panel seam stitch',[(x+dx,-.02,z),(x+dx,-.021,z-.015)],.0016,thread)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=1,location=(x,-.035,-.435))
    ob=bpy.context.object;ob.name='Peened liner fastening';ob.scale=(.018,.008,.018);ob.data.materials.append(steel)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);uv(ob)
    for p in ob.data.polygons:p.use_smooth=True

world=bpy.data.worlds.new('Enclosed helmet ambient');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.20,.22,.24,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.12;S.world=world
for name,pos,target,power,size in [('Slit daylight',(-.5,-1.3,.50),(0,0,0),105,2.5),('Lower sky bounce',(1.,-.75,-.25),(0,0,-.10),28,1.6)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=.28
    ob=bpy.data.objects.new(name,data);S.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Owner optical aperture');cd.type='ORTHO';cd.ortho_scale=32/9;cd.clip_start=.001
cam=bpy.data.objects.new(cd.name,cd);S.collection.objects.link(cam);cam.location=(0,-3,0)
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();S.camera=cam
S.render.engine='CYCLES';S.cycles.samples=160;S.cycles.use_denoising=True
S.render.threads_mode='FIXED';S.render.threads=10
S.render.resolution_x=3072;S.render.resolution_y=1728;S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA';S.render.film_transparent=True
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=.1
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/SteelArmet_Interior.blend'))
S.render.filepath=str(R/'Textures/T_SteelArmet_Visor.png');bpy.ops.render.render(write_still=True)
# The second render is an honest neutral-background presentation of the model;
# production transparency is kept in the first render, not faked with a scene.
S.render.film_transparent=False;S.render.resolution_x=1536;S.render.resolution_y=864;S.cycles.samples=64
S.render.filepath=str(R/'Renders/SteelArmet_Interior.png');bpy.ops.render.render(write_still=True)
(R/'visor.json').write_text(json.dumps(dict(completed=True,source='Exports/SteelArmet_Interior.blend',texture='Textures/T_SteelArmet_Visor.png',clear_center_height_fraction=.198,clear_max_width_fraction=.90,resolution=[3072,1728],projection='normalized viewport; no change to gameplay FOV or shot rays',composition_layer=15,lighting='baked interior daylight; no realtime parallax',runtime_tested=False),indent=2))
print('REFERENCE_ARMET_VISOR_AUTHORED',flush=True)
