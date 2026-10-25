"""ST6 burgundy beret: editable sculpted shell, tailoring, crest and exports.

Author coordinates: centimetres, X wearer-right, Y rear, Z up. Blender uses
metres and flipped Y. No rendering, UE integration or acceptance tests.
"""
import bpy, bmesh, json, math, hashlib, os
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('ST6_BERET_ROOT',str(P/'SourceAssets/ST6Beret20261023/SurfaceV2')));E=R/'Exports'
E.mkdir(parents=True,exist_ok=True);(R/'Authored').mkdir(exist_ok=True)
HFILE=P/'SourceAssets/BlueMageHat20261019/native_head_jason.json'
head=json.loads(HFILE.read_text(encoding='utf-8-sig'));hp=np.array(head['positions']);z0=float(hp[:,2].max())-6.3
sample=hp[np.abs(hp[:,2]-z0)<.65];center=(sample.min(0)+sample.max(0))*.5;center[2]=z0
xy=sample[:,:2]-center[:2];radii=(sample[:,:2].max(0)-sample[:,:2].min(0))*.5+.48
radii*=max(1.,float(np.sqrt(((xy/radii)**2).sum(1)).max())+.015);RX,RY=radii
TAU=math.tau
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
MODEL=collection('01_ST6_Beret_Editable');HIGH=collection('02_HIGH_FeltSurface_BakeSource');REF=collection('03_Reference_Jason');CUT=collection('04_VentCutters')
HIGH.hide_render=True;HIGH.hide_viewport=True;REF.hide_render=True;REF.hide_viewport=True;CUT.hide_render=True
objects=[];materials={}
def move(ob,col):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    col.objects.link(ob)
def bv(p):return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))
def mesh(name,ps,fs,mat,uv=None,col=MODEL,smooth=True):
    me=bpy.data.meshes.new(name);me.from_pydata([bv(p) for p in ps],[],[list(reversed(f)) for f in fs]);me.update()
    ob=bpy.data.objects.new(name,me);col.objects.link(ob);me.materials.append(mat)
    for f in me.polygons:f.use_smooth=smooth
    if uv is None:
        uv=[]
        for face in fs:
            pts=np.asarray([ps[i] for i in face]);normal=np.cross(pts[1]-pts[0],pts[2]-pts[0]);axes=[i for i in range(3) if i!=int(np.argmax(np.abs(normal)))];uv.append([[p[axes[0]]/4,p[axes[1]]/4] for p in pts])
    if uv:
        layer=me.uv_layers.new(name='PhysicalScaleUV')
        for poly,coords in zip(me.polygons,uv):
            for li,co in zip(poly.loop_indices,reversed(coords)):layer.data[li].uv=co
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    if col==MODEL:objects.append(ob)
    return ob
def material(name,color,roughness,metal=0,family=None,sheen=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness;bs.inputs['Metallic'].default_value=metal;bs.inputs['Sheen Weight'].default_value=sheen
    if family:
        n=m.node_tree.nodes;l=m.node_tree.links
        for channel in ('BaseColor','Normal','ORM'):
            t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'Textures'/('T_'+family+'_'+channel+'.png')),check_existing=True);t.extension='REPEAT';t.label=channel
            if channel=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
            else:
                t.image.colorspace_settings.name='Non-Color'
                if channel=='Normal':
                    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.65;l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
                else:
                    separate=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],separate.inputs['Color']);l.new(separate.outputs['Green'],bs.inputs['Roughness']);l.new(separate.outputs['Blue'],bs.inputs['Metallic'])
    materials[name]=m;return m
