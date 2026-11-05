"""Exterior concept-art scene. No mechanical interiors or installation geometry."""
from pathlib import Path
from math import sin, cos, pi, copysign, exp, sqrt, atan2
import math,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'ArtSource'; EDITION=ROOT; OUT=EDITION/'Views'
OUT.mkdir(parents=True,exist_ok=True)
WEAVE_PITCH_MULTIPLIER=1.0
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
def collect(n):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);return c
skins=collect('Monocoque silhouette');comb=collect('Cheek saddle');heel=collect('Cushion & sole');hardware=collect('External trim');studio=collect('Lighting')
def mesh(n,v,f,m,col,smooth=True):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    ob=bpy.data.objects.new(n,me);col.objects.link(ob);me.materials.append(m)
    for p in me.polygons:p.use_smooth=smooth
    return ob
def material(name,col,met,rough,grain=0,coat=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    for key,val in [('Base Color',(*col,1)),('Roughness',rough),('Metallic',met),('Coat Weight',coat),('Coat Roughness',.25)]:p.inputs[key].default_value=val
    if grain:
        uv=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=96;noise.inputs['Detail'].default_value=2.2;l.new(uv.outputs['Object'],noise.inputs[0])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=grain;bump.inputs['Distance'].default_value=.010;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    return m
def carbon(name,angle,frequency,darkness,coat):
    m=material(name,(.065,.072,.077),.20,.36,coat=coat);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    frequency=frequency/WEAVE_PITCH_MULTIPLIER
    tc=n.new('ShaderNodeTexCoord');mp=n.new('ShaderNodeMapping');mp.inputs['Rotation'].default_value[2]=math.radians(angle);mp.inputs['Scale'].default_value=(frequency,frequency,1)
    l.new(tc.outputs['UV'],mp.inputs['Vector'])
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ART/'woven_face.png'),check_existing=True);tex.interpolation='Linear';l.new(mp.outputs['Vector'],tex.inputs[0])
    mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(darkness,darkness,darkness,1);l.new(tex.outputs['Color'],mul.inputs[1]);l.new(mul.outputs[0],p.inputs['Base Color'])
    ht=n.new('ShaderNodeTexImage');ht.image=bpy.data.images.load(str(ART/'woven_height.png'),check_existing=True);ht.image.colorspace_settings.name='Non-Color';l.new(mp.outputs[0],ht.inputs[0])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.085;bump.inputs['Distance'].default_value=.006;l.new(ht.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.30,.30,.30,1);r.color_ramp.elements[1].color=(.45,.45,.45,1);l.new(ht.outputs['Color'],r.inputs[0]);l.new(r.outputs[0],p.inputs['Roughness'])
    aniso=next((i for i in p.inputs if i.name.startswith('Anisotropic') and i.type=='VALUE' and 'Rotation' not in i.name),None)
    if aniso:aniso.default_value=.34
    return m
carbon_shell=carbon('Basalt | woven carbon with satin clearcoat',8,2.20,.68,.30)
carbon_flute=carbon('Spine | directional carbon',-15,2.45,.39,.24)
carbon_comb=carbon('Crown | compact diagonal weave',17,2.72,.60,.27)
rub=material('Charcoal | dense shoulder elastomer',(.032,.038,.038),.02,.62,.62)
padface=material('Charcoal | stippled contact rubber',(.024,.029,.029),0,.68,.62)
poly=material('Soft-touch comb insert',(.042,.050,.049),.02,.55,.42)
dark=material('Graphite inset',(.014,.020,.021),.29,.44,.18)
ti=material('Satin titanium',(.19,.20,.18),.83,.30,.09)
slate=material('Dark titanium',(.080,.093,.090),.74,.31,.12)
ivory=material('Small satin witness',(.39,.43,.39),.52,.37)
def clamp(t):return max(0,min(1,t))
def fade(a,b,t):
    k=clamp((t-a)/(b-a));return k*k*(3-2*k)
