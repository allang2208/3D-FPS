"""Repair the existing face and comb a scalp-constrained, swept-back black bun."""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/ChapelNun20261115/HeadQualityR2'
O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
old=json.loads((P/'SourceAssets/ChapelNun20261115/ProductionR1/Authored/head.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/ChapelNun20261115/ProductionR1/Authored/Nun_Head_Hair.blend'))
for obj in list(bpy.data.objects):
    if obj.type=='CURVE':bpy.data.objects.remove(obj,do_unlink=True)
head=bpy.data.objects['SK_NunHead'];me=head.data
# Remove only sub-millimetre spikes beneath the lip; retain the facial silhouette.
sys.path.insert(0,str(P/'Tools/ChapelNun'))
from lip_continuity import refine
refined_lip_count=refine(me,old)
for f in me.polygons:
    if f.material_index!=0:continue
    c=f.center
    if ((abs(c.x)-3.05)/1.45)**2+((c.z-157.43)/.48)**2<1 and c.y>6.6:
        f.material_index=2
    elif (c.x/2.38)**2+((c.z-150.76)/.68)**2<1 and c.y>8.0:
        f.material_index=3
for _ in range(3):me.materials.append(me.materials[0])
# Join maps material identity; distinct slots must not share the preview material object.
for i in range(1,5):
    preview=me.materials[0].copy();preview.name='NunSlot_'+str(i);me.materials[i]=preview
verts=[v.co.copy() for v in me.vertices]
bvh=BVHTree.FromPolygons(verts,[tuple(f.vertices) for f in me.polygons])
tree=KDTree(len(verts))
for i,p in enumerate(verts):tree.insert(p,i)
tree.balance()
center=Vector((0,.1,158.9));rng=random.Random(16112026)
def limit(theta):
    a=abs(theta)
    # Forehead, temples, above the ears, then the nape; radians on the actual head.
    knots=[(0.,.92),(.65,1.00),(1.1,1.22),(1.65,1.48),(2.2,1.84),(math.pi,2.06)]
    for (a0,b0),(a1,b1) in zip(knots,knots[1:]):
        if a<=a1:
            t=(a-a0)/(a1-a0);t=t*t*(3-2*t);return b0+(b1-b0)*t
    return 2.06
def direction(theta,phi):return Vector((math.sin(phi)*math.sin(theta),math.sin(phi)*math.cos(theta),math.cos(phi)))
def project(d,lift=.06):
    d=d.normalized();p,n,idx,dist=bvh.ray_cast(center,d,40)
    if p is None:raise RuntimeError('Missing scalp intersection')
    return p+d*lift
def constrained(d,lift):
    theta=math.atan2(d.x,d.y);phi=math.acos(max(-1,min(1,d.z)))
    return project(direction(theta,min(phi,limit(theta)-.015)),lift)
def nearest_weights(p):
    _,i,_=tree.find(p)
    return [[g.group,g.weight] for g in me.vertices[i].groups]
# A fitted, feathered root foundation prevents pale scalp holes between real strands.
# It is restricted to the hair-bearing surface and uses the same head weights.
cap_p=[];cap_t=[];cap_uv=[];cap_w=[];A=256;B=72
for j in range(B+1):
    v=j/B
    for i in range(A+1):
        theta=-math.pi+math.tau*i/A;phi=max(.002,v*limit(theta))
        p=project(direction(theta,phi),.018)
        cap_p.append(list(p));cap_w.append(nearest_weights(p))
