"""Refine the Final Toll paired hammerheads against the retained reference; no preview or gameplay run.

World-space authoring uses metres, Z up and the retained factory cross-sections.
All decorative strokes have thickness; silhouette is geometry, not an image plane.
"""
import bpy
import bmesh
import json
import math
import random
import time
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
OUT = P/'Export'
TEX = P/'Textures'
OUT.mkdir(exist_ok=True)
TEX.mkdir(exist_ok=True)
PI = math.pi
TAU = math.tau
PIVOT = Vector((0, 0, .916))
CUTS = {-1: -.0354452141, 1: .0345547859}
PARTS = []
ENERGY = []
CRYSTALS = []
INLAYS = []
CUTTERS = []
START = time.time()
RNG = random.Random(2301023)


def announce(message):
    print('FINAL_TOLL '+message, flush=True)


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def attach(obj, mat, group=None):
    obj.data.materials.append(mat)
    (group if group is not None else PARTS).append(obj)
    return obj


def solid(name, vertices, faces, mat, bevel=0., segments=4, group=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    BUILD.objects.link(obj)
    attach(obj, mat, group)
    if group is not CRYSTALS:
        for polygon in mesh.polygons:
            polygon.use_smooth=True
        mesh.set_sharp_from_angle(angle=math.radians(40))
    if bevel:
        mod = obj.modifiers.new('Machined and hand dressed edge radii', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(32)
        mod.use_clamp_overlap = True
        mod.harden_normals = True
        obj.modifiers.new('Area-weighted corner normals', 'WEIGHTED_NORMAL').keep_sharp = True
    return obj


def frame(origin, normal, u):
    n = Vector(normal).normalized()
    u = Vector(u).normalized()
    return Vector(origin), u, n.cross(u).normalized(), n


def pt(f, x, y, d=0):
    o, u, v, n = f
    return o+u*x+v*y+n*d


OCT = [(-.62,-1),(.62,-1),(1,-.62),(1,.62),(.62,1),(-.62,1),(-1,.62),(-1,-.62)]


def oct_loft(name, side, sections, mat, bevel=.0007):
    vertices = []
    for x, ry, rz in sections:
        vertices += [(CUTS[side]+side*x, y*ry-.0007, z*rz+.916) for y,z in OCT]
    faces = [tuple(reversed(range(8)))]
    for j in range(len(sections)-1):
        for i in range(8):
            k = (i+1)%8
            faces.append((j*8+i,j*8+k,(j+1)*8+k,(j+1)*8+i))
    faces.append(tuple((len(sections)-1)*8+i for i in range(8)))
    return solid(name, vertices, faces, mat, bevel, 6)


def annulus(name, f, inner, outer, d0, d1, mat, count=128, group=None, bevel=0):
    verts = []
    for depth,radius in ((d0,inner),(d0,outer),(d1,outer),(d1,inner)):
        verts += [pt(f,math.cos(i*TAU/count)*radius,math.sin(i*TAU/count)*radius,depth)
                  for i in range(count)]
    faces = []
    for layer in range(4):
        for i in range(count):
            j = (i+1)%count
            faces.append((layer*count+i,layer*count+j,((layer+1)%4)*count+j,((layer+1)%4)*count+i))
    return solid(name,verts,faces,mat,bevel,3,group)


def disk(name,f,radius,d0,d1,mat,count=64,group=None):
    verts = [pt(f,math.cos(i*TAU/count)*radius,math.sin(i*TAU/count)*radius,d)
             for d in (d0,d1) for i in range(count)]
    faces = [tuple(reversed(range(count))),tuple(range(count,2*count))]
    for i in range(count):
        j=(i+1)%count
        faces.append((i,j,count+j,count+i))
    return solid(name,verts,faces,mat,group=group)


def stroke(name,points,radius,mat,sides=8,group=None):
    # Explicit solid swept tubes, including closed end caps. Do not depend on
    # headless curve-to-mesh fill_caps behaviour.
    points = [Vector(p) for p in points]
    if len(points)<2:
        return None
    verts=[]
    for i,p in enumerate(points):
        tangent = (points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        a=tangent.cross(helper).normalized()
        b=tangent.cross(a).normalized()
        verts += [p+radius*(a*math.cos(j*TAU/sides)+b*math.sin(j*TAU/sides)) for j in range(sides)]
    faces=[tuple(reversed(range(sides)))]
    for i in range(len(points)-1):
        for j in range(sides):
            k=(j+1)%sides
            faces.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
    faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    return solid(name,verts,faces,mat,group=group)


def strip(name,f,outline,d0,d1,mat,bevel=.00025,group=None):
    size=len(outline)
    verts=[pt(f,x,y,d) for d in (d0,d1) for x,y in outline]
    faces=[tuple(reversed(range(size))),tuple(range(size,2*size))]
    for i in range(size):
        j=(i+1)%size
        faces.append((i,j,size+j,size+i))
    return solid(name,verts,faces,mat,bevel,4,group)


def node(tree,kind,label=None):
    n=tree.nodes.new(kind)
    if label:
        n.name=label
        n.label=label
    return n


def procedural_metal(name,base,bright,rough,hammered):
    material=bpy.data.materials.new(name)
    material.use_nodes=True
    t=material.node_tree
    p=t.nodes.get('Principled BSDF')
    p.inputs['Metallic'].default_value=.98
    p.inputs['Base Color'].default_value=(*base,1)
    p.inputs['Roughness'].default_value=rough
    coord=node(t,'ShaderNodeTexCoord')
    noise=node(t,'ShaderNodeTexNoise','Fine forging grain 0.8mm')
    noise.inputs['Scale'].default_value=1200
    noise.inputs['Detail'].default_value=3
    t.links.new(coord.outputs['Geometry'] if 'Geometry' in coord.outputs else coord.outputs['Object'],noise.inputs['Vector'])
    color=node(t,'ShaderNodeMixRGB','Steel alloy and oxidation variation')
    color.inputs[1].default_value=(*base,1)
    color.inputs[2].default_value=(*bright,1)
    t.links.new(noise.outputs['Fac'],color.inputs[0])
    geometry=node(t,'ShaderNodeNewGeometry')
    wear=node(t,'ShaderNodeMapRange','Hand worn convex edges')
    wear.inputs['From Min'].default_value=.48
    wear.inputs['From Max'].default_value=.57
    wear.inputs['To Min'].default_value=0
    wear.inputs['To Max'].default_value=.42
    t.links.new(geometry.outputs['Pointiness'],wear.inputs['Value'])
    worn=node(t,'ShaderNodeMixRGB')
    worn.inputs[2].default_value=(*[min(v*1.6+.08,.7) for v in bright],1)
    t.links.new(color.outputs[0],worn.inputs[1])
    t.links.new(wear.outputs[0],worn.inputs[0])
    t.links.new(worn.outputs[0],p.inputs['Base Color'])
    rm=node(t,'ShaderNodeMapRange')
    rm.inputs['To Min'].default_value=max(rough-.08,.1)
    rm.inputs['To Max'].default_value=rough+.08
    t.links.new(noise.outputs['Fac'],rm.inputs[0])
    t.links.new(rm.outputs[0],p.inputs['Roughness'])
    coarse=node(t,'ShaderNodeTexVoronoi','Subtle hammered depressions 5mm')
    coarse.inputs['Scale'].default_value=210
    t.links.new(coord.outputs['Object'],coarse.inputs['Vector'])
    bump=node(t,'ShaderNodeBump','Forging pits below 0.1mm')
    bump.inputs['Strength'].default_value=.24
    bump.inputs['Distance'].default_value=hammered
    t.links.new(coarse.outputs['Distance'],bump.inputs['Height'])
    fine=node(t,'ShaderNodeBump','Fine metal grain')
    fine.inputs['Strength'].default_value=.18
    fine.inputs['Distance'].default_value=.000025
    t.links.new(noise.outputs['Fac'],fine.inputs['Height'])
    t.links.new(bump.outputs[0],fine.inputs['Normal'])
    # Long sparse hairlines are physically separate from the isotropic forging
    # grain; they are not a tiled high-contrast noise layer over the silhouette.
    stretch=node(t,'ShaderNodeVectorMath','Directional hand finishing grain')
    stretch.operation='MULTIPLY'
    stretch.inputs[1].default_value=(45,3400,95)
    t.links.new(coord.outputs['Object'],stretch.inputs[0])
    scratch_noise=node(t,'ShaderNodeTexNoise','Sparse sub-millimetre finishing marks')
    scratch_noise.inputs['Scale'].default_value=1
    scratch_noise.inputs['Detail'].default_value=2
    t.links.new(stretch.outputs[0],scratch_noise.inputs['Vector'])
    scratch=node(t,'ShaderNodeValToRGB','Fine scratched metal threshold')
    scratch.color_ramp.elements[0].position=.66
    scratch.color_ramp.elements[1].position=.76
    t.links.new(scratch_noise.outputs['Fac'],scratch.inputs[0])
    scratched=node(t,'ShaderNodeBump','Hairline surface relief 8 micrometres')
    scratched.inputs['Strength'].default_value=.17
    scratched.inputs['Distance'].default_value=.000008
    scratched.invert=True
    t.links.new(scratch.outputs[0],scratched.inputs['Height'])
    t.links.new(fine.outputs[0],scratched.inputs['Normal'])
    t.links.new(scratched.outputs[0],p.inputs['Normal'])
    surface_rough=node(t,'ShaderNodeMixRGB','Exposed hand-polished hairlines')
    surface_rough.inputs[2].default_value=(max(rough-.11,.12),)*3+(1,)
    t.links.new(scratch.outputs[0],surface_rough.inputs[0])
    t.links.new(rm.outputs[0],surface_rough.inputs[1])
    t.links.new(surface_rough.outputs[0],p.inputs['Roughness'])
    oxide=node(t,'ShaderNodeTexNoise','Broad restrained alloy patina')
    oxide.inputs['Scale'].default_value=92
    oxide.inputs['Detail'].default_value=2
    t.links.new(coord.outputs['Object'],oxide.inputs['Vector'])
    ox_fac=node(t,'ShaderNodeMapRange','Restrained oxide intensity')
    ox_fac.inputs['From Min'].default_value=.44
    ox_fac.inputs['From Max'].default_value=.73
    ox_fac.inputs['To Max'].default_value=.17
    t.links.new(oxide.outputs['Fac'],ox_fac.inputs[0])
    patina=node(t,'ShaderNodeMixRGB','Localized cool oxide in the steel')
    patina.inputs[2].default_value=(*[c*.72 for c in base],1)
    t.links.new(ox_fac.outputs[0],patina.inputs[0])
    t.links.new(worn.outputs[0],patina.inputs[1])
    t.links.new(patina.outputs[0],p.inputs['Base Color'])
    material['physical_grain_m']=.0008
    material['physical_hammer_height_m']=hammered
    material['base_colors_are_linear']=True
    return material


def simple_material(name,color,metal,rough):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal
    p.inputs['Roughness'].default_value=rough
    return m


def initialize():
    global BUILD, HOST, STEEL, SILVER, BRASS, BLACK, JEWEL, FLUX, FINE_BRASS, NATIVE
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    scene.unit_settings.scale_length=1
    BUILD=bpy.data.collections.new('01_FINAL_TOLL_Editable_Components')
    scene.collection.children.link(BUILD)
    HOST=bpy.data.collections.new('02_RETAINED_FACTORY_HOST_reference_only')
    scene.collection.children.link(HOST)
    source=P.parent/'ModulesV1/RuneboundWarhammer_Modular_Editable.blend'
    with bpy.data.libraries.load(str(source),link=False) as (a,b):
        b.objects=[name for name in a.objects if name.startswith('SM_RuneboundWarhammer_') and name.endswith('_factory')]
    for obj in b.objects:
        HOST.objects.link(obj)
        obj['retained_factory_reference']=True
        obj.hide_render=True
        if 'hammer_heads' in obj.name:
            obj.hide_set(True)
    # Appended transforms must enter the dependency graph before factory-local
    # collar vertices are sampled in the common WPN_root author space.
    bpy.context.view_layer.update()
    NATIVE=bpy.data.objects['SM_RuneboundWarhammer_head_mount_factory'].data.materials[0]
    STEEL=procedural_metal('AUTHOR_Blackened_Forged_Steel',(.095,.112,.13),(.20,.225,.25),.41,.000075)
    SILVER=procedural_metal('AUTHOR_Hand_Dressed_Silver_Steel',(.34,.365,.39),(.49,.515,.54),.28,.000022)
    BRASS=procedural_metal('AUTHOR_Aged_Brass_Binding',(.15,.12,.065),(.32,.26,.13),.38,.000018)
    BLACK=procedural_metal('AUTHOR_Dark_Recessed_Engraving',(.025,.031,.037),(.055,.066,.076),.49,.000025)
    FINE_BRASS=procedural_metal('M_FinalToll_FineInlay_Brass',(.25,.155,.065),(.46,.305,.12),.3,.000012)
    JEWEL=simple_material('M_FinalToll_Optical_Crystal',(.012,.07,.24),0,.085)
    jp=JEWEL.node_tree.nodes.get('Principled BSDF')
    jp.inputs['Transmission Weight'].default_value=.72
    jp.inputs['IOR'].default_value=1.52
    jp.inputs['Coat Weight'].default_value=.45
    jp.inputs['Coat Roughness'].default_value=.055
    FLUX=simple_material('M_FinalToll_Rune_Energy',(.25,.14,.025),0,.24)
    t=FLUX.node_tree
    fp=t.nodes.get('Principled BSDF')
    fp.inputs['Emission Color'].default_value=(1,.64,.22,1)
    fp.inputs['Emission Strength'].default_value=2.35
    tint=node(t,'ShaderNodeRGB','EnergyTint')
    tint.outputs[0].default_value=(1,.64,.22,1)
    strength=node(t,'ShaderNodeValue','AwakeIntensity')
    strength.outputs[0].default_value=.35
    mult=node(t,'ShaderNodeMath')
    mult.operation='MULTIPLY_ADD'
    mult.inputs[1].default_value=6
    mult.inputs[2].default_value=.25
    t.links.new(strength.outputs[0],mult.inputs[0])
    t.links.new(mult.outputs[0],fp.inputs['Emission Strength'])
    t.links.new(tint.outputs[0],fp.inputs['Emission Color'])
    FLUX['runtime_parameters']='EnergyTint, AwakeIntensity; destruction red is a tint change'
    scene.world=bpy.data.worlds.new('FinalToll_AuthoringWorld')
    scene.world.color=(.08,.08,.08)
    announce('Host and physical materials loaded')


def original_collar(side):
    source=bpy.data.objects['SM_RuneboundWarhammer_hammer_heads_factory']
    mesh=source.data
    mesh.calc_loop_triangles()
    vertices=[]
    faces=[]
    texcoords=[]
    limit=CUTS[side]+side*.009

    def clip(poly):
        result=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=(limit-a[0].x)*side
            db=(limit-b[0].x)*side
            if da>=0:
                result.append(a)
            if (da>=0)!=(db>=0):
                t=da/(da-db)
                result.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t)))
        return result

    for tri in mesh.loop_triangles:
        poly=[(source.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co,
               mesh.uv_layers[0].data[i].uv.copy()) for i in tri.loops]
        if any(p.x*side<0 for p,_ in poly):
            continue
        poly=clip(poly)
        for i in range(1,len(poly)-1):
            corners=(poly[0],poly[i],poly[i+1])
            if (corners[1][0]-corners[0][0]).cross(corners[2][0]-corners[0][0]).length<1e-12:
                continue
            faces.append(tuple(range(len(vertices),len(vertices)+3)))
            vertices.extend(c[0] for c in corners)
            texcoords.extend(c[1] for c in corners)
    out=solid(('L' if side<0 else 'R')+'_Original_70mm_Interface_Collar',vertices,faces,NATIVE)
    uv=out.data.uv_layers.new(name='OriginalFactoryUV')
    for loop in out.data.loops:
        uv.data[loop.index].uv=texcoords[loop.vertex_index]
    bm=bmesh.new()
    bm.from_mesh(out.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00000035)
    rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x-limit)<.000002 for v in e.verts)]
    if rim:
        bmesh.ops.holes_fill(bm,edges=rim,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(out.data)
    bm.free()
    out['source_interface']='Original factory side cut, preserved coordinates and collar UV'
    return out


GLYPHS=[
    [[(-.3,-.5),(-.3,.5),(.3,.25),(-.3,0),(.3,-.25)]],
    [[(0,-.5),(0,.5)],[(-.35,.2),(0,.45),(.35,.2)]],
    [[(-.35,-.5),(.3,.5)],[(.3,-.5),(-.35,.5)],[(-.1,0),(.35,0)]],
    [[(-.35,-.4),(.3,-.05),(-.35,.3),(.3,.5)]],
    [[(-.3,-.5),(-.3,.5),(.35,.5),(.35,-.1),(-.3,-.1)]],
    [[(0,-.5),(0,.5)],[(-.35,-.2),(0,.08),(.35,-.2)]],
    [[(-.35,-.5),(.35,-.5),(0,0),(.35,.5),(-.35,.5)]],
    [[(-.35,0),(0,.5),(.35,0),(0,-.5),(-.35,0)]],
    [[(-.3,-.5),(-.3,.5),(.35,.1)],[(-.3,-.1),(.35,-.4)]],
    [[(-.35,-.35),(.35,.35)],[(-.35,.35),(.35,-.35)],[(0,-.5),(0,.5)]],
    [[(-.35,-.5),(-.35,.5),(.3,.5)],[(0,-.3),(0,.2),(.35,.2)]],
    [[(-.35,.5),(.35,.15),(-.35,-.15),(.35,-.5)]],
    [[(0,-.5),(0,.5),(.35,.2)],[(0,.1),(-.35,-.2)]],
    [[(-.35,-.5),(.35,-.2),(-.35,.2),(.35,.5)]],
    [[(-.35,-.4),(-.35,.4),(.35,.4),(.35,-.4)],[(0,-.4),(0,.15)]],
    [[(-.35,.2),(0,.5),(.35,.2)],[(0,.5),(0,-.5),(.35,-.2)]],
    [[(-.35,-.5),(-.35,.5),(.35,0),(-.35,-.5)]],
    [[(-.35,.45),(.35,.45),(-.35,-.45),(.35,-.45)]],
    [[(-.3,-.5),(-.3,.5)],[(-.3,.3),(.35,0),(-.3,-.3)]],
    [[(-.35,-.35),(0,0),(-.35,.35)],[(.35,-.35),(0,0),(.35,.35)]],
    [[(-.35,-.5),(.35,.5)],[(-.35,.5),(-.35,0),(.35,0)]],
    [[(0,-.5),(0,.5)],[(-.35,0),(.35,0)],[(-.35,.3),(.35,.3)]],
    [[(-.35,-.4),(.35,-.4),(-.35,.4),(.35,.4)]],
    [[(-.35,-.3),(-.35,.4),(.35,-.4),(.35,.3)]]
]


def glyph_belt(name,f,radius,height,width,depth,count=28):
    # Engraving troughs are real sub-surface channels; fine metal inserts sit
    # inside them. Explicit relief survives close inspection from an oblique view.
    cutters=[]
    for i in range(count):
        angle=TAU*(i+.5)/count
        radial=Vector((math.cos(angle),math.sin(angle)))
        tangent=Vector((-radial.y,radial.x))
        for j,path in enumerate(GLYPHS[(i*7+count)%len(GLYPHS)]):
            coords=[radial*(radius+y*height)+tangent*(x*width) for x,y in path]
            points=[pt(f,q.x,q.y,depth) for q in coords]
            cutter=stroke(name+'_EngravingCutter_%02d_%d'%(i,j),points,.00028,BLACK,8,CUTTERS)
            cutters.append(cutter)
            stroke(name+'_InlaidGlyph_%02d_%d'%(i,j),
                   [p-f[3]*.00020 for p in points],.000115,FINE_BRASS,8,INLAYS)
        if i%2==0:
            q=radial*(radius-height*.72)
            ff=frame(pt(f,q.x,q.y,depth+.00007),f[3],f[1])
            disk(name+'_Punctuation_%02d'%i,ff,.00024,-.00008,.00016,FINE_BRASS,8,INLAYS)
    return cutters


def bolt(name,f,size=.0016):
    annulus(name+'_Counterbore',f,size*.82,size*1.35,-.0005,.00025,BLACK,32)
    annulus(name+'_SilverSeat',f,size*.78,size*1.1,-.00015,.00042,SILVER,32)
    disk(name+'_SixSidedHead',f,size,-.0001,.00115,SILVER,6)
    stroke(name+'_DriverSlot',[pt(f,-size*.55,0,.00116),pt(f,size*.55,0,.00116)],
           .00016,BLACK,6)


def faceted_crystal(name,f,radius):
    count=32
    rings=[(.0,radius*.87),(.001,radius),(.0042,radius*.82),(.007,radius*.43)]
    verts=[]
    for layer,(depth,r) in enumerate(rings):
        shift=(layer%2)*PI/count
        verts += [pt(f,r*math.cos(i*TAU/count+shift),r*math.sin(i*TAU/count+shift),depth) for i in range(count)]
    faces=[tuple(reversed(range(count)))]
    for k in range(len(rings)-1):
        for i in range(count):
            j=(i+1)%count
            # Split the optical crown into true, alternating lapidary facets.
            faces.extend(((k*count+i,k*count+j,(k+1)*count+i),
                          (k*count+j,(k+1)*count+j,(k+1)*count+i)))
    faces.append(tuple((len(rings)-1)*count+i for i in range(count)))
    shell=solid(name+'_32Facet_Crystal',verts,faces,JEWEL,group=CRYSTALS)
    shell['optical_material']='dielectric IOR 1.52; no metallic crystal'
    # A closed internal luminous seal sits below the crystal, not on top of it.
    disk(name+'_InnerLuminousCore',f,radius*.73,-.00065,.0004,FLUX,64,ENERGY)
    annulus(name+'_InternalSeal',f,radius*.58,radius*.625,.0008,.00115,FINE_BRASS,96,INLAYS)
    for phase in (0,PI/4):
        path=[pt(f,math.cos(phase+i*TAU/4)*radius*.57,math.sin(phase+i*TAU/4)*radius*.57,.0012)
              for i in range(5)]
        stroke(name+'_InnerStar_'+str(phase),path,.00023,FLUX,8,ENERGY)
    for k in range(8):
        a=k*TAU/8
        stroke(name+'_RadialFilament_'+str(k),
               [pt(f,math.cos(a)*radius*.15,math.sin(a)*radius*.15,.00135),
                pt(f,math.cos(a)*radius*.52,math.sin(a)*radius*.52,.00135)],
               .00010,FLUX,6,ENERGY)


def setting(name,f,r=.022,end=False):
    outer=r*1.57
    disk(name+'_RecessClosedFloor',f,outer,-.0022,-.0004,BLACK,96)
    annulus(name+'_StructuralBezel',f,r*.93,r*1.16,-.0013,.0024,BRASS,160,bevel=.00018)
    carrier=annulus(name+'_RuneCarrier',f,r*1.18,r*1.49,-.0010,.0005,STEEL,192,bevel=.00012)
    annulus(name+'_OuterLip',f,r*1.5,outer,-.001,.0021,SILVER,160,bevel=.0002)
    for radius in (r*1.19,r*1.49):
        annulus(name+'_HairlineBinding_'+str(radius),f,radius-.00014,radius+.00014,
                .00048,.00082,FINE_BRASS,160,INLAYS)
    cutters=glyph_belt(name,f,r*1.34,r*.20,r*.11,.00058,32 if end else 28)
    activate(cutters[0])
    for cutter in cutters:
        cutter.select_set(True)
    bpy.ops.object.join()
    cutter=bpy.context.object
    cutter.name=name+'_EDITABLE_EngravingTool'
    modifier=carrier.modifiers.new('Recessed rune engraving 0.2mm', 'BOOLEAN')
    modifier.operation='DIFFERENCE'
    modifier.solver='EXACT'
    modifier.use_self=True
    modifier.object=cutter
    cutter.hide_render=True
    cutter.display_type='WIRE'
    cutter.hide_set(True)
    # Beadwork is kept on the principal settings, where it affects the close view.
    for k in range(48):
        a=k*TAU/48
        bf=frame(pt(f,math.cos(a)*r*1.105,math.sin(a)*r*1.105,.0022),f[3],f[1])
        disk(name+'_Bead_%02d'%k,bf,.00032,-.00014,.00026,FINE_BRASS,8,INLAYS)
    for k in range(4):
        a=k*PI/2+PI/4
        radial=Vector((math.cos(a),math.sin(a)))
        tangent=Vector((-radial.y,radial.x))
        shape=[radial*(r*.91)+tangent*.0014,
               radial*(outer+.0025)+tangent*.0018,
               radial*(outer+.0042),
               radial*(outer+.0025)-tangent*.0018,
               radial*(r*.91)-tangent*.0014]
        strip(name+'_SolidRetainingClaw_%d'%k,f,[tuple(q) for q in shape],.0003,.0031,BRASS,.00022)
        tip=pt(f,*(radial*(outer+.0014)),.0029)
        bolt(name+'_ClawPin_%d'%k,frame(tip,f[3],f[1]),.00068)
    crystal_f=frame(f[0]-f[3]*.0048,f[3],f[1])
    faceted_crystal(name,crystal_f,r)
    # Circumferential energy is broken into separate fitted channels.
    for k in range(8):
        a=k*TAU/8
        path=[pt(f,math.cos(a+j*.045)*r*1.025,math.sin(a+j*.045)*r*1.025,.0026) for j in range(6)]
        stroke(name+'_AwakeChannel_%d'%k,path,.00020,FLUX,8,ENERGY)


def box(name, center, size, material, bevel=.00055, group=None):
    c=Vector(center);h=Vector(size)*.5
    verts=[c+Vector((x*h.x,y*h.y,z*h.z)) for z in (-1,1) for y in (-1,1) for x in (-1,1)]
    return solid(name,verts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],material,bevel,4,group)