def curve(xs,ys,t):
    # Monotone Hermite longitudinal shape, independent of mesh sampling resolution.
    if t<=xs[0]:return ys[0]
    if t>=xs[-1]:return ys[-1]
    k=next(i for i in range(len(xs)-1) if xs[i+1]>=t);h=xs[k+1]-xs[k];u=(t-xs[k])/h
    def slope(i):
        if i==0:return (ys[1]-ys[0])/(xs[1]-xs[0])
        if i==len(xs)-1:return (ys[-1]-ys[-2])/(xs[-1]-xs[-2])
        a=(ys[i]-ys[i-1])/(xs[i]-xs[i-1]);b=(ys[i+1]-ys[i])/(xs[i+1]-xs[i])
        return 0 if a*b<=0 else 2*a*b/(a+b)
    return (2*u**3-3*u*u+1)*ys[k]+(-2*u**3+3*u*u)*ys[k+1]+(u**3-2*u*u+u)*h*slope(k)+(u**3-u*u)*h*slope(k+1)
def rings(name, rows, mat,col):
    N=len(rows);M=len(rows[0]);verts=[v for row in rows for v in row];faces=[]
    for i in range(N-1):
        for j in range(M):faces.append((i*M+j,i*M+(j+1)%M,(i+1)*M+(j+1)%M,(i+1)*M+j))
    faces.extend([tuple(reversed(range(M))),tuple((N-1)*M+j for j in range(M))])
    obj=mesh(name,verts,faces,mat,col)
    # Longitudinal lay: use actual surface arc length around each exterior section.
    uv=obj.data.uv_layers.new(name='Carbon drape');arcs=[]
    for row in rows:
        cum=[0.]
        for j in range(M):cum.append(cum[-1]+(Vector(row[(j+1)%M])-Vector(row[j])).length)
        arcs.append(cum)
    # Section goes front-to-back around its perimeter. Check normals, handle the seam explicitly.
    for f in obj.data.polygons:
        if f.index >= (N-1)*M:
            for li in f.loop_indices:
                x,y,z=verts[obj.data.loops[li].vertex_index];uv.data[li].uv=(y,z)
            f.use_smooth=False;continue
        j=f.index%M
        for li in f.loop_indices:
            vi=obj.data.loops[li].vertex_index;i,jj=divmod(vi,M);idx=M if j==M-1 and jj==0 else jj
            uv.data[li].uv=(verts[vi][0],arcs[i][idx])
    import bmesh
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(obj.data);bm.free()
    return obj
xs=[.43,.55,.96,1.80,2.25,2.49,2.72,3.12,4.12,5.30,6.28,7.38,7.91,8.05]
high=[2.63,2.67,2.70,2.66,2.60,2.58,2.55,2.51,2.42,2.28,2.18,2.20,2.22,2.16]
low=[.20,.14,.13,.13,.14,.23,.48,.63,.73,.91,1.12,1.29,1.32,1.37]
wide=[.48,.55,.61,.65,.65,.64,.62,.60,.55,.48,.40,.34,.35,.32]
def params(x):return curve(xs,high,x),curve(xs,low,x),curve(xs,wide,x)
def sidewidth(x,s):
    hi,lo,w=params(x)
    cross=max(.00001,1-abs(2*s-1)**3.6)**(1/3.6)
    # A continuous sculpted compression channel, shallow at both ends.
    ridge=.28+.47*fade(1.1,7.4,x)
    recess=.125*exp(-((s-ridge)/.145)**2)*fade(.65,1.65,x)*(1-fade(6.1,7.91,x))
    flank=.040*exp(-((s-.82)/.11)**2)*fade(.5,1.2,x)*(1-fade(6.4,7.8,x))
    return (w+flank-recess)*cross
rows=[]
for i in range(143):
    x=xs[0]+(xs[-1]-xs[0])*i/142;hi,lo,w=params(x);row=[]
    for j in range(104):
        a=2*pi*j/104;zfrac=copysign(abs(cos(a))**.60,cos(a));s=(zfrac+1)/2
        wy=0 if abs(sin(a))<.00001 else copysign(sidewidth(x,s),sin(a))
        row.append((x-4.14,wy,lo+(hi-lo)*s))
    rows.append(row)