for j in range(B):
    for i in range(A):
        a=j*(A+1)+i;b=a+1;c=a+A+1;d=c+1
        for tri in ((a,b,c),(b,d,c)):
            cap_t.append(tri);cap_uv.append([(k%(A+1)/A,k//(A+1)/B) for k in tri])
cap=bpy.data.meshes.new('ScalpFoundation');cap.from_pydata(cap_p,[],cap_t);cap.uv_layers.new(name='UVMap')
for f,uv in zip(cap.polygons,cap_uv):
    f.material_index=4;f.use_smooth=True
    for li,xy in zip(f.loop_indices,uv):cap.uv_layers[0].data[li].uv=xy
obj=bpy.data.objects.new('ScalpFoundation',cap);bpy.context.collection.objects.link(obj)
for bone in old['bones']:obj.vertex_groups.new(name=bone['name'])
for i,weights in enumerate(cap_w):
    for bi,w in weights:obj.vertex_groups[bi].add([i],w,'REPLACE')
for mat in me.materials:cap.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);obj.select_set(True);bpy.context.view_layer.objects.active=head;bpy.ops.object.join()
me=head.data;me.calc_loop_triangles()
data={k:old[k] for k in ('binding_source','skeleton','bones')}
data.update(positions=[list(v.co) for v in me.vertices],weights=[[[g.group,g.weight] for g in v.groups] for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=['NunSkin','NativeNeck','EyeSurface','Lips','ScalpFoundation'])
for tri in me.loop_triangles:
    order=list(tri.loops)[::-1]
    data['triangles'].append(list(tri.vertices)[::-1]);data['uv'].append([[me.uv_layers.active.data[k].uv.x,1-me.uv_layers.active.data[k].uv.y] for k in order]);data['normals'].append([list(me.corner_normals[k].vector) for k in order]);data['triangle_materials'].append(tri.material_index)
(O/'head.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
diagnosis={'old_issue':'Azimuth fan exposed the crown and interpolated hair below the forehead boundary.','scalp_foundation_triangles':len(cap_t),'lip_vertices_refined':refined_lip_count,'source_curves':{}}
def groom(name,count,loose=False):
    curves=bpy.data.curves.new(name,'CURVE');curves.dimensions='3D';curves.resolution_u=1
    obj=bpy.data.objects.new(name,curves);bpy.context.collection.objects.link(obj);obj['groom_group_id']=0;obj['groom_guide']=0
    for k in range(count):
        theta=rng.uniform(-math.pi,math.pi);phi=math.acos(rng.uniform(math.cos(limit(theta)-.025),1))
        rootdir=direction(theta,phi);phase=rng.uniform(0,math.tau)
        if loose:
            side=-1 if k%2 else 1;theta=side*rng.uniform(1.25,2.95);phi=limit(theta)-rng.uniform(.03,.18)
            root=project(direction(theta,phi),.08);tangent=Vector((side*.18,-.55,-.5)).normalized();length=rng.uniform(.8,3.6)
            points=[root+tangent*(length*j/23)+Vector((.12*math.sin(phase+j/8)*j/23,0,-.15*(j/23)**2)) for j in range(24)]
        else:
            endtheta=(1 if rootdir.x>=0 else -1)*(math.pi-rng.uniform(.0,.20));endphi=rng.uniform(1.94,2.02)
            enddir=direction(endtheta,endphi);points=[];angle0=rng.uniform(0,math.tau);radius=rng.uniform(1.35,3.1)
            for j in range(64):
                t=j/63
                if t<=.74:
                    u=t/.74
                    d=rootdir.slerp(enddir,u)
                    lift=.065+.23*math.sin(math.pi*u)+.028*math.sin(phase+u*17)*math.sin(math.pi*u)
                    point=constrained(d,lift)
                else:
                    u=(t-.74)/.26;a=angle0+u*math.tau*1.2
                    coil=Vector((radius*math.sin(a),-11.0-1.3*math.sin(math.pi*u),152.0+radius*.72*math.cos(a)))
                    start=constrained(enddir,.07);blend=min(1,u/.28);blend=blend*blend*(3-2*blend);point=start.lerp(coil,blend)
                    # The bun must also remain outside the back of the cranium.
                    delta=point-center;surface=project(delta,.08)
                    if delta.length<(surface-center).length:point=surface
                points.append(point)
        spline=curves.splines.new('POLY');spline.points.add(len(points)-1)
        spline.points.foreach_set('co',[c for pt in points for c in (*pt,1.)])
        for j,pt in enumerate(spline.points):pt.radius=.0055*(1-.7*(j/(len(points)-1))**4)
    diagnosis['source_curves'][name]=count
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.wm.alembic_export(filepath=str(O/(name+'.abc')),start=1,end=1,selected=True,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.)
    print('QUALITY_GROOM_SAVED',name,count,flush=True)
    return obj
groom('Nun_LowBun_Core_R2',52000);groom('Nun_LowBun_Loose_R2',1600,True)
# Store editable materials for the same source-model visual checks.
skin=me.materials[0];nt=skin.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.55
source=P/'SourceAssets/ChapelNun20261115/MeshyHeadR1/Source'
tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(source/'NunHead_R1_M00_normal.png'));tex.image.colorspace_settings.name='Non-Color'
nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.7;nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
for index,name,rough in [(2,'Nun_EyeSurface',.22),(3,'Nun_Lips',.44)]:
    mat=skin.copy();mat.name=name;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=rough;me.materials[index]=mat
    if index==2:
        for link in list(bs.inputs['Normal'].links):mat.node_tree.links.remove(link)
        bs.inputs['Subsurface Weight'].default_value=.1
capmat=bpy.data.materials.new('Nun_ScalpFoundation');capmat.use_nodes=True;bs=capmat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.009,.008,.007,1);bs.inputs['Roughness'].default_value=.65;me.materials[4]=capmat
neck=bpy.data.materials.new('NativeNeckPreview');neck.use_nodes=True;bs=neck.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.42,.27,.19,1);bs.inputs['Roughness'].default_value=.58;me.materials[1]=neck
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
(O/'authoring.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8')
print('HEAD_QUALITY_AUTHORED',flush=True)
import runpy
runpy.run_path(str(P/'Tools/ChapelNun/repair_head_orientation.py'),run_name='__main__')