FELT=material('ST6_Wine_WoolFelt',(.095,.006,.018),.82,family='ST6_BurgundyFelt',sheen=.38)
LEATHER=material('ST6_Black_Leather',(.018,.016,.015),.48,family='ST6_BlackLeather')
LINING=material('ST6_Burgundy_SatinLining',(.023,.009,.013),.48,family='ST6_Lining',sheen=.18)
SILVER=material('ST6_DarkSilver',(.22,.25,.27),.39,.93,family='ST6_DarkSilver')
RECESS=material('ST6_OxidizedSilverRecess',(.055,.065,.074),.53,.9)
THREAD=material('ST6_Black_WaxedThread',(.023,.02,.021),.64)
WINE_THREAD=material('ST6_Wine_TailoringThread',(.085,.012,.025),.75)
LABEL=material('ST6_Woven_Label',(.16,.15,.13),.78)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
knots=np.array([0,.08,.2,.35,.5,.65,.8,.92,1.]);scales=np.array([1.005,1.045,1.20,1.36,1.31,1.10,.80,.43,0.]);levels=np.array([.75,1.30,1.95,2.80,4.55,6.30,7.50,8.00,8.14])
def hermite(t,values):
    i=min(len(knots)-2,max(0,int(np.searchsorted(knots,t)-1)));u=(t-knots[i])/(knots[i+1]-knots[i]);slopes=np.gradient(values,knots);span=knots[i+1]-knots[i]
    return (2*u**3-3*u*u+1)*values[i]+(u**3-2*u*u+u)*span*slopes[i]+(-2*u**3+3*u*u)*values[i+1]+(u**3-u*u)*span*slopes[i+1]
def angular(a,b):return (a-b+math.pi)%TAU-math.pi
def crown(t,a):
    scale=hermite(t,scales);z=hermite(t,levels);s=math.sin(a);cx=1.35*math.sin(math.pi*t)-1.65*float(smooth((t-.6)/.4));cy=.28*math.sin(math.pi*t)
    e=math.sin(math.pi*t)**1.25
    z+=(-2.65*max(s,0)**1.6+1.35*max(-s,0)**1.5)*e
    fold=0.
    for angle,strength in ((.84,.20),(1.57,.27),(2.32,.16),(-2.3,.07)):
        da=angular(a,angle+.28*t);g=math.exp(-((t-.35)/.25)**2)*math.sin(math.pi*t)
        fold+=strength*g*(-math.exp(-(da/.105)**2)+.48*math.exp(-((da-.17)/.13)**2))
    ripple=.035*math.sin(a*9+t*5)*math.exp(-((t-.16)/.16)**2)*math.sin(math.pi*t)
    radius_shift=fold+ripple;z+=fold*.75
    return np.array([cx+(RX*scale+radius_shift)*math.sin(a),cy-(RY*scale+radius_shift)*math.cos(a),z])
def surface(name,nr,na,fn,mat,tile=10):
    ts=np.linspace(0,.988,nr);ps=[fn(float(t),math.pi+TAU*i/na) for t in ts for i in range(na)];fs=[];uv=[]
    for j in range(nr-1):
        for i in range(na):
            fs.append([j*na+i,j*na+(i+1)%na,(j+1)*na+(i+1)%na,(j+1)*na+i]);uv.append([(i/na*tile,j/(nr-1)*3),((i+1)/na*tile,j/(nr-1)*3),((i+1)/na*tile,(j+1)/(nr-1)*3),(i/na*tile,(j+1)/(nr-1)*3)])
    ps.append(fn(1,0));tip=len(ps)-1
    for i in range(na):fs.append([(nr-1)*na+i,(nr-1)*na+(i+1)%na,tip]);uv.append([(i/na*tile,3),((i+1)/na*tile,3),((i+.5)/na*tile,3.1)])
    return mesh(name,ps,fs,mat,uv),ps,fs
crown_ob,cp,cf=surface('01_Felt_Crown_AsymmetricDrape',52,192,crown,FELT)
solid=crown_ob.modifiers.new('Real felt thickness 1.8mm','SOLIDIFY');solid.thickness=.0018;solid.offset=-1;solid.use_even_offset=True
tree=BVHTree.FromPolygons([bv(p) for p in cp],cf,all_triangles=False)
def lining(t,a):
    q=crown(t,a);q[0]*=.978;q[1]*=.978;q[2]-=.27
    return q
