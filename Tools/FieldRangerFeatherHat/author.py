"""Detailed boat hat, lining, sewn leather and articulated feather, in centimetres.

Source coordinates are Jason reference coordinates: +Y forward, +X wearer left.
Blender uses (X,-Y,Z) in metres. Runtime fitting resolves the FBX import basis.
"""
import copy,importlib.util,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerFeatherHat20261021'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import vertex,face,finish,unit,smooth,norm_weights
SLOTS=['RangerCloth','RangerLeather','RangerLining','RangerBrass','RangerThread','RangerFeather','RangerQuill']
ROOT={'HatRoot':1.};TAU=math.tau
d=dict(profile='FieldRangerFeatherHat',positions=[],weights=[],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=SLOTS,
 contract='Approved Concept01 detailed boat cap; fitted Jason scalp opening; closed cloth/leather shells; feather vane and shaft share three-bone local spring')
parts=[]
def part(name,fn):
    start=len(d['triangles']);fn();parts.append(dict(name=name,first_triangle=start,triangle_count=len(d['triangles'])-start))
def tube(points,radius,slot,weight=ROOT,closed=False,sides=8):
    points=np.asarray(points);count=len(points);rings=[];distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    for i,p in enumerate(points):
        tangent=unit(points[(i+1)%count]-points[(i-1)%count]) if closed else unit(points[min(i+1,count-1)]-points[max(0,i-1)])
        a=unit(np.cross(tangent,[1,0,0] if abs(tangent[0])<.8 else [0,0,1]));b=np.cross(tangent,a)
        r=radius(i/(count-1)) if callable(radius) else radius
        rings.append([vertex(d,p+r*(a*math.cos(t)+b*math.sin(t)),weight(p) if callable(weight) else weight) for t in np.linspace(0,TAU,sides,endpoint=False)])
    for i in range(count if closed else count-1):
        end=(i+1)%count;length=distance[i]+np.linalg.norm(points[end]-points[i]);r=radius(i/(count-1)) if callable(radius) else radius
        for k in range(sides):
            ids=[rings[i][k],rings[i][(k+1)%sides],rings[end][(k+1)%sides],rings[end][k]]
            uv=[[distance[i]/8,k*TAU*r/sides/8],[distance[i]/8,(k+1)*TAU*r/sides/8],[length/8,(k+1)*TAU*r/sides/8],[length/8,k*TAU*r/sides/8]]
            for tri in ((0,1,2),(0,2,3)):
                mid=np.mean([d['positions'][ids[j]] for j in tri],axis=0);out=unit(mid-(points[i]+points[end])*.5)
                face(d,[ids[j] for j in tri],slot,[uv[j] for j in tri],out)
    if not closed:
        for end in (0,count-1):
            center=vertex(d,points[end],weight(points[end]) if callable(weight) else weight);out=unit(points[end]-points[1 if end==0 else end-1])
            for k in range(sides):
                t,s=TAU*k/sides,TAU*(k+1)/sides
                face(d,[center,rings[end][k],rings[end][(k+1)%sides]],slot,[[.5,.5],[.5+.5*math.cos(t),.5+.5*math.sin(t)],[.5+.5*math.cos(s),.5+.5*math.sin(s)]],out)
def shell(rows,segments,pos,normal,uv,outer,inner,thickness,weight=lambda t,a:ROOT,cap=False):
    rings=[]
    for inset in (0,thickness):
        grid=[]
        for t in rows:grid.append([vertex(d,pos(t,TAU*i/segments)-normal(t,TAU*i/segments)*inset,weight(t,TAU*i/segments)) for i in range(segments)])
        rings.append(grid)
    for inside,grid in enumerate(rings):
        for j in range(len(rows)-1):
            for i in range(segments):
                k=(i+1)%segments;ids=[grid[j][i],grid[j][k],grid[j+1][k],grid[j+1][i]]
                tex=[uv(rows[j],i/segments),uv(rows[j],(i+1)/segments),uv(rows[j+1],(i+1)/segments),uv(rows[j+1],i/segments)]
                n=normal((rows[j]+rows[j+1])*.5,TAU*(i+.5)/segments)*(-1 if inside else 1)
                for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],inner if inside else outer,[tex[k] for k in tri],n)
    for j in ((0,) if cap else (0,len(rows)-1)):
        for i in range(segments):
            k=(i+1)%segments;ids=[rings[0][j][i],rings[1][j][i],rings[1][j][k],rings[0][j][k]]
            tangent=pos(rows[1] if j==0 else rows[-2],TAU*i/segments)-pos(rows[j],TAU*i/segments)
            out=-unit(tangent)
            length=np.linalg.norm(np.array(d['positions'][ids[0]])-d['positions'][ids[3]])
            uv_edge=[[0,0],[0,thickness/8],[length/8,thickness/8],[length/8,0]]
            for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],outer,[uv_edge[k] for k in tri],out)
    return rings
