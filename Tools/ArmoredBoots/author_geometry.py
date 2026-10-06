"""Blender authoring of fitted grey-steel armored boots, with native Jason rig.

Macro plates, rolled lips, welt and fasteners are geometry. Fine grain is baked.
The concept supplies the visible design; concealed rear construction is authored.
"""
import json
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix,Vector

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArmoredBoots20261004'
bpy.ops.wm.read_factory_settings(use_empty=True)
native=json.loads((R/'base.json').read_text());bones=native['bones'];bone_ids={b['name']:b['index'] for b in bones}
objects=[];bindings={}

def unit(a):
    a=np.array(a,float);return a/max(np.linalg.norm(a),1e-10)

def profile(z):
    levels=[4,8,12,18,24,30,36,40]
    return np.array([np.interp(z,levels,v) for v in [
        [14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],
        [-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],
        [4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],
        [5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]])

def shaft_point(side,theta,z,offset=0,ridge=0):
    cx,cy,rx,ry=profile(z);s=1 if side=='l' else -1
    return np.array([s*(cx+(rx+offset)*math.sin(theta)),cy+(ry+offset)*math.cos(theta)+ridge*math.exp(-(theta/.19)**2),z])

def foot_point(side,u,v,z):
    s=1 if side=='l' else -1;angle=math.atan2(2.00392146,12.92064786)
    return np.array([s*(14.798+math.cos(angle)*u+math.sin(angle)*v),-2.45465-math.sin(angle)*u+math.cos(angle)*v,z])

def foot_shape(v):
    levels=[-7.0,-6.6,-5.5,-3,0,3,6,10,14,18,21,22.8,24]
    width=np.interp(v,levels,[.16,2.4,3.9,4.35,4.6,4.95,5.5,6.0,6.15,5.65,4.7,3.35,.18])
    top=np.interp(v,levels,[5.1,7.2,9.2,10.9,12.0,10.4,8.2,6.6,5.7,5.15,4.75,3.7,1.25])
    return width,top

def dorsal(side,v,theta,raise_cm=0):
    w,h=foot_shape(v);return foot_point(side,(w+raise_cm)*math.sin(theta),v,-.65+(h+.65)*(.5+.5*math.cos(theta))+raise_cm)

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return float(t*t*(3-2*t))

def skin(side,p,mode):
    if mode=='calf':return {bone_ids['calf_'+side]:1.}
    # Native articulation locations: ankle 8.42 cm; ball forward 13.08 cm.
    s=1 if side=='l' else -1;v=(s*p[0]-14.798)*.1533+(p[1]+2.45465)*.9882
    calf=smooth(8.4,16.5,p[2]) if mode=='flex' else 0.
    toe=smooth(10.6,16.3,v)*(1-calf)
    return {bone_ids['calf_'+side]:calf,bone_ids['ball_'+side]:toe,bone_ids['foot_'+side]:max(0,1-calf-toe)}

def mesh_object(name,vertices,faces,side,mode,slot,thickness=0,bevel=0):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in vertices],[],[list(reversed(f)) for f in faces]);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if thickness:
        mod=ob.modifiers.new('Closed forged thickness','SOLIDIFY');mod.thickness=thickness*.01;mod.offset=-1
        mod.use_even_offset=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    if bevel:
        mod=ob.modifiers.new('Rounded production bevel','BEVEL');mod.width=bevel*.01;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.5
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(52))
    uv=mesh.uv_layers.new(name='Physical25cm')
    for poly in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]));plane=[i for i in range(3) if i!=axis]
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[plane[0]]/.25,co[plane[1]]/.25)
    mesh.update();ob['material_slot']=slot;ob['side']=side;ob['weight_zone']=mode
    objects.append(ob);return ob