lining_ob,_,_=surface('02_Sewn_Interior_Lining',38,144,lining,LINING,7)
solid=lining_ob.modifiers.new('Satin shell 0.55mm','SOLIDIFY');solid.thickness=.00055;solid.offset=-1
def tube(name,paths,radius,mat,sides=6,closed=False):
    ps=[];fs=[];uv=[]
    for path in paths:
        path=np.array(path);start=len(ps);length=len(path)
        for j,p in enumerate(path):
            direction=path[(j+1)%length]-path[(j-1)%length] if closed else path[min(j+1,length-1)]-path[max(j-1,0)]
            direction/=max(np.linalg.norm(direction),1e-12);ref=np.array([0.,0.,1.]) if abs(direction[2])<.9 else np.array([1.,0.,0.]);u=np.cross(direction,ref);u/=np.linalg.norm(u);v=np.cross(direction,u)
            ps.extend([p+radius*(u*math.cos(TAU*i/sides)+v*math.sin(TAU*i/sides)) for i in range(sides)])
        for j in range(length if closed else length-1):
            for i in range(sides):
                fs.append([start+j*sides+i,start+j*sides+(i+1)%sides,start+((j+1)%length)*sides+(i+1)%sides,start+((j+1)%length)*sides+i]);uv.append([(i/sides,j*.2),((i+1)/sides,j*.2),((i+1)/sides,(j+1)*.2),(i/sides,(j+1)*.2)])
        if not closed:
            fs.extend([[start+i for i in reversed(range(sides))],[start+(length-1)*sides+i for i in range(sides)]]);uv.extend([[(i/sides,0) for i in reversed(range(sides))],[(i/sides,1) for i in range(sides)]])
    return mesh(name,ps,fs,mat,uv)
def band(a,z,r=0):return np.array([(RX+r)*math.sin(a),-(RY+r)*math.cos(a),z+.12*math.cos(a)-.09*math.sin(a)])
ps=[];fs=[];uv=[];n=256
for j in range(5):
    z=-.65+j*.375
    for i in range(n):ps.append(band(math.pi+TAU*i/n,z,.035))
for j in range(4):
    for i in range(n):fs.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i]);uv.append([(i/n*15,j*.09375),((i+1)/n*15,j*.09375),((i+1)/n*15,(j+1)*.09375),(i/n*15,(j+1)*.09375)])
band_ob=mesh('03_Black_Leather_Headband',ps,fs,LEATHER,uv);s=band_ob.modifiers.new('Turned leather thickness','SOLIDIFY');s.thickness=.0012;s.offset=-1
tube('04_Leather_RolledEdges',[[band(a,z,.045) for a in np.linspace(0,TAU,384,endpoint=False)] for z in (-.65,.85)],.07,LEATHER,8,True)
stitches=[]
for z in (-.40,.59):
    for a in np.linspace(0,TAU,150,endpoint=False):stitches.append([band(a+d,z,.105)+[0,0,.015*math.sin(k*math.pi/3)] for k,d in enumerate(np.linspace(0,.027,4))])
tube('05_Headband_Double_SaddleStitches',stitches,.021,THREAD,5)
# Soft crown gathering stitches, a sewn rear shaping seam and inside lining seam.
seams=[]
for a in np.linspace(0,TAU,160,endpoint=False):seams.append([crown(.025,a+d)+[0,0,.032] for d in (0,.012,.026)])
for t in np.arange(.04,.85,.018):seams.append([crown(tt,math.pi+.015)+[0,0,.035] for tt in np.linspace(t,t+.009,3)])
tube('06_Felt_Tailoring_Stitches',seams,.018,WINE_THREAD,5)
inside=[]
for a in np.linspace(0,TAU,120,endpoint=False):inside.append([lining(.035,a+d)-[0,0,.035] for d in (0,.013,.025)])
tube('07_Interior_Lining_Stitches',inside,.017,WINE_THREAD,5)
# Rear adjustment laces emerge from the bound opening, with a restrained knot.
laces=[]
for side in (-1,1):
    points=[]
    for t in np.linspace(0,1,24):points.append([side*(.20+.70*t+.16*math.sin(t*math.pi)),RY+.18+.20*t,-.18-2.65*t+.12*math.sin(t*math.pi)])
    laces.append(points)