rings('01 | uninterrupted carbon monocoque',rows,carbon_shell,skins)
def patch_side(sign):
    vs=[];faces=[];st=[];nx=92;ny=14
    for i in range(nx):
        k=i/(nx-1);x=.89+6.45*k;hi,lo,w=params(x)
        env=max(.004,fade(0,.15,k)*(1-fade(.84,1,k)))
        sm=.30+.46*fade(1.0,7.8,x)
        for j in range(ny):
            v=j/(ny-1);s=sm+((v-.52)*(.265*env+.002));z=lo+(hi-lo)*s
            relief=.004+.030*sin(pi*v)*env
            vs.append((x-4.14,sign*(sidewidth(x,s)+relief),z));st.append((x,z))
    for i in range(nx-1):
        for j in range(ny-1):
            a=i*ny+j;faces.append((a,a+1,a+ny+1,a+ny) if sign<0 else (a+ny,a+ny+1,a+1,a))
    ob=mesh('02 | swept side spine',vs,faces,carbon_flute,skins);uv=ob.data.uv_layers.new(name='Flank surface')
    for f in ob.data.polygons:
        for l in f.loop_indices:uv.data[l].uv=st[ob.data.loops[l].vertex_index]
    solid=ob.modifiers.new('Buried perimeter','SOLIDIFY');solid.thickness=.014
for sign in (-1,1):patch_side(sign)
def heel_inset(sign):
    # A quiet moulded heel guard interrupts the woven field near the shoulder.
    pts=[];faces=[];nn=47;mm=15
    for i in range(nn):
        f=i/(nn-1);s=.17+.73*f
        outside=.54+.16*f;inner=outside+.02+(.315+.19*f)*max(.001,sin(pi*f))**.65
        for j in range(mm):
            g=j/(mm-1);x=outside+(inner-outside)*g;hi,lo,w=params(x)
            pts.append((x-4.14,sign*(sidewidth(x,s)+.008+.024*sin(pi*g)),lo+(hi-lo)*s))
    for i in range(nn-1):
        for j in range(mm-1):
            a=i*mm+j;faces.append((a,a+mm,a+mm+1,a+1) if sign>0 else (a,a+1,a+mm+1,a+mm))
    ob=mesh('Heel | moulded abrasion guard',pts,faces,poly,heel)
    mod=ob.modifiers.new('Thin perimeter','SOLIDIFY');mod.thickness=.012
for sign in (-1,1):heel_inset(sign)
# The long contact comb has a carbon skirt and a textured, separately inset crown.
def loft_profile(name,stations,profile,m,col,ns=100):
    xvals=[a[0] for a in stations];ys=list(zip(*stations))[1:];rr=[]
    for i in range(ns):
        x=xvals[0]+(xvals[-1]-xvals[0])*i/(ns-1)
        z,w,h=[curve(xvals,y,x) for y in ys]
        rr.append([(x-4.14,sy*w,z+sz*h) for sy,sz in profile])
    return rings(name,rr,m,col)