head=json.loads((P/'SourceAssets/FieldHat20261019/native_head_jason.json').read_text())
hp=np.array(head['positions']);z0=float(hp[:,2].max())-7.2;sample=hp[abs(hp[:,2]-z0)<1.5]
center=(sample.min(0)+sample.max(0))*.5;center[2]=z0
xy=sample[:,:2]-center[:2];radius=(sample[:,:2].max(0)-sample[:,:2].min(0))*.5+.45
radius*=max(1.,float(np.sqrt(((xy/radius)**2).sum(1)).max())+.02)
RX,RY=radius+.52;H=11.3
def crown(t,a):
    ang=t*math.pi*.5;cs=math.cos(ang);s=math.sin(ang)
    ripple=(.035*math.sin(a*7+1.3)+.025*math.sin(a*11-2*t))*math.sin(math.pi*t)**2
    x=RX*cs*math.sin(a);y=RY*cs*math.cos(a)
    z=H*s-.7*math.sin(2*ang)**2*abs(math.sin(a))
    return np.array([x,y,z])+np.array([math.sin(a),math.cos(a),.2])*ripple
def crown_n(t,a):
    da=crown(t,a+.0001)-crown(t,a-.0001);dt=crown(min(.99999,t+.0001),a)-crown(max(0,t-.0001),a)
    n=unit(np.cross(dt,da))
    return n if n@np.array([math.sin(a),math.cos(a),.7])>0 else -n
def make_crown():
    rows=np.linspace(0,.992,49);rings=shell(rows,192,crown,crown_n,lambda t,u:[u*TAU*(RX+RY)*.5/8,t*H*1.6/8],0,2,.23,cap=True)
    # Tiny last ring closes to one vertex per surface, preserving the open head entrance.
    for inner in (0,1):
        tip=vertex(d,[0,0,H-(.23 if inner else 0)],ROOT)
        for i in range(192):
            k=(i+1)%192
            face(d,[rings[inner][-1][i],rings[inner][-1][k],tip],2 if inner else 0,[[i/192,.98],[(i+1)/192,.98],[(i+.5)/192,1]],(0,0,-1 if inner else 1))
part('01_Crown_Cloth_And_Lining',make_crown)
def brim(u,a):
    base=np.array([(RX-.12)*math.sin(a),(RY-.12)*math.cos(a),.38])
    front=max(math.cos(a),0);back=max(-math.cos(a),0)
    top=np.array([(RX+.85)*math.sin(a),(RY+5.5*front+2.7*back)*math.cos(a),.85+4.65*abs(math.sin(a))**.85+.65*back])
    p=base*(1-u)+top*u
    p+=np.array([math.sin(a),math.cos(a),0])*(.95*math.sin(math.pi*u))
    p[2]+=.10*math.sin(a*3+.6)*math.sin(math.pi*u)
    return p
def brim_n(u,a):
    da=brim(u,a+.0001)-brim(u,a-.0001);du=brim(min(1,u+.0001),a)-brim(max(0,u-.0001),a)
    return unit(np.cross(du,da))
part('02_Raised_Boat_Brim',lambda:shell(np.linspace(0,1,19),224,brim,brim_n,lambda u,a:[a*TAU*(RX+RY)*.5/8,u*6/8],0,2,.20))
def band(t,a,inner=False):
    p=crown(t/H,a);return p+crown_n(t/H,a)*(.18 if not inner else -.30)