tube('08_Rear_Adjustment_Laces',laces,.062,THREAD,8)
tube('08b_Leather_Lace_Aglets',[[path[-4],path[-2],path[-1]] for path in laces],.085,LEATHER,10)
tube('09_Rear_Adjustment_Knot',[[[.36*math.sin(a),RY+.27+.12*math.cos(a),-.22+.23*math.cos(a)] for a in np.linspace(0,TAU,32,endpoint=False)]],.08,THREAD,8,True)
# A rigid badge in a raised leather backing, individually editable components.
at=-.56;tt=.38;q=crown(tt,at);qB=bv(q)
side=bv(crown(tt,at+.001))-bv(crown(tt,at-.001));rise=bv(crown(tt+.001,at))-bv(crown(tt-.001,at))
normal=rise.cross(side).normalized();up=(Vector((0,0,1))-normal*normal.z).normalized();right=up.cross(normal).normalized()
lift=0.
for xx in np.linspace(-1.45,1.45,7):
    for zz in np.linspace(-1.9,1.9,7):
        near,_,_,_=tree.find_nearest(qB+right*(xx*.01)+up*(zz*.01));lift=max(lift,(near-qB).dot(normal))
qB+=normal*(lift+.0003)
def badge_point(x,z,depth):return qB+right*(x*.01)+up*(z*.01)+normal*(depth*.01)
def badge_mesh(name,outline,depth,offset,mat,bevel):
    ps=[badge_point(x,z,offset+d) for d in (0,depth) for x,z in outline];n=len(outline);fs=[list(reversed(range(n))),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    ob=mesh(name,[(p.x*100,-p.y*100,p.z*100) for p in ps],fs,mat,smooth=False)
    if bevel:
        b=ob.modifiers.new('Rounded manufactured edges','BEVEL');b.width=bevel*.01;b.segments=3
        ob.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return ob
shield=[(-1.26,1.64),(1.26,1.64),(1.31,.40),(1.05,-.72),(0,-1.74),(-1.05,-.72),(-1.31,.40)]
outline=[(x*1.12,z*1.08) for x,z in shield];back=[];front=[]
for x,z in outline:
    near,nrm,_,_=tree.find_nearest(badge_point(x,z,0));back.append(near+normal*.0004);front.append(badge_point(x,z,.23))
n=len(outline);backing=mesh('10_Conforming_Leather_Crest_Backing',[(p.x*100,-p.y*100,p.z*100) for p in back+front],[list(reversed(range(n))),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)],LEATHER,smooth=False)
bevel=backing.modifiers.new('Soft backing edges','BEVEL');bevel.width=.00035;bevel.segments=3
badge_mesh('11_DarkSilver_Crest_Shield',shield,.15,.24,SILVER,.055)
badge_mesh('12_Recessed_Shield_Field',[(x*.87,z*.87) for x,z in shield],.018,.40,RECESS,.035)
# Raised wing chevrons and central spear are original ST6 identity geometry.
wing=[(.13,.58),(.48,.95),(1.02,1.16),(.94,.83),(.55,.60),(.88,.67),(.78,.39),(.45,.26),(.67,.30),(.53,.07),(.20,.20)]
for side in (-1,1):badge_mesh('13_Crest_Wing_'+('R' if side>0 else 'L'),[(side*x,z) for x,z in wing],.065,.44,SILVER,.025)
badge_mesh('14_Crest_Central_Spear',[(0,1.30),(.14,.66),(.06,.30),(.06,-.03),(-.06,-.03),(-.06,.30),(-.14,.66)],.075,.445,SILVER,.018)
font=bpy.data.fonts.load('C:/Windows/Fonts/seguisb.ttf')
def lettering(name,body,pos,size,mat,basis=None):
    curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.font=font;curve.align_x='CENTER';curve.align_y='CENTER';curve.size=size*.01;curve.extrude=.00024;curve.bevel_depth=.00006;curve.bevel_resolution=2;curve.resolution_u=12
    ob=bpy.data.objects.new(name,curve);MODEL.objects.link(ob);curve.materials.append(mat);ob.location=pos
    if basis:ob.rotation_euler=basis.to_euler()
    objects.append(ob);return ob
basis=Matrix((right,up,normal)).transposed()
lettering('15_Raised_ST6_Lettering','ST6',badge_point(0,-.62,.46),.78,SILVER,basis)
# Interior woven label follows the rear sweatband; its lettering faces inward.
labelpts=[]
for z in (-.39,.42):
    for x in np.linspace(-1.5,1.5,9):labelpts.append([float(x),(RY-.20)*math.sqrt(1-(x/(RX-.16))**2),z])