def crown(name,cx,levels,material):
    verts=[]
    for z,rx,ry in levels:
        verts += [(cx+ox*rx,-.0007+oy*ry,z) for ox,oy in OCT]
    faces=[tuple(reversed(range(8)))]
    for k in range(len(levels)-1):
        faces += [(k*8+i,k*8+(i+1)%8,(k+1)*8+(i+1)%8,(k+1)*8+i) for i in range(8)]
    faces.append(tuple((len(levels)-1)*8+i for i in range(8)))
    return solid(name,verts,faces,material,.00065,5)


def window_surround(name,cx,side_y):
    """Closed 4.8 mm deep arched frame with an actual empty window and inner reveal."""
    outer=[(-.015,.850),(.015,.850),(.015,.951),(.012,.960),(0,.974),(-.012,.960),(-.015,.951)]
    inner=[(-.0102,.855),(.0102,.855),(.0102,.950),(.0075,.957),(0,.966),(-.0075,.957),(-.0102,.950)]
    verts=[]
    for depth,path in ((.034,outer),(.039,outer),(.039,inner),(.034,inner)):
        verts += [(cx+x,-.0007+side_y*depth,z) for x,z in path]
    faces=[];n=len(outer)
    for ring in range(4):
        for i in range(n):
            j=(i+1)%n
            faces.append((ring*n+i,ring*n+j,((ring+1)%4)*n+j,((ring+1)%4)*n+i))
    solid(name,verts,faces,STEEL,.00048,4)
    # The gold arris is sunk into the solid surround, never suspended over the aperture.
    outline=[(cx+x,-.0007+side_y*.03905,z) for x,z in inner]
    stroke(name+'_Inset_Bronze_Arris',outline+[outline[0]],.00055,BRASS,8)


