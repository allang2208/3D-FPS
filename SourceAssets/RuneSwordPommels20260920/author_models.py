"""Detailed, editable pommels built from Vibe3D profiles and the exact stock collar.

Production geometry, texture baking and model exports only; no review renders or tests.
Units: metres, blade +Z, width X, front -Y, mount at origin.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from collections import Counter
P=Path(__file__).parent
EXPORT=P/'Export';TEXTURES=P/'Textures'
EXPORT.mkdir(exist_ok=True);TEXTURES.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Interface/SourceInterface.blend'))
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
stock=bpy.data.materials['M_AzureRunesword'].copy();stock.name='M_Pommel_StockCollar_Source'
# Pin the stock image sampling to the retained source UVs, independent of the bake atlas.
uv=stock.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='SourceUV'
for node in stock.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:stock.node_tree.links.new(uv.outputs['UV'],node.inputs['Vector'])
factory=bpy.data.objects['FactoryPommel'];template=bpy.data.objects['StockCollar']
factory.hide_set(True);factory.hide_render=True;template.hide_set(True);template.hide_render=True
base_rows=json.loads((P/'base_profiles.json').read_text())
profile_by_name={r['name']:r for r in base_rows}
assembled={};components={};current=None

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj

def put(obj):
    for coll in list(obj.users_collection):coll.objects.unlink(obj)
    current.objects.link(obj);components[current.name].append(obj)
    return obj

def principal(mat):return next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')

def finish(name,color,metal,rough,emission=0,transmission=0,grain=True):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=principal(mat);bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
    bs.inputs['Transmission Weight'].default_value=transmission;bs.inputs['IOR'].default_value=1.46
    if grain:
        nt=mat.node_tree;n=nt.nodes;l=nt.links
        tc=n.new('ShaderNodeTexCoord')
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1200;noise.inputs['Detail'].default_value=3.0;noise.inputs['Roughness'].default_value=.65
        l.new(tc.outputs['Object'],noise.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[1].position=.85
        ramp.color_ramp.elements[0].color=tuple(c*.74 for c in color)+(1,)
        ramp.color_ramp.elements[1].color=tuple(min(c*1.16,1) for c in color)+(1,)
        l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
        rr=n.new('ShaderNodeMapRange');rr.inputs['From Min'].default_value=0;rr.inputs['From Max'].default_value=1
        rr.inputs['To Min'].default_value=rough*.78;rr.inputs['To Max'].default_value=min(rough*1.35,1)
        l.new(noise.outputs['Fac'],rr.inputs['Value']);l.new(rr.outputs[0],bs.inputs['Roughness'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17;bump.inputs['Distance'].default_value=.000055
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return mat

silver=finish('M_Pommel_Silver_Source',(.40,.425,.445),.94,.29)
iron=finish('M_Pommel_MeteorIron_Source',(.070,.082,.098),.94,.44)
dark=finish('M_Pommel_InlayDark_Source',(.025,.034,.041),.76,.5)
blue=finish('M_Pommel_BlueInlay_Source',(.035,.12,.18),.55,.27,.07)
jade=finish('M_Pommel_JadeCrystal_Source',(.055,.36,.21),0,.14,.14,.58,False)
jade_glow=finish('M_Pommel_StarGlow_Source',(.26,.88,.52),0,.21,2.8,0,False)
bluegem=finish('M_Pommel_BlueGem_Source',(.025,.23,.36),0,.13,.18,.3,False)
# Heterogeneous solid crystal: restrained internal mineral streaks, no metal channel.
nt=jade.node_tree;noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=105;noise.inputs['Detail'].default_value=4
tc=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(tc.outputs['Object'],noise.inputs['Vector'])
ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.035,.21,.115,1);ramp.color_ramp.elements[1].color=(.18,.56,.33,1)
nt.links.new(noise.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],principal(jade).inputs['Base Color'])

def mesh(name,verts,faces,mat,smooth=True,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    obj=bpy.data.objects.new(name,me);put(obj);me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=smooth
    if bevel:
        mod=obj.modifiers.new('Manufactured edge rounds','BEVEL');mod.width=bevel;mod.segments=3
        mod.limit_method='ANGLE';mod.angle_limit=math.radians(23)
    return obj

def load_base(name,mat):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(P/'Interface'/(name+'.fbx')))
    obj=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4);obj.name=name
    obj.data.materials.clear();obj.data.materials.append(mat)
    return put(obj)

def radius_at(name,z):
    rows=[(r*.01,h*.01) for r,h in profile_by_name[name]['points'] if r>0]
    if z>=rows[0][1]:return rows[0][0]
    for (a,za),(b,zb) in zip(rows,rows[1:]):
        if za>=z>=zb:
            t=(z-za)/(zb-za);return a+(b-a)*t
    return rows[-1][0]

def lathe(name,profile,mat,n=96,smooth=True):
    verts=[];faces=[]
    for r,z in profile:
        verts.extend((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n))
    for j in range(len(profile)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces += [tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))]
    return mesh(name,verts,faces,mat,smooth)

def bead_ring(name,z,r,thick,mat=silver):
    steps=12;profile=[(r+thick*math.cos(i*math.tau/steps),z+thick*math.sin(i*math.tau/steps)) for i in range(steps+1)]
    return lathe(name,profile,mat,96)

def stroke(name,points,radius,mat):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=radius;c.bevel_resolution=2;c.use_fill_caps=True
    sp=c.splines.new('POLY');sp.points.add(len(points)-1)
    for v,p in zip(sp.points,points):v.co=(*p,1)
    ob=bpy.data.objects.new(name,c);put(ob);c.materials.append(mat);return ob

def ribbon(name,path,width,thick,mat=silver,inset=True):
    # A closed, load-bearing curved ribbon with a recessed central ornament strip.
    cross=[(-.5,-thick),(.5,-thick),(.5,0),(.42,.00026),(.34,.00026),(.30,-.00010),(-.30,-.00010),(-.34,.00026),(-.42,.00026),(-.5,0)] if inset else [(-.5,-thick),(.5,-thick),(.5,0),(-.5,0)]
    verts=[];faces=[]
    for angle,r,z,w in path:
        for x,d in cross:
            p=Vector((math.cos(angle),math.sin(angle),0))*(r+d)+Vector((-math.sin(angle),math.cos(angle),0))*(x*width*w)
            verts.append((p.x,p.y,z))
    n=len(cross)
    for j in range(len(path)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(path)-1)*n+i for i in range(n))])
    return mesh(name,verts,faces,mat,True)

def ornament(name,angle,z,radial,scale,kind='diamond',mat=dark):
    if kind=='diamond':shape=[(0,scale),(.43*scale,0),(0,-scale),(-.43*scale,0),(0,scale)]
    elif kind=='chevron':shape=[(-.43*scale,.4*scale),(0,-.2*scale),(.43*scale,.4*scale)]
    else:shape=[(0,scale),(0,-scale)]
    points=[]
    for x,dz in shape:
        a=angle+x/max(radial,.006)
        points.append((radial*math.cos(a),radial*math.sin(a),z+dz))
    return stroke(name,points,.00014,mat)

def star(name,center,u,v,radius,mat,points=8,height=.00045):
    center=Vector(center);u=Vector(u);v=Vector(v);normal=u.cross(v).normalized()
    outline=[]
    for i in range(points*2):
        a=i*math.pi/points;rr=radius if i%2==0 else radius*.22
        outline.append(center+(u*math.cos(a)+v*math.sin(a))*rr)
    verts=[tuple(p) for p in outline]+[tuple(center+normal*height),tuple(center-normal*.00016)]
    faces=[];n=len(outline)
    for i in range(n):faces.extend([(i,(i+1)%n,n),((i+1)%n,i,n+1)])
    return mesh(name,verts,faces,mat,False)

def gem(name,center,scale,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=center)
    ob=bpy.context.object;ob.name=name;ob.scale=scale;ob.data.materials.append(mat)
    return put(ob)

def add_mount():
    ob=template.copy();ob.data=template.data.copy();ob.name='Original mounting neck';put(ob)
    ob.hide_set(False);ob.hide_render=False;ob.data.materials.clear();ob.data.materials.append(stock)
    if ob.data.uv_layers:ob.data.uv_layers[0].name='SourceUV'
    # The original cut is closed. Extract its exact perimeter for a continuous transition.
    edge_count=Counter();positions={};cut=-.009
    def key(v):return tuple(round(float(c),7) for c in v)
    for poly in ob.data.polygons:
        coords=[ob.data.vertices[i].co for i in poly.vertices]
        if all(abs(c.z-cut)<.000002 for c in coords):
            for a,b in zip(coords,coords[1:]+coords[:1]):
                ka,kb=key(a),key(b);positions[ka]=a.copy();positions[kb]=b.copy();edge_count[tuple(sorted((ka,kb)))]+=1
    boundary={p for edge,count in edge_count.items() if count==1 for p in edge}
    ring=sorted((positions[k] for k in boundary),key=lambda p:math.atan2(p.y,p.x))
    if len(ring)<8:raise RuntimeError('Cannot author transition without the stock cut perimeter')
    verts=[];faces=[];n=len(ring)
    for j in range(9):
        t=j/8;s=t*t*(3-2*t);z=cut-.008*t
        for p in ring:
            angle=math.atan2(p.y,p.x);r=.0192
            verts.append((p.x*(1-s)+r*math.cos(angle)*s,p.y*(1-s)+r*math.sin(angle)*s,z))
    for j in range(8):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple(8*n+i for i in range(n))])
    mesh('Original rim to new neck transition',verts,faces,silver,True)
    bead_ring('Upper neck engraved edge',-.0126,.0201,.00048)
    bead_ring('Lower neck edge',-.0163,.0195,.00043)
    # Repeating small chevrons around the silver neck band.
    for i in range(24):
        angle=math.tau*i/24
        ornament('Neck diamond',angle,-.0145,.0202,.00145,'diamond')
    return ob

def begin(key):
    global current
    current=bpy.data.collections.new('Authoring_'+key);scene.collection.children.link(current)
    components[current.name]=[];add_mount()

def end(key):assembled[key]=list(components[current.name])

def make_meteor():
    begin('Meteor')
    body=load_base('MeteorBody',iron)
    mod=body.modifiers.new('Forged facet edge bevel','BEVEL');mod.width=.00048;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(18)
    # Eight shoulders tie the socket to the blunt octagonal striking face.
    for k in range(8):
        a=k*math.tau/8;path=[]
        for j in range(65):
            z=-.016-(.1015-.016)*j/64
            r=radius_at('MeteorBody',z)*math.cos(math.pi/8)+.00046
            path.append((a,r,z,1.0+.25*math.sin(math.pi*j/64)))
        ribbon('Meteor reinforcing rib %d'%k,path,.0058,.0012)
        for j,z in enumerate([-.023,-.031,-.040,-.051,-.063,-.076,-.090]):
            r=radius_at('MeteorBody',z)*math.cos(math.pi/8)+.00052
            ornament('Meteor engraved diamond',a,z,r,.0030,'diamond')
            if j<6:ornament('Meteor engraved chevron',a,z-.004,r,.0026,'chevron')
    # Octagonal lower band and the flush celestial impact plate.
    lathe('Octagonal impact rim',[(.0307,-.102),(.0335,-.1016),(.0339,-.1033),(.0329,-.1045),(.0307,-.1045)],silver,8,False).rotation_euler.z=math.pi/8
    star('Meteor eight point inset',(0,0,-.10372),(1,0,0),(0,-1,0),.0265,silver,8,.00048)
    gem('Small blue meteor eye',(0,0,-.1041),(.0032,.0032,.0019),bluegem)
    end('meteor')

def make_jade():
    begin('Jade')
    crystal=load_base('JadeCrystal',jade)
    # Mildly faceted translucent mineral; cage and crystal are separate mesh surfaces.
    for poly in crystal.data.polygons:poly.use_smooth=False
    for k in range(4):
        a=k*math.tau/4;path=[]
        for j in range(81):
            z=-.016-(.114-.016)*j/80;r=radius_at('JadeCrystal',z)+.00065
            w=.8+.38*math.sin(math.pi*j/80)
            path.append((a,r,z,w))
        ribbon('Jade silver meridian %d'%k,path,.0076,.0017)
        for z in [-.027,-.039,-.052,-.066,-.080,-.093]:
            r=radius_at('JadeCrystal',z)+.00072
            ornament('Jade cage engraved diamond',a,z,r,.0036,'diamond')
            ornament('Jade cage fine slash',a,z-.0044,r,.0026,'chevron')
    # A cap, not a hanging ornament: it closes and supports the rib tips.
    lathe('Jade reinforced strike cap',[(.0008,-.1168),(.0075,-.1152),(.0165,-.111),(.0184,-.1084),(.0169,-.1079),(.010,-.1125)],silver,48)
    bead_ring('Jade lower cage ring',-.1088,.0182,.00065)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:
        star('Cage lower star',(math.cos(a)*.0183,math.sin(a)*.0183,-.107),(-math.sin(a),math.cos(a),0),(0,0,1),.0038,silver,4,.00045)
    star('Condensed star core',(0,0,-.068),(1,0,0),(0,0,1),.013,jade_glow,8,.0013)
    star('Crossed star core',(0,0,-.068),(0,1,0),(0,0,1),.0105,jade_glow,4,.0010)
    gem('Solid inner nucleus',(0,0,-.068),(.0045,.0045,.0045),jade_glow)
    end('jade_core')

def swift_radius(z):
    t=max(0,min(1,(-z-.017)/.09))
    return .0188+.0050*math.sin(math.pi*t)**1.35-.0032*t

def make_swift():
    begin('Swift')
    load_base('SwiftEndcap',silver)
    # Four hollow windows between continuous metal ribs; nothing is painted opaque.
    for k in range(4):
        a=k*math.tau/4;path=[]
        for j in range(97):
            t=j/96;z=-.0165-.092*t
            w=1.18-.28*math.sin(math.pi*t)
            path.append((a+.13*math.sin(math.tau*t),swift_radius(z),z,w))
        ribbon('Swift continuous load rib %d'%k,path,.0086,.0026)
        for t in [.17,.37,.57,.77]:
            z=-.0165-.092*t;angle=a+.13*math.sin(math.tau*t);r=swift_radius(z)+.00009
            ornament('Swift blue rune',angle,z,r,.0037,'diamond',blue)
            ornament('Swift rune link',angle,z-.0045,r,.0024,'line',blue)
    bead_ring('Swift upper shared ring',-.0182,.0194,.0010)
    bead_ring('Swift lower shared ring',-.1068,.0165,.00086)
    # Fine swept edge lines articulate the window contours without filling them.
    for k in range(4):
        a=k*math.tau/4
        for side in [-1,1]:
            points=[]
            for j in range(65):
                t=j/64;z=-.019-.086*t;r=swift_radius(z)
                ang=a+.13*math.sin(math.tau*t)+side*.0038/r
                points.append((r*math.cos(ang),r*math.sin(ang),z))
            stroke('Swift polished window lip',points,.00029,silver)
    star('Swift bottom star',(0,0,-.1203),(1,0,0),(0,-1,0),.0048,blue,4,.00030)
    end('swift')

make_meteor();make_jade();make_swift()

# The saved authoring file retains every component and the exact stock reference.
for key,objs in assembled.items():
    for obj in objs:obj.hide_set(key!='meteor');obj.hide_render=key!='meteor'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneSword_Pommels_Editable.blend'))
manifest=[]
for key,objs in assembled.items():
    manifest.append({'id':key,'source_collection':objs[0].users_collection[0].name,'components':[o.name for o in objs],
      'location_cm':[0,0,-19.5],'interface':'azure_hilt_v1'})
(P/'authoring_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('POMMEL_GEOMETRY_AUTHORED',json.dumps([{r['id']:len(r['components'])} for r in manifest]),flush=True)