def patch(name,side,fn,nu,nv,mode='calf',slot=0,thickness=.18,bevel=.065):
    vertices=[fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)]
    faces=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;faces.append([a,a+1,a+nu+2,a+nu+1])
    # Projected armor patches are intended to face outwards. Correct winding
    # before thickness using the requested local outward vector.
    a,b,c=[np.array(vertices[i]) for i in faces[len(faces)//2][:3]]
    n=np.cross(b-a,c-a);mid=np.mean([a,b,c],axis=0)
    if slot==0 and (('Sabaton' in name or 'ToeCap' in name) and n[2]<0):faces=[list(reversed(f)) for f in faces]
    elif slot==0 and ('Shin' in name or 'AnkleLame' in name) and n[1]<0:faces=[list(reversed(f)) for f in faces]
    return mesh_object(name,vertices,faces,side,mode,slot,thickness,bevel)

def tube(name,path,radius,side,mode,slot=0,closed=False,sides=8):
    path=np.array(path);vertices=[];faces=[];count=len(path)
    for i,p in enumerate(path):
        tangent=unit(path[(i+1)%count]-path[(i-1)%count]) if closed else unit(path[min(i+1,count-1)]-path[max(0,i-1)])
        a=unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.9 else [0,1,0]));b=np.cross(tangent,a)
        vertices.extend(p+radius*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,2*math.pi,sides,endpoint=False))
    for i in range(count if closed else count-1):
        for j in range(sides):faces.append([i*sides+j,i*sides+(j+1)%sides,((i+1)%count)*sides+(j+1)%sides,((i+1)%count)*sides+j])
    if not closed:faces.extend([list(reversed(range(sides))),list(range((count-1)*sides,count*sides))])
    return mesh_object(name,vertices,faces,side,mode,slot)

def rivet(name,p,n,side,mode,r=.22):
    n=unit(n);a=unit(np.cross(n,[0,0,1] if abs(n[2])<.9 else [1,0,0]));b=np.cross(n,a)
    curve=[(0,.12),(.5,.11),(.88,.065),(1,.0),(1.07,-.045),(.65,-.07),(0,-.07)]
    verts=[np.array(p)+n*curve[0][1]];faces=[];sides=12
    for radius,h in curve[1:-1]:verts.extend(np.array(p)+n*h+r*radius*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,sides,endpoint=False))
    for i in range(sides):faces.append([0,1+i,1+(i+1)%sides])
    for j in range(len(curve)-3):
        for i in range(sides):
            a0=1+j*sides+i;b0=1+j*sides+(i+1)%sides;faces.append([a0,b0,b0+sides,a0+sides])
    end=len(verts);verts.append(np.array(p)+n*curve[-1][1]);start=1+(len(curve)-3)*sides
    for i in range(sides):faces.append([start+i,end,start+(i+1)%sides])
    mesh_object(name,verts,faces,side,mode,0)

def leather(side):
    # Continuous foot last with closed toe/heel, leather under the steel shells.
    verts=[];faces=[];ny=66;nr=40
    for v in np.linspace(-7,24,ny):
        w,h=foot_shape(v)
        for theta in np.linspace(0,math.tau,nr,endpoint=False):verts.append(foot_point(side,w*math.sin(theta),v,-.65+(h+.65)*(.5+.5*math.cos(theta))))
    for j in range(ny-1):
        for i in range(nr):faces.append([j*nr+i,j*nr+(i+1)%nr,(j+1)*nr+(i+1)%nr,(j+1)*nr+i])
    faces.extend([list(reversed(range(nr))),list(range((ny-1)*nr,ny*nr))])
    mesh_object('LeatherFoot_'+side,verts,faces,side,'foot',1)
    # Outer shaft, padded rim and inner wall share one watertight ring mesh.
    verts=[];faces=[];nr=64;rows=[]
    for z in np.linspace(8,38.1,28):rows.append((z,0.))
    rows.extend([(38.35,-.03),(38.52,-.18),(38.38,-.37)])
    rows.extend([(z,-.38) for z in np.linspace(38.1,8,27)])
    for z,offset in rows:
        for theta in np.linspace(0,math.tau,nr,endpoint=False):
            rim_lift=.48*max(0,math.cos(theta))*(smooth(34,38,z))
            wrinkle=.10*math.sin(z*1.8+math.sin(theta)*1.2)*math.exp(-((z-14)/5)**2)
            verts.append(shaft_point(side,theta,z+rim_lift,offset+wrinkle))
    for j in range(len(rows)):
        for i in range(nr):faces.append([j*nr+i,j*nr+(i+1)%nr,((j+1)%len(rows))*nr+(i+1)%nr,((j+1)%len(rows))*nr+i])
    mesh_object('LeatherShaftWithInnerWall_'+side,verts,faces,side,'flex',1)
    # Welt and sole retain a rounded anatomical foot outline and low heel.
    outline=[]
    for v in np.linspace(-6.9,23.9,78):outline.append((foot_shape(v)[0]+.48,v))
    for v in np.linspace(23.9,-6.9,78):outline.append((-foot_shape(v)[0]-.48,v))
    verts=[];faces=[]
    for z,offset in [(-2.55,-.05),(-2.48,.05),(-1.05,.10),(-.65,.03)]:
        verts.extend(foot_point(side,u+math.copysign(offset,u),v,z+max(0,v-18)*.025) for u,v in outline)
    n=len(outline)
    for j in range(3):
        for i in range(n):faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i])
    faces.extend([list(reversed(range(n))),list(range(3*n,4*n))])
    mesh_object('LayeredLeatherSole_'+side,verts,faces,side,'foot',2,bevel=.10)
    welt=[foot_point(side,u,v,-.72) for u,v in outline]
    tube('RaisedWelt_'+side,welt,.12,side,'foot',2,True)
    # A coarse visible welt seam uses individual short arcs, grouped in one mesh.
    verts=[];faces=[];loop=np.array(welt);lengths=np.linalg.norm(np.roll(loop,-1,axis=0)-loop,axis=1);total=sum(lengths)
    cumulative=np.r_[0,np.cumsum(lengths)]
    def at(t):
        t=t%total;i=min(len(loop)-1,np.searchsorted(cumulative,t,side='right')-1);f=(t-cumulative[i])/lengths[i]
        return loop[i]*(1-f)+loop[(i+1)%len(loop)]*f
    for distance in np.arange(0,total,.72):
        path=[at(distance+d)+[0,0,.04+.07*math.sin(t*math.pi)] for t,d in zip(np.linspace(0,1,4),np.linspace(0,.40,4))]
        start=len(verts)
        for j,p in enumerate(path):
            axis=unit(path[min(j+1,3)]-path[max(0,j-1)]);a=unit(np.cross(axis,[0,0,1]));b=np.cross(axis,a)
            verts.extend(p+.035*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,5,endpoint=False))
        for j in range(3):
            for i in range(5):faces.append([start+j*5+i,start+j*5+(i+1)%5,start+(j+1)*5+(i+1)%5,start+(j+1)*5+i])
    mesh_object('WeltStitch_'+side,verts,faces,side,'foot',3)