def build_head(side):
    label='L' if side<0 else 'R';cut=CUTS[side];cx=cut+side*.067
    original_collar(side)
    oct_loft(label+'_Solid_Load_Bearing_Neck',side,[(.007,.027,.034),(.015,.030,.035),(.025,.033,.040)],STEEL,.001)
    oct_loft(label+'_Neck_Silver_Weld_Seat',side,[(.009,.029,.035),(.012,.031,.037),(.015,.030,.036)],SILVER,.0006)
    crown(label+'_Flared_Bell_Base',cx,[(.831,.050,.042),(.837,.053,.045),(.845,.051,.043),(.854,.045,.037)],STEEL)
    crown(label+'_Base_Bronze_Binding',cx,[(.839,.053,.044),(.842,.053,.044)],BRASS)
    crown(label+'_Bell_Roof',cx,[(.970,.045,.037),(.978,.049,.041),(.983,.046,.039)],STEEL)
    crown(label+'_Crown_Binding',cx,[(.979,.049,.041),(.982,.049,.041)],SILVER)
    crown(label+'_Tapered_Resonance_Chimney',cx,[(.983,.037,.033),(.994,.027,.025),(1.005,.022,.021)],STEEL)
    crown(label+'_Chimney_Cap',cx,[(1.004,.027,.026),(1.010,.028,.026),(1.014,.023,.022)],SILVER)
    box(label+'_Central_Load_Web',(cx,-.0007,.907),(.088,.008,.116),BLACK,.001)
    for sy in (-1,1):
        y=-.0007+sy*.036
        for i in range(4):
            x=cx-.042+i*.028
            box(label+'_Solid_Vault_Post_%s_%d'%(sy,i),(x,y,.910),(.006,.009,.120),BRASS,.0006)
            # Embedded bolts and square seats are kept inside the top/base rails.
            for z in (.855,.970):
                f=frame((x,-.0007+sy*.0392,z),(0,sy,0),(1,0,0))
                strip(label+'_Captive_Rivet_Seat',f,[(-.003,-.003),(.003,-.003),(.003,.003),(-.003,.003)],-.0007,.0006,BRASS,.00025)
                bolt(label+'_Window_Rivet',f,.00115)
        for i in range(3):
            x=cx-.028+i*.028
            window_surround(label+'_Solid_Arched_Window_%s_%d'%(sy,i),x,sy)
            yy=-.0007+sy*.018
            f=frame((x,yy,.859),(0,0,1),(1,0,0))
            disk(label+'_Resonator_Pivot',f,.003,-.007,.109,SILVER,24)
            disk(label+'_Bronze_Tone_Column',f,.0075,.007,.093,BRASS,48)
            for offset,rr,height in ((.002,.0088,.005),(.012,.0086,.002),(.085,.0086,.003),(.093,.0095,.005)):
                disk(label+'_Column_Turned_Collar',f,rr,offset,offset+height,BRASS,48)
            fy=yy+sy*.00735
            stroke(label+'_Axial_Seal_Recess',[(x,fy,.879),(x,fy,.936)],.00065,BLACK,8)
            stroke(label+'_Axial_Seal_Energy',[(x,fy+sy*.00015,.880),(x,fy+sy*.00015,.935)],.00028,FLUX,8,ENERGY)
            # Glyphs conform to the cylindrical tone column, with a partially embedded cross section.
            for j in range(7):
                z=.886+j*.0065
                for k,path in enumerate(GLYPHS[(i*3+j*5)%len(GLYPHS)]):
                    points=[]
                    for a,b in path:
                        xx=a*.0038
                        surface=math.sqrt(.0075**2-xx**2)
                        points.append((x+xx,yy+sy*(surface+.000035),z+b*.0034))
                    stroke(label+'_Fitted_Column_Inlay',points,.00016,FINE_BRASS,6,INLAYS)
        # No constant-Y lettering on the octagonal corners. Both rows fit the flat rail faces.
        for z,depth,halfwidth in ((.8405,.044,.028),(.9805,.041,.027)):
            for i in range(13):
                x=cx-halfwidth+2*halfwidth*i/12
                ff=frame((x,-.0007+sy*depth,z),(0,sy,0),(1,0,0))
                for path in GLYPHS[(i*7)%len(GLYPHS)]:
                    stroke(label+'_Embedded_Rail_Engraving',[pt(ff,a*.0023,b*.0017,.000025) for a,b in path],.00013,FINE_BRASS,6,INLAYS)
        # Solid taper-mounted trim follows the actual octagonal chimney profile.
        def roofpoint(x,z,offset=0):
            if z<=.994:ry=.033+(.025-.033)*(z-.983)/.011
            else:ry=.025+(.021-.025)*(z-.994)/.011
            return (cx+x,-.0007+sy*(ry+offset),z)
        border=[(-.019,.984),(.019,.984),(.012,.998),(.010,1.003),(-.010,1.003),(-.012,.998)]
        path=[roofpoint(x,z,.0001) for x,z in border]
        stroke(label+'_Fitted_Roof_Binding',path+[path[0]],.00065,BRASS,8)
        emblem=[(0,.986),(-.004,.992),(0,1.001),(.004,.992),(0,.986)]
        stroke(label+'_Roof_Lozenge', [roofpoint(x,z,.00012) for x,z in emblem],.00046,FINE_BRASS,8,INLAYS)
    # Broad 17 mm impact slab, with its ornament embedded in the face.
    f=frame((cut+side*.118,-.0007,.916),(side,0,0),(0,1,0))
    outline=[(-.029,-.074),(.029,-.074),(.041,-.060),(.041,.059),(.027,.075),(-.027,.075),(-.041,.059),(-.041,-.060)]
    strip(label+'_Solid_Impact_Anvil',f,outline,-.010,.007,STEEL,.0017)
    for scale,depth,radius,mat in ((.93,.0068,.0011,SILVER),(.84,.0070,.00045,BRASS)):
        points=[pt(f,a*scale,b*scale,depth) for a,b in outline]
        stroke(label+'_Embedded_Impact_Rim',points+[points[0]],radius,mat,10)
    sigil=[(0,-.055),(-.0017,-.012),(-.006,0),(-.0017,.012),(0,.055),(.0017,.012),(.006,0),(.0017,-.012),(0,-.055)]
    stroke(label+'_Impact_Seal_Recess',[pt(f,a,b,.0068) for a,b in sigil],.00075,BLACK,8)
    stroke(label+'_Impact_Seal_Inlay',[pt(f,a,b,.00710) for a,b in sigil],.00035,FINE_BRASS,8,INLAYS)
    stroke(label+'_Impact_Seal_Energy',[pt(f,0,b,.00710) for b in (-.042,.042)],.00025,FLUX,8,ENERGY)
    for y in (-.025,.025):
        for z in (-.056,.056):
            bolt(label+'_Anvil_Captive_Fastener',frame(pt(f,y,z,.0067),f[3],f[1]),.0015)
    announce(label+' V2 solid windows and surface-fitted details complete')