part('03_Leather_Base_Band',lambda:shell(np.linspace(.05,2.0,8),224,band,lambda t,a:crown_n(t/H,a),lambda z,a:[a*TAU*(RX+RY)*.5/8,z/8],1,1,.14))
part('04_Leather_Opening_Sweatband',lambda:shell(np.linspace(.05,2.3,8),192,lambda t,a:band(t,a,True),lambda t,a:-crown_n(t/H,a),lambda z,a:[a*TAU*(RX+RY)*.5/8,z/8],1,1,.14))
part('05_Leather_Rolled_Brim_Edge',lambda:tube([brim(1,a)-brim_n(1,a)*.08 for a in np.linspace(0,TAU,448,endpoint=False)],.13,1,closed=True,sides=10))
part('06_Band_Folded_Welts',lambda:[tube([band(z,a) for a in np.linspace(0,TAU,320,endpoint=False)],.065,1,closed=True,sides=6) for z in (.12,1.94)])
def stitch_line(path,spacing=.40,length=.23,radius=.018):
    path=np.array(path);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    def at(s):return np.array([np.interp(s,arc,path[:,k]) for k in range(3)])
    for s in np.arange(.06,arc[-1]-length,spacing):
        a,b=at(s),at(s+length);mid=(a+b)*.5
        tube([a,mid+unit(mid-np.array([0,0,mid[2]-2]))*.018,b],radius,4,sides=5)
def stitches():
    for z in (.35,1.7):stitch_line([band(z,a)+crown_n(z/H,a)*.025 for a in np.linspace(0,TAU,641)],.36,.22)
    stitch_line([brim(.93,a)+brim_n(.93,a)*.025 for a in np.linspace(0,TAU,641)],.36,.21)
    for xsign in (-1,1):
        path=[]
        for t in np.linspace(.03,.995,170):
            p=crown(t,0)+crown_n(t,0)*.035;p[0]+=xsign*.12;path.append(p)
        for t in np.linspace(.995,.03,170):
            p=crown(t,math.pi)+crown_n(t,math.pi)*.035;p[0]+=xsign*.12;path.append(p)
        stitch_line(path,.32,.19,.016)
part('07_Individual_Double_Stitching',stitches)
base=np.array([RX+1.1,-1.35,4.15]);axis=unit(np.array([.025,-.84,.54]));vane_axis=unit(np.array([0,axis[2],-axis[1]]));vane_normal=unit(np.cross(axis,vane_axis))
def stem(t):return base+axis*(19*t)+np.array([.48*t*t,-.6*t*t,.80*t*t])
def fweight(t):
    names=['HatRoot','FeatherBase','FeatherMid','FeatherTip'];knots=[.06,.22,.55,.88]
    if t<=knots[0]:return ROOT.copy()
    if t>=knots[-1]:return {'FeatherTip':1.}
    j=next(i for i in range(3) if knots[i]<=t<=knots[i+1]);w=float(smooth((t-knots[j])/(knots[j+1]-knots[j])))
    return {names[j]:1-w,names[j+1]:w}
def weight_at(p):return fweight(float(np.clip((p-base)@axis/19,0,1)))
def width(t,sign):
    u=np.clip((t-.115)/.885,0,1);w=2.2*math.sin(math.pi*u)**.78
    notch=1-.10*max(0,math.sin(t*TAU*31+.8*sign))**18-.045*max(0,math.sin(t*TAU*53+sign))**20
    return w*(1 if sign>0 else .79)*notch
def feather_point(t,s,back=False):
    w=width(t,1 if s>=0 else -1);v=abs(s)
    return stem(t)+vane_axis*s*w+axis*(.8*v*w/2.2)+vane_normal*(.13*math.sin(math.pi*t)*v*v+(-.018 if back else .018))
def feather():
    nt,nw=170,20;rows=np.linspace(.116,.999,nt);grids=[]
    for back in (False,True):
        grid=[]
        for t in rows:grid.append([vertex(d,feather_point(t,s,back),fweight(t)) for s in np.linspace(-1,1,nw+1)])
        grids.append(grid)
        for i in range(nt-1):
            for j in range(nw):
                ids=[grid[i][j],grid[i][j+1],grid[i+1][j+1],grid[i+1][j]]
                tex=[[j/nw,rows[i]],[(j+1)/nw,rows[i]],[(j+1)/nw,rows[i+1]],[j/nw,rows[i+1]]]
                for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],5,[tex[k] for k in tri],-vane_normal if back else vane_normal)
    for j in (0,nw):
        for i in range(nt-1):
            ids=[grids[0][i][j],grids[1][i][j],grids[1][i+1][j],grids[0][i+1][j]]
            for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],5,[[j/nw,rows[i]],[j/nw+.001,rows[i]],[j/nw,rows[i+1]]],vane_axis*(1 if j else -1))
    for i in (0,nt-1):
        for j in range(nw):
            ids=[grids[0][i][j],grids[0][i][j+1],grids[1][i][j+1],grids[1][i][j]]
            for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],5,[[j/nw,rows[i]],[(j+1)/nw,rows[i]],[(j+1)/nw,rows[i]+.001]],axis*(1 if i else -1))