def greave(side):
    # Shin plate follows calf taper, with softly peaked top and rolled perimeter.
    def shin(u,v):
        theta=(u*2-1)*1.61;bottom=15.4+.7*abs(math.sin(theta));top=38.0+1.05*math.exp(-(theta/.42)**2)
        z=bottom+(top-bottom)*v
        return shaft_point(side,theta,z,.40,.32*(.85+.15*v))
    patch('ShinGreave_'+side,side,shin,40,32,thickness=.22,bevel=.085)
    rim=[shin(t,1) for t in np.linspace(0,1,49)]+[shin(1,t) for t in np.linspace(1,0,30)]+[shin(t,0) for t in np.linspace(1,0,49)]+[shin(0,t) for t in np.linspace(0,1,30)]
    tube('ShinRolledPerimeter_'+side,rim,.072,side,'calf',0,True)
    for i,(z0,z1,offset) in enumerate([(12.8,17.0,.67),(10.2,14.4,.77)]):
        def lame(u,v,z0=z0,z1=z1,offset=offset):
            theta=(u*2-1)*1.46;z=z0+(z1-z0)*v+.45*abs(math.sin(theta))
            return shaft_point(side,theta,z,offset,.10)
        patch('AnkleLame_%s_%d'%(side,i),side,lame,34,6,mode='flex',thickness=.18,bevel=.08)
        for theta in [-1.21,1.21]:
            p=shaft_point(side,theta,(z0+z1)/2+.40,offset+.18)
            rivet('AnkleLameRivet_%s_%d_%s'%(side,i,theta),p,[(1 if side=='l' else -1)*math.sin(theta),math.cos(theta),0],side,'flex')
    for theta in [-1.5,1.5]:
        for z in [18.3,25.0,34.7]:
            p=shaft_point(side,theta,z,.62);rivet('ShinRivet_%s_%s_%s'%(side,theta,z),p,[(1 if side=='l' else -1)*math.sin(theta),math.cos(theta),0],side,'calf')

def sabaton(side):
    for i,(start,end,offset) in enumerate([(2.0,6.8,.34),(5.0,9.8,.38),(8.0,12.6,.42),(10.9,15.4,.46),(13.7,18.3,.50)]):
        def plate(u,v,start=start,end=end,offset=offset):
            theta=(u*2-1)*1.90;station=start+(end-start)*v+.40*math.sin(theta)**2
            return dorsal(side,station,theta,offset)
        patch('Sabaton_%s_%02d'%(side,i),side,plate,34,6,mode='foot',thickness=.15,bevel=.07)
        for theta in [-1.70,1.70]:
            station=(start+end)/2+.35;p=dorsal(side,station,theta,offset+.13)
            s=1 if side=='l' else -1;rivet('SabatonRivet_%s_%s_%s'%(side,i,theta),p,[s*math.sin(theta),0,.45],side,'foot',.18)
    def toe(u,v):return dorsal(side,17.2+(23.96-17.2)*v,(u*2-1)*2.1,.30)
    patch('ToeCap_'+side,side,toe,38,16,mode='foot',thickness=.19,bevel=.08)