labelfaces=[[i,i+1,9+i+1,9+i] for i in range(8)]
tag=mesh('15b_Interior_Woven_ST6_Label',labelpts,labelfaces,LABEL);tag.modifiers.new('Label cloth thickness','SOLIDIFY').thickness=.00035
insidebasis=Matrix((Vector((-1,0,0)),Vector((0,0,1)),Vector((0,1,0)))).transposed()
lettering('15c_Interior_Label_Mark','ST6 / FIELD',bv((0,RY-.27,.02)),.25,THREAD,insidebasis)
# Shield perimeter stitching is on the backing, outside the metal edge.
crest_stitches=[]
poly=np.array([(x*1.065,z*1.035) for x,z in shield])
for a,b in zip(poly,np.roll(poly,-1,axis=0)):
    count=max(2,int(np.linalg.norm(b-a)/.16))
    for t in np.linspace(0,1,count,endpoint=False):
        path=[badge_point(*(a+(b-a)*u),.245) for u in (t,min(1,t+.28/count),min(1,t+.56/count))]
        crest_stitches.append([[v.x*100,-v.y*100,v.z*100] for v in path])
tube('16_Crest_HandStitches',crest_stitches,.017,THREAD,5)
# Two actual vent holes, finished with metal eyelets; cutters remain editable.
for k,a in enumerate((1.13,1.43)):
    p=bv(crown(.10,a));nrm=Vector((math.sin(a),math.cos(a),.05)).normalized()
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.00115,depth=.02,location=p)
    cutter=bpy.context.object;cutter.name='VentHole_Cutter_'+str(k);cutter.rotation_euler=nrm.to_track_quat('Z','Y').to_euler();move(cutter,CUT);cutter.hide_render=True;cutter.display_type='WIRE';cutter.hide_set(True)
    for target in (crown_ob,lining_ob):
        bo=target.modifiers.new('Real vent bore '+str(k),'BOOLEAN');bo.operation='DIFFERENCE';bo.solver='EXACT';bo.object=cutter
    bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=8,location=p+nrm*.00025,major_radius=.00175,minor_radius=.00055)
    rim=bpy.context.object;rim.name='17_Vent_Eyelet_'+str(k);rim.rotation_euler=nrm.to_track_quat('Z','Y').to_euler();move(rim,MODEL);rim.data.materials.append(SILVER)
    for f in rim.data.polygons:f.use_smooth=True
    objects.append(rim)
# The sweatband fold has an inner return rather than a paper-thin edge.
innerpaths=[[band(a,z,-.16) for a in np.linspace(0,TAU,256,endpoint=False)] for z in (-.55,.45)]
tube('18_Inner_Sweatband_Return',innerpaths,.055,LEATHER,7,True)
# Separate high-resolution surface source, with actual micro-relief displacement.
hi=crown_ob.copy();hi.data=crown_ob.data.copy();hi.name='HIGH_Felt_Crown_MicroRelief';HIGH.objects.link(hi)
hi.modifiers.clear()
sub=hi.modifiers.new('Sculpt surface subdivision','SUBSURF');sub.levels=2;sub.render_levels=2
tex=bpy.data.textures.new('ST6_Felt_Height_Source',type='IMAGE');tex.image=bpy.data.images.load(str(R/'Textures/T_ST6_BurgundyFelt_Height.png'));tex.image.colorspace_settings.name='Non-Color'
disp=hi.modifiers.new('Authored wool fibre micro-relief','DISPLACE');disp.texture=tex;disp.texture_coords='UV';disp.strength=.00030;disp.mid_level=.5
thickness=hi.modifiers.new('High felt thickness','SOLIDIFY');thickness.thickness=.0018;thickness.offset=-1
for cutter in CUT.objects:
    bo=hi.modifiers.new(cutter.name,'BOOLEAN');bo.operation='DIFFERENCE';bo.solver='EXACT';bo.object=cutter
