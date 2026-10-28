"""Author the dimensional raven crown and the shared blade/icon glyph; render production textures."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ART=P/'Art';ART.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.render.engine='CYCLES';S.cycles.samples=48
S.render.film_transparent=True;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA'
S.render.resolution_x=S.render.resolution_y=1536;S.render.resolution_percentage=100
S.world=bpy.data.worlds.new('RavenStudioWorld');S.world.color=(.16,.16,.16);S.view_settings.view_transform='AgX'

def material(name,color,metal=.8,rough=.28,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=125;noise.inputs['Detail'].default_value=3
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.012
    m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs[0],p.inputs['Normal'])
    return m
steel=material('Raven_DarkForgedSteel',(.055,.085,.12),.85,.32)
silver=material('Raven_SilverBevels',(.48,.60,.70),.92,.22)
ice=material('Raven_Crystal',(.06,.40,.75),.3,.16,.32)
eye=material('Raven_LuminousEye',(.10,.60,1),.25,.16,2)
glyphmat=material('Raven_RuneSilver',(.65,.7,.75),.8,.28)

def finish(o,name,mat,bevel=.04):
    o.name=name;o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('ForgedEdge','BEVEL');mod.width=bevel;mod.segments=3
        mod=o.modifiers.new('WeightedMetalNormals','WEIGHTED_NORMAL')
    return o
def ellipsoid(name,location,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=location)
    o=bpy.context.object;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,mat,0)
    for f in o.data.polygons:f.use_smooth=True
    return o
def plate(name,points,mat,y=-.55,depth=.18,ridge=.12):
    n=len(points);cx=sum(p[0] for p in points)/n;cz=sum(p[1] for p in points)/n
    v=[(x,y,z) for x,z in points]+[(x,y+depth,z) for x,z in points]+[(cx,y-ridge,cz)]
    faces=[(2*n,i,(i+1)%n) for i in range(n)]+[tuple(range(n,2*n))]
    faces += [(i,n+i,n+(i+1)%n,(i+1)%n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);S.collection.objects.link(o);return finish(o,name,mat,.025)
def cylinder(name,z,r,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r,depth=depth,location=(0,0,z))
    return finish(bpy.context.object,name,mat,.04)
def ring(name,z,r,t,mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=t,major_segments=64,minor_segments=12,location=(0,0,z))
    return finish(bpy.context.object,name,mat,0)

# The crown has a closed neck, rounded skull, hooked beak and overlapping solid feather plates.
cylinder('Crown_NeckSocket',.48,.70,.96,steel)
for z in (.04,.16,.81,.93):ring('Crown_SocketRim',z,.71,.045,silver)
ellipsoid('Crown_NeckCore',(-.15,.08,2.0),(.78,.61,1.46),steel)
ellipsoid('Crown_Skull',(.13,.0,3.48),(1.15,.69,.83),steel)
plate('Crown_Brow',[(-.85,3.80),(.26,4.19),(1.03,3.79),(.90,3.50),(.18,3.74),(-.60,3.49)],silver,y=-.61,ridge=.16)
# A loft gives the beak a round root and a genuinely hooked solid tip.
sections=[(.85,3.57,.38,.36),(1.35,3.45,.34,.31),(1.8,3.14,.23,.26),(2.03,2.73,.11,.17),(2.03,2.39,.012,.018)]
verts=[]
for x,z,ry,rz in sections:
    for i in range(16):
        a=2*math.pi*i/16;verts.append((x,math.cos(a)*ry,z+math.sin(a)*rz))
faces=[tuple(range(15,-1,-1)),tuple(range((len(sections)-1)*16,len(sections)*16))]
for j in range(len(sections)-1):
    for i in range(16):faces.append((j*16+i,j*16+(i+1)%16,(j+1)*16+(i+1)%16,(j+1)*16+i))
m=bpy.data.meshes.new('HookedBeak');m.from_pydata(verts,[],faces);m.update();o=bpy.data.objects.new('Crown_HookedBeak',m);S.collection.objects.link(o);finish(o,o.name,silver,.025)
plate('Crown_Mandible',[(.72,3.18),(1.62,2.96),(1.97,2.43),(1.73,2.75),(.69,2.98)],steel,y=-.22,depth=.42,ridge=.04)
for side in (-1,1):
    ellipsoid('Crown_EyeSocket',(.58,side*.58,3.52),(.33,.13,.21),silver)
    ellipsoid('Crown_IceEye',(.59,side*.696,3.53),(.215,.075,.12),eye)
    for j in range(7):
        x=-.58-.07*j;z=3.8-j*.37
        points=[(x+.45,z-.18),(x-.16,z+.20),(x-1.05-.11*math.sin(j),z+.78-j*.075),(x-.66,z+.02),(x-.16,z-.51)]
        plate('Crown_Feather_%d_%d'%(side,j),points,silver if j%2==0 else steel,y=side*.56,depth=side*.16,ridge=-side*.10)
        inset=[(x-.12,z+.08),(x-.78,z+.48-j*.04),(x-.45,z+.01),(x-.12,z-.23)]
        plate('Crown_IceInlay_%d_%d'%(side,j),inset,ice,y=side*.72,depth=side*.045,ridge=-side*.04)
plate('Crown_ChestDiamond',[(-.33,.75),(0,1.22),(.33,.75),(0,.32)],silver,y=-.74,ridge=.10)
plate('Crown_ChestCrystal',[(-.18,.75),(0,1.05),(.18,.75),(0,.45)],ice,y=-.86,depth=.06,ridge=.12)
crown=[o for o in S.objects if o.type=='MESH']

def camera(name,location,target,scale):
    bpy.ops.object.camera_add(location=location);c=bpy.context.object;c.name=name;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale;S.camera=c;return c
cam=camera('CrownAssetCamera',(4,-16,6.1),(0,0,2.35),5.8)
for name,loc,power,size,color in [('Key',(-4,-6,8),1100,5,(.72,.83,1)),('Fill',(5,-3,4),750,4,(.45,.7,1)),('Rim',(-3,4,6),1350,3,(.55,.78,1))]:
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.name=name;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.data.color=color;light.rotation_euler=(Vector((0,0,2.5))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrostRaven_Crown_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in crown:o.select_set(True)
bpy.context.view_layer.objects.active=crown[0]
bpy.ops.export_scene.fbx(filepath=str(P/'SM_FrostRaven_Crown.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,add_leaf_bones=False)
S.render.filepath=str(ART/'RavenCrown.png');bpy.ops.render.render(write_still=True)
for o in crown:o.hide_render=True

# Three separated feather strokes on either wing and one long beak/body mark.
sigils=[]
for side in (-1,1):
    leaves=[[(.20,-.10),(.36,.35),(.70,.62),(1.10,1.50),(1.02,.69),(.70,.24)],
            [(.16,-.38),(.47,-.01),(.86,.14),(1.19,.67),(1.02,.07),(.57,-.20)],
            [(.12,-.70),(.43,-.40),(.82,-.34),(1.10,-.02),(.88,-.54),(.38,-.60)]]
    for j,p in enumerate(leaves):sigils.append(plate('Rune_Feather_%d_%d'%(side,j),[(x*side,z) for x,z in p],glyphmat,y=-.05,depth=.08,ridge=.04))
sigils.append(plate('Rune_RavenHead',[(-.22,.25),(-.03,.43),(.19,.33),(.36,.16),(.15,.19),(.03,.06),(-.03,-.91),(-.12,-1.23),(-.20,-.72),(-.14,-.08)],glyphmat,y=-.05,depth=.08,ridge=.05))
cam.location=(0,-12,.12);cam.rotation_euler=(Vector((0,0,.12))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.65
S.render.resolution_x=1024;S.render.resolution_y=1280;S.cycles.samples=32
S.render.filepath=str(ART/'RavenSigilRelief.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrostRaven_Rune_Editable.blend'))
white=bpy.data.materials.new('GlyphMask');white.use_nodes=True;n=white.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(1,1,1,1);o=n.new('ShaderNodeOutputMaterial');white.node_tree.links.new(e.outputs[0],o.inputs[0])
for obj in sigils:obj.data.materials.clear();obj.data.materials.append(white)
S.view_settings.view_transform='Standard';S.cycles.samples=4
S.render.filepath=str(ART/'RavenSigil.png');bpy.ops.render.render(write_still=True)
(P/'art-receipt.json').write_text(json.dumps({'complete':True,'crown_source':'FrostRaven_Crown_Editable.blend','glyph_source':'FrostRaven_Rune_Editable.blend','render_purpose':'Production HUD and rune textures, not gameplay acceptance','crown_meshes':len(crown),'glyph_meshes':len(sigils)},indent=2))