part('08_Feather_Closed_Vane',feather)
part('09_Feather_Quill_Rachis',lambda:tube([stem(t) for t in np.linspace(0,1,180)],lambda t:.12*(1-t)**.8+.012,6,weight_at,sides=12))
def barbs():
    for sign in (-1,1):
        for t in np.linspace(.16,.96,105):
            for back in (False,True):
                path=[feather_point(t,s*sign,back)+vane_normal*(-.009 if back else .009) for s in np.linspace(.035,.97,6)]
                first=len(d['triangles']);tube(path,lambda q:.010*(1-q)+.0035,5,weight_at,sides=4)
                for fi in range(first,len(d['triangles'])):
                    d['uv'][fi]=[[float(np.clip(.5+((np.array(d['positions'][i])-stem(t))@vane_axis)/max(width(t,sign)*2,.01),0,1)),float(t)] for i in d['triangles'][fi]]
part('10_Feather_Raised_Barb_Ridges',barbs)
def ferrule():
    # Real hollow tube: upper opening surrounds the stem, with rolled lips.
    aa=vane_axis;bb=vane_normal;origin=stem(.025)
    def pos(z,a):return origin+axis*z+(.34+.025*math.cos(z*math.pi/1.8))*(aa*math.cos(a)+bb*math.sin(a))
    def normal(z,a):return aa*math.cos(a)+bb*math.sin(a)
    shell(np.linspace(-.25,1.65,12),48,pos,normal,lambda z,a:[a*.30,z/8],3,3,.09)
    for z in (-.20,1.58):tube([pos(z,a) for a in np.linspace(0,TAU,72,endpoint=False)],.045,3,closed=True,sides=8)
    for step in (-.65,.65):
        center=origin+np.array([-.07,step,-.32])
        tube([center-np.array([.15,0,0]),center+np.array([.16,0,0])],.29,3,sides=32)
    # Bent leather keeper ties the socket into the band without loose ends.
    path=[origin+np.array([-.19,-.82+1.64*t,-.36+.16*math.sin(math.pi*t)]) for t in np.linspace(0,1,35)]
    tube(path,.14,1,sides=8)