# Native scalp is a hidden authoring reference, excluded from every export.
ref=mesh('REFERENCE_Jason_Head',hp-center,head['triangles'],material('REFERENCE_Neutral',(.18,.18,.18),.9),col=REF)
ref.display_type='WIRE';ref.hide_render=True
# One stable attachment bone; a beret does not need a cape/hat-tip chain.
arm=bpy.data.armatures.new('ST6_Beret_Attachment');rig=bpy.data.objects.new('ST6_Beret_Attachment',arm);MODEL.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
b=arm.edit_bones.new('HatRoot');b.head=(0,0,0);b.tail=(0,0,.04);bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for ob in objects:
    ob.parent=rig
    if ob.type=='MESH':
        g=ob.vertex_groups.new(name='HatRoot');g.add(list(range(len(ob.data.vertices))),1.,'REPLACE');a=ob.modifiers.new('Rigid head attachment','ARMATURE');a.object=rig
rig['item_id']='ue_st6_tactical_helmet';rig['production_stage']='Detailed model candidate; not integrated in Unreal';rig['palette']='Burgundy wool / black leather / dark silver';rig['author_source']='Tools/ST6Beret/author.py'
axes=np.array(head['bones']['head']['axes']).T;scale=np.linalg.norm(axes,axis=0);rot=axes/scale;quat=Matrix(rot.T.tolist()).to_quaternion();w,x,y,z=quat
fit=dict(location=np.linalg.solve(axes,center-np.array(head['bones']['head']['position'])).tolist(),rotation=[math.degrees(math.asin(np.clip(2*(z*x-w*y),-1,1))),math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))),math.degrees(math.atan2(-2*(w*x+y*z),1-2*(x*x+y*y)))],scale=(1/scale).tolist())
(R/'fit_candidate.json').write_text(json.dumps(dict(reference=str(HFILE),reference_sha256=hashlib.sha256(HFILE.read_bytes()).hexdigest(),native_head=head['source'],world_origin_cm=center.tolist(),opening_radii_cm=radii.tolist(),fits={'jason':fit},fit_tested=False),indent=2),encoding='utf-8')
# Editable text is retained in the master; evaluate a temporary export copy.
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
rig.select_set(True);bpy.context.view_layer.objects.active=crown_ob
scene.world=scene.world or bpy.data.worlds.new('ST6_StudioWorld');scene.world.color=(.10,.10,.10)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.45;area.spaces.active.region_3d.view_location=(0,0,.035)
bpy.ops.file.pack_all();blend=E/'ST6_Beret_Burgundy_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
originals=list(objects);exports=[];deps=bpy.context.evaluated_depsgraph_get();counts=[]
for ob in originals:
    evaluated=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(evaluated,depsgraph=deps,preserve_all_data_layers=True);copy=bpy.data.objects.new(ob.name+'_Export',me);MODEL.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copy.parent=rig
    group=copy.vertex_groups.get('HatRoot') or copy.vertex_groups.new(name='HatRoot');group.add(list(range(len(me.vertices))),1.,'REPLACE');mod=copy.modifiers.new('HeadAttachment','ARMATURE');mod.object=rig
    exports.append(copy);me.calc_loop_triangles();counts.append(dict(part=ob.name,vertices=len(me.vertices),triangles=len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
for ob in exports:ob.select_set(True)
rig.select_set(True);bpy.context.view_layer.objects.active=exports[0]
fbx=E/'SK_ST6_Beret_Burgundy.fbx';glb=E/'ST6_Beret_Burgundy.glb'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=False,export_animations=False,export_yup=True)
receipt=dict(completed=True,stage='detailed_model_authored',item_id='ue_st6_tactical_helmet',palette='burgundy felt, black leather, dark silver',blend=str(blend),fbx=str(fbx),glb=str(glb),parts=counts,triangles=sum(v['triangles'] for v in counts),vertices=sum(v['vertices'] for v in counts),high_source='HIGH_Felt_Crown_MicroRelief: subdivision 2 + real height displacement',original_texture_maps=4*len(json.loads((R/'textures.json').read_text())['maps']),unreal_imported=False,configuration_changed=False,preview_rendered=False,tested=False)
(R/'authored.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('ST6_BERET_AUTHORED',len(counts),receipt['triangles'],str(blend),flush=True)