oval=[(copysign(abs(sin(2*pi*j/72))**.73,sin(2*pi*j/72)),copysign(abs(cos(2*pi*j/72))**.78,cos(2*pi*j/72))) for j in range(72)]
saddle=[(.68,2.61,.38,.035),(.83,2.73,.54,.11),(1.16,2.83,.64,.19),(1.78,2.84,.69,.24),(3.53,2.77,.66,.26),(4.25,2.69,.61,.24),(4.74,2.56,.54,.20),(5.00,2.47,.42,.11),(5.08,2.43,.28,.045)]
loft_profile('03 | gently dropped comb skirt',saddle,oval,carbon_comb,comb)
pad_top=[(1.02,2.91,.32,.025),(1.25,2.98,.45,.073),(1.78,3.02,.53,.09),(3.40,2.97,.51,.095),(4.12,2.91,.45,.092),(4.52,2.78,.36,.066),(4.68,2.70,.24,.022)]
loft_profile('04 | cheek contact overmould',pad_top,oval,poly,comb)
base=[(.63,.16,.37,.038),(.8,.12,.49,.066),(1.90,.115,.52,.065),(2.24,.135,.49,.060),(2.44,.21,.35,.055),(2.52,.28,.20,.028)]
loft_profile('05 | discrete flat toe overmould',base,oval,dark,heel,70)
def rear_rings(name,material,mode):
    arr=[];n=113;M=120
    for i in range(n):
        f=i/(n-1);z=.12+2.59*f
        rnd=max(.001,(1-max(0,1-f/.07)**2)*(1-max(0,1-(1-f)/.082)**2))**.5
        w=(.51+.058*sin(pi*min(1,f*1.20))-.13*(1-f)**3)*rnd
        pts=[]
        for j in range(M):
            a=2*pi*j/M;c=cos(a);ss=sin(a);y=w*copysign(abs(ss)**.77,ss)
            rc=copysign(abs(c)**.75,c)
            if mode=='pad':
                x=.30+.080*(1-f)-(.225+.014*sin(pi*f))*rc*(.22+.78*rnd)
                if c>0:
                    fit=fade(.10,.60,c)*(1-fade(.73,.97,abs(y)/max(w,.012)))
                    for iz in range(8):
                        center=.55+.235*iz+.17*abs(y)
                        x+=.046*exp(-((z-center)/.026)**2)*fit
                    x+=.020*exp(-((abs(y)/max(w,.01)-.81)/.040)**2)*fade(.04,.15,f)*(1-fade(.85,.97,f))
            else:
                x=.515+.048*(1-f)-.092*rc*(.24+.76*rnd);y*=1.014
            pts.append((x-4.14,y,z))
        arr.append(pts)
    return rings(name,arr,material,heel)
rear_rings('06 | shaped pad with recessed traction channels',padface,'pad')
rear_rings('07 | narrow dark pad carrier',slate,'carrier')
def move(o,col):
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o)
def disk(name,x,z,y,rad,dep,m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=80,radius=rad,depth=dep,location=(x-4.14,y,z),rotation=(pi/2,0,0))
    o=bpy.context.object;o.name=name;move(o,hardware);o.data.materials.append(m)
    bevel=o.modifiers.new('Edge catch','BEVEL');bevel.width=min(.016,dep*.3);bevel.segments=3
    n=o.modifiers.new('Face normals','WEIGHTED_NORMAL');return o
def rod(name,pts,r,m):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=r;c.bevel_resolution=3
    sp=c.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,v in zip(sp.points,pts):p.co=(*v,1)
    o=bpy.data.objects.new(name,c);hardware.objects.link(o);c.materials.append(m);return o
# Restrained, flush exterior medallion at the cheek, not an instrument or dial.
for sign in (-1,1):
    x=1.35;z=2.18;hi,lo,w=params(x);y=sidewidth(x,(z-lo)/(hi-lo))
    disk('08 | small recessed control surround',x,z,sign*(y+.005),.140,.030,dark)
    disk('08 | satin outer lip',x,z,sign*(y+.021),.118,.024,slate)
    disk('08 | textured face',x,z,sign*(y+.035),.088,.016,poly)
    for k in range(3):
        xx=x-.038+.036*k;rod('Index | raised flute',[(xx-4.14,sign*(y+.046),z-.040),(xx-4.14+.013,sign*(y+.046),z+.039)],.0055,slate)
    for j in range(3):
        xx=1.56+j*.068;zz=2.22+j*.011;h,l,_=params(xx);offset=sidewidth(xx,(zz-l)/(h-l))+.009
        rod('Index | small cheek witness',[(xx-4.14,sign*offset,zz),(xx-4.14+.010,sign*offset,zz+.035)],.0045,ivory)
    xx=1.92;zz=.46;h,l,_=params(xx);offset=sidewidth(xx,(zz-l)/(h-l))
    disk('Toe | flush trim seat',xx,zz,sign*offset,.093,.025,dark)
    disk('Toe | satin plug',xx,zz,sign*(offset+.011),.072,.016,slate)