def join_group(objects,name):
    objects=[o for o in objects if o and o.name in bpy.data.objects]
    activate(objects[0])
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    out=bpy.context.object
    out.name=name
    out.data.name=name+'_Geometry'
    # Keep each authored hard edge, optical facet and evaluated weighted normal.
    triangulate=out.modifiers.new('Explicit tangent-stable export triangles','TRIANGULATE')
    triangulate.quad_method='FIXED'
    triangulate.ngon_method='BEAUTY'
    if 'keep_custom_normals' in triangulate.bl_rna.properties:
        triangulate.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    return out


def unwrap(obj):
    activate(obj)
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(72),island_margin=.0008,
                             area_weight=.2,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.uv_layers.active.name='UVMap'


def bake_maps(obj):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=16
    scene.render.bake.margin=8
    scene.render.bake.use_selected_to_active=False
    scene.render.bake.use_clear=True
    scene.render.threads_mode='FIXED'
    scene.render.threads=12
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='CUDA'
        prefs.get_devices()
        available=[d for d in prefs.devices if d.type=='CUDA']
        if available:
            for device in prefs.devices:
                device.use=device.type=='CUDA'
            scene.cycles.device='GPU'
            announce('PBR bake on CUDA: '+', '.join(d.name for d in available))
    except Exception as error:
        announce('PBR bake uses CPU: '+str(error))
    activate(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    originals=[]
    for mat in obj.data.materials:
        mat.use_nodes=True
        t=mat.node_tree
        output=next(n for n in t.nodes if n.type=='OUTPUT_MATERIAL')
        p=next(n for n in t.nodes if n.type=='BSDF_PRINCIPLED')
        originals.append((mat,output,p,output.inputs['Surface'].links[0].from_socket))
    maps={}
    for channel in ('BaseColor','ORM','Normal'):
        image=bpy.data.images.new('T_FinalToll_'+channel,width=4096,height=4096,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        temporary=[]
        for mat,output,p,original in originals:
            t=mat.node_tree
            target=node(t,'ShaderNodeTexImage','BAKE_TARGET_'+channel)
            target.image=image
            target.select=True
            t.nodes.active=target
            temporary.append((t,target))
            if channel=='Normal':
                continue
            emit=node(t,'ShaderNodeEmission','BAKE_OUTPUT_'+channel)
            temporary.append((t,emit))
            if channel=='BaseColor':
                if p.inputs['Base Color'].is_linked:
                    t.links.new(p.inputs['Base Color'].links[0].from_socket,emit.inputs[0])
                else:
                    emit.inputs[0].default_value=p.inputs['Base Color'].default_value
            else:
                combine=node(t,'ShaderNodeCombineXYZ','Bake AO Roughness Metallic')
                ao=node(t,'ShaderNodeAmbientOcclusion','Local contact crevices 4mm')
                ao.inputs['Distance'].default_value=.004
                ao.samples=16
                ao.inside=False
                ao.only_local=True
                temporary.extend(((t,combine),(t,ao)))
                t.links.new(ao.outputs['AO'],combine.inputs['X'])
                for axis,parameter in (('Y','Roughness'),('Z','Metallic')):
                    socket=p.inputs[parameter]
                    if socket.is_linked:
                        t.links.new(socket.links[0].from_socket,combine.inputs[axis])
                    else:
                        combine.inputs[axis].default_value=socket.default_value
                t.links.new(combine.outputs[0],emit.inputs[0])
            t.links.new(emit.outputs[0],output.inputs['Surface'])
        announce('Baking 4096 '+channel)
        if channel=='Normal':
            scene.render.bake.normal_space='TANGENT'
            bpy.ops.object.bake(type='NORMAL')
        else:
            bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(TEX/(image.name+'.png'))
        image.file_format='PNG'
        image.save()
        image.pack()
        maps[channel]=image
        for mat,output,p,original in originals:
            mat.node_tree.links.new(original,output.inputs['Surface'])
        for tree,n in reversed(temporary):
            tree.nodes.remove(n)
        announce(channel+' written')
    material=simple_material('M_FinalToll_PBR_Surface',(.2,.22,.24),1,.35)
    t=material.node_tree
    p=t.nodes.get('Principled BSDF')
    for index,(key,image) in enumerate(maps.items()):
        tex=node(t,'ShaderNodeTexImage','T_FinalToll_'+key)
        tex.image=image
        tex.location=(-650,-index*260)
        if key=='BaseColor':
            t.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        elif key=='ORM':
            sep=node(t,'ShaderNodeSeparateColor','R AO / G Roughness / B Metallic')
            sep.mode='RGB'
            t.links.new(tex.outputs['Color'],sep.inputs[0])
            t.links.new(sep.outputs['Green'],p.inputs['Roughness'])
            t.links.new(sep.outputs['Blue'],p.inputs['Metallic'])
            gltf_group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
            gltf_group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
            gltf_node=node(t,'ShaderNodeGroup','glTF baked contact occlusion')
            gltf_node.node_tree=gltf_group
            t.links.new(sep.outputs['Red'],gltf_node.inputs['Occlusion'])
            material['ambient_occlusion_texture']='T_FinalToll_ORM.R'
        else:
            normal=node(t,'ShaderNodeNormalMap','Tangent OpenGL; flip green on UE import')
            t.links.new(tex.outputs['Color'],normal.inputs['Color'])
            t.links.new(normal.outputs[0],p.inputs['Normal'])
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.material_index=0
    return maps


def finalize():
    # Editable source retains all cut tools, per-piece modifiers and materials.
    bpy.ops.file.pack_all()
    source_file=P/'FinalTollHammerHead_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source_file))
    announce('Editable construction source saved')
    metal=join_group(PARTS,'FinalToll_Atlas_Surface')
    announce('Structural surfaces frozen for UV and PBR baking')
    unwrap(metal)
    maps=bake_maps(metal)
    brass=join_group(INLAYS,'FinalToll_Fine_Inlay')
    # Explicit inlays use a separate physically based material; this preserves
    # sub-millimetre legibility without depending on tiny atlas islands.
    brass.data.materials.clear()
    brass.data.materials.append(FINE_BRASS)
    for face in brass.data.polygons:
        face.material_index=0
    unwrap(brass)
    energy=join_group(ENERGY,'FinalToll_Emissive_Seals_and_Circuits')
    unwrap(energy)
    final=join_group([metal,brass,energy],'SM_RuneboundWarhammer_FinalTollHammerHeads_V2')
    for vertex in final.data.vertices:
        vertex.co-=PIVOT
    final.location=(0,0,0)
    final['weapon']='ue_runebound_warhammer'
    final['option_id']='final_toll_soul_bell'
    final['slot']='hammer_heads'
    final['installation_offset_cm']=[0,0,91.6]
    final['design_reference']='final_toll_soul_bell_concept.png'
    final['energy_parameters']='M_FinalToll_Rune_Energy: EnergyTint / AwakeIntensity'
    final['purpose']='First-person close-view rigid paired head module'
    final['not_runtime_integrated']=True
    final['chamber_count']=2
    final['resonance_columns_per_chamber']=6
    final['construction']='Open three-window gothic cages, solid strike plates, retained factory collars'
    # Cutters are not exported and remain only in the saved editable source.
    for obj in list(BUILD.objects):
        if obj!=final:
            bpy.data.objects.remove(obj,do_unlink=True)
    activate(final)
    final.data.calc_loop_triangles()
    receipt={
        'name':'终律·镇魂钟','id':'final_toll_soul_bell',
        'status':'modeled, UV-authored, PBR-baked and exported; no gameplay integration',
        'source':str(source_file),'model':final.name,
        'vertices':len(final.data.vertices),'triangles':len(final.data.loop_triangles),
        'materials':[m.name for m in final.data.materials],
        'uv_channels':[uv.name for uv in final.data.uv_layers],
        'pivot_author_m':[0,0,.916],'installation_offset_cm':[0,0,91.6],
        'interface_planes_x_m':[CUTS[-1],CUTS[1]],
        'bounds_local_m':[[min(v.co[i] for v in final.data.vertices) for i in range(3)],
                          [max(v.co[i] for v in final.data.vertices) for i in range(3)]],
        'pbr':{k:{'file':str(TEX/(im.name+'.png')),'resolution':list(im.size),
                  'colorspace':im.colorspace_settings.name} for k,im in maps.items()},
        'orm_channels':{'R':'ambient occlusion','G':'roughness','B':'metallic'},
        'normal_convention':'tangent OpenGL; UE Texture flip_green_channel=True',
        'color_space':'linear shader values; BaseColor stored sRGB',
        'lod_strategy':'Preserve primary close-view geometry; no global decimation or automatic LOD reduction.',
        'runtime_tested':False,'preview_rendered':False,
    }
    fbx=OUT/(final.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',
        use_tspace=True,path_mode='COPY',embed_textures=True)
    announce('Centimetre-convention static FBX exported')
    glb=OUT/'FinalTollHammerHeads_V2.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_materials='EXPORT',export_texcoords=True,export_normals=True,export_tangents=True,
        export_yup=True)
    announce('Self-contained GLB exported')
    final.location=PIVOT
    # The ready-to-use source shows the new heads assembled on the original host.
    for obj in HOST.objects:
        obj.hide_render=False
        obj.hide_set('hammer_heads' in obj.name)
        if 'hammer_heads' in obj.name:
            obj.hide_render=True
    bpy.context.scene.cursor.location=PIVOT
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.clip_start=.001
                area.spaces.active.clip_end=100
                area.spaces.active.region_3d.view_location=PIVOT
                area.spaces.active.region_3d.view_distance=.49
                area.spaces.active.shading.type='MATERIAL'
    bpy.ops.file.pack_all()
    ready=P/'FinalTollHammerHead_Assembled_PBR.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(ready))
    receipt.update(fbx=str(fbx),glb=str(glb),assembled_blend=str(ready),elapsed_seconds=round(time.time()-START,2))
    # Keep the installation contract limited to the six actual factory modules.
    contract_file=P/'host_contract.json'
    if contract_file.is_file():
        contract=json.loads(contract_file.read_text(encoding='utf-8'))
        contract['parts']=[row for row in contract['parts'] if row['object'].startswith('SM_RuneboundWarhammer_')]
        contract_file.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'production_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    announce('PRODUCTION_COMPLETE '+json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    initialize()
    build_head(-1)
    build_head(1)
    finalize()