def ankle_guard(side):
    # Tear-shaped cheek plates protect both ankle bones, leaving front flex gap.
    for which in [-1,1]:
        verts=[];faces=[];n=44
        center=np.array([0.,0.]);outline=[]
        for t in np.linspace(0,math.tau,n,endpoint=False):
            outline.append([4.8*math.cos(t)*(1-.15*math.sin(t)),5.4*math.sin(t)])
        def project(v,z,rho):
            return foot_point(side,which*(4.9+.52*(1-rho*rho)),v-1.0,z+8.1)
        verts=[project(0,0,0)]
        for rho in [.2,.45,.7,.87,1.]:verts.extend(project(v*rho,z*rho,rho) for v,z in outline)
        for i in range(n):faces.append([0,1+i,1+(i+1)%n])
        for j in range(4):
            for i in range(n):
                a=1+j*n+i;b=1+j*n+(i+1)%n;faces.append([a,b,b+n,a+n])
        mesh_object('AnkleCheek_%s_%s'%(side,which),verts,faces,side,'flex',0,.18,.08)
        normal=[which*(1 if side=='l' else -1),0,0]
        for v,z in [(-2.7,1.2),(2.4,1.),(-1.4,-3.7)]:rivet('CheekRivet_%s_%s_%s'%(side,which,z),project(v,z,.8)+np.array(normal)*.10,normal,side,'flex',.19)
    # Rear heel counter is open above the flex line, unlike a calf-spanning shell.
    def counter(u,v):
        theta=math.pi+(u*2-1)*1.30;z=1.0+7.5*v
        return shaft_point(side,theta,z,.17)
    patch('HeelCounter_'+side,side,counter,28,10,mode='foot',thickness=.17,bevel=.08)

def straps(side):
    sign=1 if side=='l' else -1
    for index,z in enumerate([22.8,33.5]):
        # The leather strap wraps the back of the boot and meets an outer buckle.
        patch('RearStrap_%s_%d'%(side,index),side,
              lambda u,v:shaft_point(side,1.48+u*(math.tau-2.96),z+(v-.5)*2.15,.24),44,3,
              mode='calf',slot=1,thickness=.17,bevel=.065)
        def loc(y,dz,raised=0):
            return shaft_point(side,1.48+y/6.5,z+dz,.55+raised)
        contour=[]
        # Rounded rectangular buckle, with clear opening and solid tongue.
        for cx,cz,start in [(1.35,.90,0),(-1.35,.90,90),(-1.35,-.90,180),(1.35,-.90,270)]:
            for angle in np.linspace(start,start+90,6,endpoint=False):
                a=math.radians(angle);contour.append(loc(cx+.22*math.cos(a),cz+.22*math.sin(a),.13))
        tube('SideBuckle_%s_%d'%(side,index),contour,.14,side,'calf',0,True)
        tube('BuckleBar_%s_%d'%(side,index),[loc(0,dz,.16) for dz in np.linspace(-1.02,1.02,8)],.095,side,'calf')
        tube('BuckleTongue_%s_%d'%(side,index),[loc(y,.12,.22) for y in np.linspace(-.1,1.6,8)],.08,side,'calf')
        patch('StrapTip_%s_%d'%(side,index),side,lambda u,v:loc(-3.7+u*4.2,(v-.5)*1.65,-.13),12,3,
              mode='calf',slot=1,thickness=.18,bevel=.09)
        for y in [-3.05,-2.2]:rivet('StrapAnchor_%s_%d_%s'%(side,index,y),loc(y,0,.05),[sign,0,0],side,'calf',.19)

for side in ['l','r']:
    leather(side);greave(side);sabaton(side);ankle_guard(side);straps(side)

def valid_uv(uv,points):
    a,b=uv[1]-uv[0],uv[2]-uv[0]
    if abs(a[0]*b[1]-a[1]*b[0])>=1e-12:return uv
    tangent=unit(points[1]-points[0]);normal=unit(np.cross(points[1]-points[0],points[2]-points[0]));bitangent=np.cross(normal,tangent)
    local=points-points[0];return np.c_[local@tangent,local@bitangent]/25