# A discreet exterior wear strip is part of the forward neck, with no open interface.
nose=[(7.76,1.76,.32,.375),(7.83,1.76,.355,.408),(7.95,1.76,.36,.410),(8.03,1.77,.345,.39),(8.08,1.77,.31,.35)]
loft_profile('09 | closed graphite neck cap',nose,oval,slate,hardware,40)
# Shot lighting: elongated reflections reveal curvature and the weave under resin.
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.56,.61,.66,1);bg.inputs['Strength'].default_value=.43
def point(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(name,loc,target,energy,sx,sy,col):
    d=bpy.data.lights.new(name,'AREA');d.shape='RECTANGLE';d.energy=energy;d.size=sx;d.size_y=sy;d.color=col
    o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;point(o,target)
lamp('Soft north ribbon',(-2,-4.4,7.6),(0,0,1.4),780,7.2,1.9,(.91,.94,1))
lamp('Long contour reflection',(1.6,3.9,5.7),(0,0,1.6),1250,6.6,1.4,(.82,.90,1))
lamp('Warm fill rear',(-7,-1.3,3.6),(-2.4,0,1.4),440,3,4,(1,.88,.75))
lamp('Nose edge',(5,-2.6,3.1),(2,0,1.65),280,2.4,1.2,(1,.94,.88))
lamp('Quiet forward fill',(1,-8,1),(0,0,1.3),195,7,5,(.91,.94,.99))
camd=bpy.data.cameras.new('Art camera');cam=bpy.data.objects.new('Art camera',camd);studio.objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.045;scene.cycles.max_bounces=5
scene.render.threads_mode='FIXED';scene.render.threads=7;scene.view_settings.view_transform='AgX'
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.resolution_percentage=100
jobs={
'Hero':((2.65,-14.2,4.90),(-.08,0,1.60),9.48,2180,1000,5),
'01_Side':((0,-15,1.57),(0,0,1.57),9.3,1536,1536,0),
'02_Heel':((-14,0,1.58),(0,0,1.58),3.64,1536,1536,0),
'03_Opposite':((0,15,1.57),(0,0,1.57),9.3,1536,1536,0),
'Top':((0,0,15),(0,0,0),9.3,1536,1536,0),
'Weave':((.4,-5.4,2.82),(-1.35,-.49,1.48),2.64,1140,740,-8),
'Comb':((-3.2,-5.4,4.45),(-1.45,-.25,2.65),3.82,1060,650,-4),
'Toe':((-6.4,-3.4,1.87),(-3.6,0,.94),2.60,1060,680,3),
'Shoulder':((3.60,-4.60,4.4),(1.75,-.2,1.73),3.15,1120,700,-5)}
def setup_shot(name,draft=False):
    eye,target,width,w,h,roll=jobs[name];cam.location=eye
    if name=='Top':cam.rotation_euler=(0,0,0)
    else:point(cam,target)
    if roll:cam.rotation_euler.rotate_axis('Z',math.radians(roll))
    camd.type='ORTHO';camd.ortho_scale=width;camd.clip_end=200
    scene.cycles.samples=12 if draft else (44 if name in ('Hero','Weave','Comb','Toe','Shoulder') else 28)
    scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=48 if draft else 100
    scene.render.filepath=str(OUT/(('Study_' if draft else '')+name+'.png'))
def shoot(name,draft=False):
    setup_shot(name,draft)
    bpy.ops.render.render(write_still=True);print('RENDERED',name,flush=True)
if '--study' in sys.argv:shoot('Hero',True)
else:
    setup_shot('Hero')
    scene.render.filepath='//Views/Hero.png'
    for texture in ('woven_face.png','woven_height.png'):
        img=bpy.data.images[texture]
        img.pack()
        img.filepath='//../ArtSource/'+texture
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.region_3d.view_perspective='CAMERA'
                space.overlay.show_overlays=False
                space.shading.type='MATERIAL'
    bpy.context.preferences.filepaths.save_version=0
    file=EDITION/'M24_CarbonSpine_Exterior.blend'
    if 'FINISHED' not in bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True):
        raise RuntimeError('Could not save the editable stock scene')
    print('EDITABLE_SAVED',file,flush=True)
    for n in jobs:shoot(n)