part('11_Hollow_Brass_Feather_Socket',ferrule)
names=['HatRoot','FeatherBase','FeatherMid','FeatherTip','FitFront','FitLeft']
positions=[np.zeros(3),stem(.10),stem(.42),stem(.75),np.array([0.,6.,0]),np.array([6.,0.,0])]
parents=[-1,0,1,2,0,0]
d['bones']={name:dict(index=i,parent=parents[i],position=p.tolist(),axes=np.eye(3).tolist()) for i,(name,p) in enumerate(zip(names,positions))}
finish(d);d['parts']=parts
(R/'Authored/hat.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module('ranger_head_fit','Tools/FieldHat/author_boonie.py');old.SRC=R;old.save_fit(head,d,center,z0,*radius)
def materials():
    def material(name,family=None,colour=(.1,.1,.1),rough=.75,metal=0):
        m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links;bs=ns['Principled BSDF'];bs.inputs['Base Color'].default_value=(*colour,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        if family:
            folder=R/'Textures' if family=='Feather' else P/'SourceAssets/FieldRangerTop20261020/Textures'
            for ch in ('BaseColor','Normal','ORM'):
                tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(folder/(family+'_'+ch+'.png')),check_existing=True);tex.image.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
                if ch=='BaseColor':ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
                elif ch=='Normal':n=ns.new('ShaderNodeNormalMap');ls.new(tex.outputs['Color'],n.inputs['Color']);ls.new(n.outputs[0],bs.inputs['Normal'])
                else:split=ns.new('ShaderNodeSeparateColor');ls.new(tex.outputs['Color'],split.inputs[0]);ls.new(split.outputs['Green'],bs.inputs['Roughness']);ls.new(split.outputs['Blue'],bs.inputs['Metallic'])
            if family=='Feather':bs.inputs['Anisotropic'].default_value=.35
            if family=='RangerTwill':bs.inputs['Sheen Weight'].default_value=.15
        return m
    return [material('RangerCloth','RangerTwill'),material('RangerLeather','RangerLeather'),material('RangerLining',colour=(.027,.032,.022),rough=.88),material('RangerBrass',colour=(.22,.145,.062),rough=.48,metal=.9),material('RangerThread',colour=(.14,.095,.052),rough=.82),material('RangerFeather','Feather'),material('RangerQuill',colour=(.36,.27,.16),rough=.48)]
old.make_materials=materials
old.build_blender(d,names)
# Rename the existing reusable export, keeping new assets isolated in this family.
fbx=R/'Exports/FieldHat.fbx';target=R/'Exports/FieldRangerFeatherHat.fbx'
target.write_bytes(fbx.read_bytes())
obj=bpy.data.objects['FieldHat'];obj.name='FieldRangerFeatherHat_GameLOD0';rig=obj.parent
collection=bpy.data.collections.new('EDITABLE_Separate_Pattern_Pieces');bpy.context.scene.collection.children.link(collection)
collection.hide_render=True;collection.hide_viewport=True
for part_info in parts:
    start=part_info['first_triangle'];end=start+part_info['triangle_count'];faces=d['triangles'][start:end];used=sorted(set(v for f in faces for v in f));remap={v:i for i,v in enumerate(used)}
    mesh=bpy.data.meshes.new(part_info['name']);mesh.from_pydata([(d['positions'][i][0]*.01,-d['positions'][i][1]*.01,d['positions'][i][2]*.01) for i in used],[],[[remap[v] for v in f] for f in faces]);mesh.update();piece=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(piece)
    for m in obj.data.materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='PhysicalGarmentUV')
    for j,poly in enumerate(mesh.polygons):
        fi=start+j;poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for k,li in enumerate(poly.loop_indices):u,v=d['uv'][fi][k];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for ns in d['normals'][start:end] for x,y,z in ns])
    groups={n:piece.vertex_groups.new(name=n) for n in names}
    for j,i in enumerate(used):
        for n,w in d['weights'][i].items():groups[n].add([j],w,'REPLACE')
    piece.parent=rig;piece.modifiers.new('Shared native hat rig','ARMATURE').object=rig
high=bpy.data.collections.new('HIGH_Physical_Surface_Bake_Sources');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for family,folder,span in [('RangerTwill',P/'SourceAssets/FieldRangerTop20261020/Textures',(8,8)),('RangerLeather',P/'SourceAssets/FieldRangerTop20261020/Textures',(8,8)),('Feather',R/'Textures',(5,19))]:
    h=np.load(folder/(family+'_height_cm.npy'))[::4,::4];ny,nx=h.shape;mesh=bpy.data.meshes.new('HIGH_'+family)
    mesh.from_pydata([(x/(nx-1)*span[0]*.01,y/(ny-1)*span[1]*.01,float(h[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)])
    ob=bpy.data.objects.new(mesh.name,mesh);high.objects.link(ob);ob['Usage']='Actual physical relief source; exclude from game FBX'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/FieldRangerFeatherHat_Detailed.blend'))
icon=module('ranger_hat_icon','Tools/FieldHat/render_icon.py');icon.OUT=R;icon.KEY='ue_ranger_feather_hat';icon.FAMILIES={icon.KEY:'FieldRangerFeatherHat20261021'}
item=dict(grid_w=2,grid_h=2,ue_icon='Icons/FieldRangerFeatherHat20261021/ue_ranger_feather_hat.png')
icon.render_current(icon.KEY,obj,item,camera_offset=(2.5,-2.7,1.6))
(R/'authored.json').write_text(json.dumps(dict(completed=True,triangles=len(d['triangles']),vertices=len(d['positions']),parts=parts,bones=names,
 fbx=str(target),blend=str(R/'Exports/FieldRangerFeatherHat_Detailed.blend'),head_source=head['source'],
 crown_height_cm=H,opening_radii_cm=radius.tolist(),feather_length_cm=19,icon=str(R/'ue_ranger_feather_hat.png'),runtime_tested=False),indent=2),encoding='utf-8')
print('RANGER_FEATHER_HAT_AUTHORED',len(d['triangles']),flush=True)