data={k:[] for k in ['positions','triangles','weights','uv','normals','triangle_materials','parts']}
for ob in objects:
    mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
    start=len(data['positions']);points=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in mesh.vertices])
    data['positions'].extend(points.tolist());side=ob['side'];mode=ob['weight_zone'];slot=ob['material_slot']
    for p in points:
        ws=skin(side,p,mode);data['weights'].append([[i,w] for i,w in ws.items() if w>1e-7])
    count=0
    for tri in mesh.loop_triangles:
        p=points[list(tri.vertices)]
        if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))<1e-9:continue
        data['triangles'].append([start+i for i in tri.vertices]);mapped=np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops])
        data['uv'].append(valid_uv(mapped,p).tolist())
        data['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops])
        data['triangle_materials'].append(slot);count+=1
    data['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(points),triangles=count,material=slot,side=side,weight_zone=mode))
data.update(source=native['source'],skeleton=native['skeleton'],bones=bones,contract='ArmoredBoots20261004: native Jason cm coordinates, +Y forward, grey-steel greave and articulated sabaton')
(R/'Jason_ArmoredBoots.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')

# The same final geometry is retained with separate pieces and full native rig.
reflection=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('Jason_NativeReference');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    bone=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;bone.matrix=matrix;bone.length=.025
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[bones[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
def material(name,root,prefix):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    coord=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=4;l.new(coord.outputs['UV'],scale.inputs[0])
    for channel in ['BaseColor','Normal','ORM']:
        img=bpy.data.images.load(str(root/(prefix+channel+'.png')),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=img;l.new(scale.outputs[0],tex.inputs['Vector'])
        if channel=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='Normal':
            norm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],bs.inputs['Normal'])
        else:
            split=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],bs.inputs['Roughness']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
    return m
materials=[material('Forged grey steel',P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/Textures','T_ChainmailPants_Steel_'),
           material('Charcoal leather',R/'Textures','T_ArmoredBoots_Leather_'),material('Layered sole leather',R/'Textures','T_ArmoredBoots_Sole_')]
thread=bpy.data.materials.new('Waxed welt thread');thread.diffuse_color=(.14,.11,.073,1);thread.use_nodes=True
thread.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.14,.11,.073,1);thread.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.8;materials.append(thread)
for ob in objects:
    ob.data.materials.append(materials[ob['material_slot']]);ob.parent=rig;ob.modifiers.new('Native Jason binding','ARMATURE').object=rig
    groups={}
    for vi,v in enumerate(ob.data.vertices):
        p=np.array([v.co.x*100,-v.co.y*100,v.co.z*100])
        for bi,w in skin(ob['side'],p,ob['weight_zone']).items():
            if w<=1e-7:continue
            if bi not in groups:groups[bi]=ob.vertex_groups.new(name=bones[bi]['name'])
            groups[bi].add([vi],w,'REPLACE')
high=bpy.data.collections.new('BAKE_ONLY_SurfaceFields');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for label,source in [('Leather',R/'LeatherHighField.npz'),('Sole',R/'SoleHighField.npz'),('Steel',P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/SteelHighField.npz')]:
    field=np.load(source);h=field['height_cm'][::4,::4];span=float(field['span_cm']);n=len(h)
    verts=[(x/(n-1)*span*.01,y/(n-1)*span*.01,float(h[y,x])*.01) for y in range(n) for x in range(n)]
    faces=[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)]
    mesh=bpy.data.meshes.new('HIGH_'+label);mesh.from_pydata(verts,[],faces);ob=bpy.data.objects.new(mesh.name,mesh);high.objects.link(ob);ob['Source']=str(source);ob['Usage']='baking only, excluded from game JSON'
bpy.context.scene['Concept']='Concept_v1.png';bpy.context.scene['Units']='Blender metres, exported UE centimetres';bpy.context.scene['RuntimeTested']=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ArmoredBoots.blend'))
(R/'production.json').write_text(json.dumps(dict(vertices=len(data['positions']),triangles=len(data['triangles']),parts=len(data['parts']),
    material_slots=['ForgedSteel','CharcoalLeather','LayeredSole','WaxedThread'],native_source=native['source'],
    source_concept='Concept_v1.png',rear_geometry='authored inference from single reference',runtime_tested=False),indent=2))
print('ARMORED_BOOTS_AUTHORED',len(data['positions']),len(data['triangles']),flush=True)
