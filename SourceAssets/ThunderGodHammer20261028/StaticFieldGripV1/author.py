"""Static Field: dimensioned Blender design, native interfaces, editable PBR source."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
for folder in ('Design','Export'): (P/folder).mkdir(exist_ok=True)
CX,CY=-.00045,-.00105
TAU=math.tau
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (src,dst):
    dst.objects=['SM_ThunderGodHammer_grip_factory']
factory=dst.objects[0];bpy.context.collection.objects.link(factory)
bpy.context.view_layer.update()
factory.data.transform(factory.matrix_world);factory.matrix_world.identity()
parts=[]; rows=[]
def pbr(family):
    mat=bpy.data.materials.new('M_StaticField_'+family);mat.use_nodes=True
    ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=ns.get('Principled BSDF')
    for kind in ('BaseColor','ORM','Normal'):
        tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/('T_StaticField_'+family+'_'+kind+'.png')))
        tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        if kind=='BaseColor':ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif kind=='ORM':
            sep=ns.new('ShaderNodeSeparateColor');ls.new(tex.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        else:
            nm=ns.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=1;ls.new(tex.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
    rows.append(dict(slot=mat.name,kind='pbr',family=family,tint=[1.,1.,1.],normal_strength=1.))
    return mat
leather=pbr('Leather');steel=pbr('Steel');silver=pbr('Silver')
def solid(name,color,rough=.5,metal=.0,emission=(0,0,0)):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    b.inputs['Emission Color'].default_value=(*emission,1);b.inputs['Emission Strength'].default_value=1
    rows.append(dict(slot=name,kind='constant',base=list(color),roughness=rough,metallic=metal,emission=list(emission)))
    return m
thread=solid('M_StaticField_WaxedThread',(.038,.025,.016),.78)
dark=solid('M_StaticField_Recess',(.014,.019,.023),.56,.75)
glow=solid('M_StaticField_IonInlay',(.025,.11,.16),.30,.4,(.03,.45,.72))
native=bpy.data.materials.new('M_StaticField_NativeInterface');native.use_nodes=True
ns=native.node_tree.nodes;ls=native.node_tree.links;bs=ns.get('Principled BSDF')
for kind,file in [('base','BaseColor.jpg'),('orm','MetallicRoughness.jpg'),('normal','Normal.jpg')]:
    n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P.parent/'Textures'/file));n.image.colorspace_settings.name='sRGB' if kind=='base' else 'Non-Color'
    if kind=='base':ls.new(n.outputs['Color'],bs.inputs['Base Color'])
    elif kind=='orm':
        sep=ns.new('ShaderNodeSeparateColor');ls.new(n.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        nm=ns.new('ShaderNodeNormalMap');ls.new(n.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
rows.append(dict(slot=native.name,kind='native'))
for i in range(len(factory.data.materials)):factory.data.materials[i]=native
def mesh(name,vs,fs,mat,uvs=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);parts.append(o)
    uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        f.use_smooth=len(f.vertices)<=4
        cap_axes=sorted(range(3),key=lambda i:abs(f.normal[i]))[:2]
        for li in f.loop_indices:
            vi=me.loops[li].vertex_index
            uv.data[li].uv=(vs[vi][cap_axes[0]]/.065,vs[vi][cap_axes[1]]/.065) if len(f.vertices)>4 else uvs[vi] if uvs else (vs[vi][0]/.065,vs[vi][2]/.065)
    return o
def lathe(name,profile,mat,N=192):
    vs=[];uv=[];fs=[]
    for z,r in profile:
        for j in range(N+1):
            a=TAU*j/N;vs.append((CX+r*math.cos(a),CY+r*math.sin(a),z));uv.append((a*.017/.065,z/.065))
    for k in range(len(profile)-1):
        for j in range(N):
            q=k*(N+1)+j;fs.append((q,q+1,q+1+N+1,q+N+1))
    fs.extend([tuple(reversed(range(N))),tuple((len(profile)-1)*(N+1)+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)
def tube(name,points,mat,width,depth=None,N=8):
    depth=depth or width;vs=[];uv=[];fs=[];length=0.
    for i,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        n=Vector((p.x-CX,p.y-CY,0)).normalized();n=(n-t*n.dot(t)).normalized();b=t.cross(n).normalized()
        if i:length+=(p-Vector(points[i-1])).length
        for j in range(N):
            a=TAU*j/N;v=p+n*(depth*math.cos(a))+b*(width*math.sin(a));vs.append(tuple(v));uv.append((j/N*.001/.065,length/.065))
    for i in range(len(points)-1):
        for j in range(N):
            a=i*N+j;b=i*N+(j+1)%N;fs.append((a,b,b+N,a+N))
    fs.extend([tuple(reversed(range(N))),tuple((len(points)-1)*N+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)
def cyl(a,z,r):return (CX+r*math.cos(a),CY+r*math.sin(a),z)
def native_band(name,z,upper):
    me=factory.data.copy();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
    me.materials.append(dark);bm=bmesh.new();bm.from_mesh(me);nl=bm.loops.layers.float_vector.new('NativeNormals')
    for f,p in zip(bm.faces,me.polygons):
        for l,li in zip(f.loops,p.loop_indices):l[nl]=me.corner_normals[li].vector
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
    edges=[e for e in bm.edges if e.is_boundary]
    for f in bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']:
        f.normal_update();f.material_index=len(me.materials)-1
        for l in f.loops:l[nl]=f.normal;l[bm.loops.layers.uv[0]].uv=(l.vert.co.x/.065,l.vert.co.y/.065)
    normals=[tuple(l[nl]) for f in bm.faces for l in f.loops];bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=True
    me.normals_split_custom_set(normals);parts.append(o)
native_band('01_NativeUpperMatingLand',.400,True)
native_band('02_NativeLowerMatingLand',-.080,False)
bpy.data.objects.remove(factory,do_unlink=True)
# Main hand contact remains the native 30.7 mm diameter; the silver is flush in cut grooves.
R=.01535;z0,z1=-.069,.355;pitch=.106;N=256;K=560;vs=[];fs=[];uv=[]
def wrap(a):return (a+math.pi)%TAU-math.pi
def phase(z,sign):return sign*TAU*(z+.069)/pitch-.8
for k in range(K+1):
    z=z0+(z1-z0)*k/K
    for j in range(N+1):
        a=TAU*j/N;d=min(abs(wrap(a-phase(z,1))),abs(wrap(a-phase(z,-1))))*R
        wrapdist=abs(wrap(a-TAU*(z-z0)/.026-.2))*R
        groove=max(.00023*math.exp(-(d/.00047)**4),.00019*math.exp(-(wrapdist/.00048)**4))
        edge=.000045*math.exp(-((d-.00075)/.0002)**2)
        r=R-groove+edge
        vs.append(cyl(a,z,r));uv.append((a*R/.065,z/.065))
for k in range(K):
    for j in range(N):
        q=k*(N+1)+j;fs.append((q,q+1,q+N+2,q+N+1))
fs.extend([tuple(reversed(range(N))),tuple(K*(N+1)+j for j in range(N))])
mesh('03_RecessedLeatherHandContact',vs,fs,leather,uv)
for sign in (-1,1):
    points=[cyl(phase(z0+(z1-z0)*i/1799,sign),z0+(z1-z0)*i/1799,R-.00017+(sign+1)*.000018) for i in range(1800)]
    tube('04_FlushSilverConductor_'+str(sign),points,silver,.00025,.000055)
# Fine saddle stitches run alongside the dominant leather seam, sunk below its rolled edge.
for i in range(380):
    z=z0+.002+(z1-z0-.004)*i/379
    a=TAU*(z-z0)/.026+.2+.064
    pts=[cyl(a+(-.026+.052*j/4),z+(-.0005+.001*j/4),R-.000005) for j in range(5)]
    tube('05_SaddleStitch_%03d'%i,pts,thread,.000085,.000055,6)
lathe('06_UpperForgedCollar',[(.348,.01530),(.350,.0155),(.351,.0166),(.352,.01725),(.354,.0178),(.357,.0182),(.359,.0184),(.361,.0184),(.362,.01775),(.367,.01765),(.369,.0180),(.387,.0180),(.389,.0177),(.393,.0175),(.396,.0171),(.398,.0160),(.401,.0153)],steel)
lathe('07_LowerForgedFerrule',[(-.081,.0153),(-.079,.0155),(-.077,.01605),(-.075,.0164),(-.072,.0164),(-.070,.0159),(-.067,.01565),(-.064,.01535)],steel)
for label,z,r in [('UpperLip',.3598,.01842),('UpperNeck',.391,.01758),('LowerLip',-.074,.01642)]:
    lathe('08_SilverEdge_'+label,[(z-.0007,r-.0001),(z-.00045,r+.00013),(z+.00045,r+.00013),(z+.0007,r-.0001)],silver)
# Forged continuous interlace on collar: the crossings sit on the collar rather than floating.
for sign in (-1,1):
    pts=[cyl(TAU*i/1200,.3775+sign*.0054*math.sin(6*TAU*i/1200),.01810+sign*.000045*math.cos(6*TAU*i/1200)) for i in range(1201)]
    tube('09_CollarContinuousKnot_'+str(sign),pts,silver,.00031,.00014)
for zc in (.365,.389):
    for sign in (-1,1):
        pts=[cyl(TAU*i/960,zc+sign*.00075*math.sin(18*TAU*i/960),.01778) for i in range(961)]
        tube('09_EdgeTwist_'+str(zc)+'_'+str(sign),pts,silver,.00015,.000065)
# Distinct field medallion at front and back: concentric inlaid rings linked by four radial conductors.
for face,a0 in [('Front',-math.pi/2),('Back',math.pi/2)]:
    # Low fitted backing covers the frieze beneath the emblem, with real thickness.
    vv=[];ff=[];U=64;V=12
    for k in range(V+1):
        z=.369+.017*k/V
        for j in range(U+1):
            a=a0-.33+.66*j/U
            fade=min(j/U,(U-j)/U,k/V,(V-k)/V)
            r=.01838+.00023*min(1,fade*12)
            vv.append(cyl(a,z,r))
    for k in range(V):
        for j in range(U):
            q=k*(U+1)+j;ff.append((q,q+1,q+U+2,q+U+1))
    ob=mesh('10_FittedFieldSeal_'+face,vv,ff,steel)
    mod=ob.modifiers.new('Embedded backing thickness','SOLIDIFY');mod.thickness=.001;mod.offset=-1
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    for ring,(ar,zr) in enumerate([(.265,.0060),(.176,.0040),(.086,.00195)]):
        pts=[cyl(a0+ar*math.cos(TAU*i/240),.3775+zr*math.sin(TAU*i/240),.01868) for i in range(241)]
        tube('11_FieldRing_'+face+str(ring),pts,silver,.00022,.00010)
    for a in [math.pi/4,3*math.pi/4,5*math.pi/4,7*math.pi/4]:
        pts=[cyl(a0+(.09+.165*j/20)*math.cos(a),.3775+(.002+.0039*j/20)*math.sin(a),.01870) for j in range(21)]
        tube('12_FieldNode_'+face+str(a),pts,glow,.00019,.000075)
for sign in (-1,1):
    pts=[cyl(TAU*i/640,-.0715+sign*.00115*math.sin(8*TAU*i/640),.01604) for i in range(641)]
    tube('13_LowerInterlace_'+str(sign),pts,silver,.00020,.000085)
source=bpy.data.collections.new('StaticField_EditableParts');bpy.context.scene.collection.children.link(source)
for o in parts:
    for c in list(o.users_collection):c.objects.unlink(o)
    source.objects.link(o)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64
scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.21,.24,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'
def light(name,loc,power,size,target):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('LargeKey',(-.45,-.55,.65),52,.6,(0,0,0));light('SilverRim',(.42,.2,.38),65,.35,(0,0,.1));light('FrontFill',(.25,-.6,.0),18,.5,(0,0,0))
d=bpy.data.cameras.new('DesignOrthographic');cam=bpy.data.objects.new(d.name,d);scene.collection.objects.link(cam);scene.camera=cam;cam.location=(.0,-2,.025);cam.rotation_euler=(math.pi/2,0,0);d.type='ORTHO';d.ortho_scale=.82
scene.render.resolution_x=2100;scene.render.resolution_y=1700;scene.render.resolution_percentage=100
presentation=bpy.data.collections.new('DesignPresentation');scene.collection.children.link(presentation)
def present(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    presentation.objects.link(o)
def copy_group(x,z,angle=0,scale=1,clip=None):
    for src in parts:
        if clip and (max(v.co.z for v in src.data.vertices)<clip[0] or min(v.co.z for v in src.data.vertices)>clip[1]):continue
        o=src.copy();o.data=src.data.copy();presentation.objects.link(o)
        if clip:
            bm=bmesh.new();bm.from_mesh(o.data)
            for cut,up in [(clip[0],True),(clip[1],False)]:
                bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=up,clear_outer=not up)
            bm.to_mesh(o.data);bm.free()
        o.rotation_euler.z=angle;o.scale=(scale,)*3;o.location=(x,0,z)
copy_group(-.31,-.16);copy_group(-.20,-.16,math.pi/2);copy_group(-.09,-.16,math.pi)
copy_group(.19,.12-3.3*.3775,.28,3.3,(.346,.405))
copy_group(.19,-.17-2.9*.17,-.25,2.9,(.135,.212))
for o in parts:o.hide_render=True;o.hide_set(True)
fontpath=Path('C:/Windows/Fonts/msyh.ttc');font=bpy.data.fonts.load(str(fontpath)) if fontpath.exists() else None
ink=solid('Design_WhiteInk',(.7,.76,.8),1,0,(.22,.24,.27))
def label(text,x,z,size=.010):
    curve=bpy.data.curves.new('Label','FONT');curve.body=text;curve.size=size
    if font:curve.font=font
    curve.materials.append(ink);o=bpy.data.objects.new('Label',curve);presentation.objects.link(o);o.location=(x,-.08,z);o.rotation_euler=(math.pi/2,0,0)
label('静电场  /  STATIC FIELD',-.365,.313,.021)
label('雷神之锤 · 专属特殊握柄改造',-.365,.283,.011)
label('正视',-.325,-.277);label('侧视',-.215,-.277);label('背视',-.105,-.277)
label('嵌银环印 / 连续锻造收口',.084,.248,.011)
label('细孔皮革 / 沉入式导电纹',.084,-.015,.011)
label('原装接口  ·  49 cm  ·  握持直径约 31 mm',-.365,-.301,.010)
label('BLENDER 三视设计与材质构造',.084,-.292,.009)
scene.render.filepath=str(P/'Design/StaticField_ThreeViews.png')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Design.blend'))
(P/'material_manifest.json').write_text(json.dumps(rows[:-1],indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print('STATIC_FIELD_DESIGN_SAVED',flush=True)
