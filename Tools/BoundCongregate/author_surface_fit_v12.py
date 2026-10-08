"""Follow the actual forked tip topology; fit garments to anatomical support."""
from pathlib import Path
import bpy,bmesh,numpy as np,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'SurfaceFitV12';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'FullWhipV10/BoundCongregate_FullWhipV10.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=bpy.data.objects['BC_Flesh']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
def smooth(a,b,x):
    t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
def weights(ob,v):return {ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-6}
def assign(ob,i,values):
    for g in list(ob.data.vertices[i].groups):ob.vertex_groups[g.group].remove([i])
    keep=sorted(values.items(),key=lambda p:-p[1])[:8];total=sum(v for _,v in keep)
    for n,v in keep:
        if v>1e-7:(ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)).add([i],float(v/total),'REPLACE')
def adjacency(ob):
    out=[[] for _ in ob.data.vertices]
    for e in ob.data.edges:
        a,b=e.vertices;out[a].append(b);out[b].append(a)
    return out
points=np.array([v.co[:] for v in body.data.vertices]);adj=adjacency(body);selected=set()
for face in body.data.polygons:
    if body.data.materials[face.material_index].name=='BC_AttackTentacle':selected.update(face.vertices)
parameter=np.full(len(points),-1.)
for i in selected:
    values=[(int(n.rsplit('_',1)[1]),w) for n,w in weights(body,body.data.vertices[i]).items() if n.startswith('attack_tentacle_')]
    parameter[i]=sum(n*w for n,w in values)/max(1e-8,sum(w for _,w in values))
old=parameter.copy();changed=set()
nodes=np.array([rig.data.bones[f'attack_tentacle_{i:02d}'].head_local[:] for i in range(57)]+[rig.data.bones['attack_tentacle_56'].tail_local[:]])
# The source has a fork, not a closed hairpin. The old 51->53 guide crossed
# empty space and assigned the joined skin to two distant parts of one chain.
# Keep the muscular stem and upstream 47 joints intact; follow the real free
# tip with the final joints and give the short hooked spur its own children.
junction=np.array((-.114,-1.188,.079))
def resample(path,count):
    path=np.array(path);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    return np.column_stack([np.interp(np.linspace(0,arc[-1],count),arc,path[:,k]) for k in range(3)])
nodes[48:]=resample([junction,(-.06,-1.13,.063),(.027,-1.067,.047),(.126,-1.064,.034),(.223,-1.069,.027)],10)
spur=resample([junction,(-.165,-1.28,.091),(-.165,-1.384,.089),(-.122,-1.423,.094),(-.064,-1.424,.101)],7)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for i in range(47,57):
    bone=rig.data.edit_bones[f'attack_tentacle_{i:02d}'];bone.head=nodes[i];bone.tail=nodes[i+1];bone.align_roll(Vector((0,1,0)))
for i in range(6):
    bone=rig.data.edit_bones.new(f'tip_spur_{i:02d}');bone.head=spur[i];bone.tail=spur[i+1]
    bone.parent=rig.data.edit_bones[f'tip_spur_{i-1:02d}' if i else 'attack_tentacle_47'];bone.use_connect=True;bone.align_roll(Vector((0,1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
def project(p,path):
    segments=np.diff(path,axis=0);lengths=np.linalg.norm(segments,axis=1)
    t=np.clip(np.sum((p-path[:-1])*segments,axis=1)/(lengths*lengths),0,1)
    gaps=np.linalg.norm(path[:-1]+segments*t[:,None]-p,axis=1);j=int(np.argmin(gaps))
    return j+float(t[j]),float(gaps[j]),float(np.sum(lengths[:j])+lengths[j]*t[j])
def chain_weights(position,prefix,count):
    ids=np.arange(max(0,int(np.floor(position))-1),min(count,int(np.floor(position))+3))
    values=np.exp(-((ids-position)/.9)**2);values/=values.sum()
    return {f'{prefix}{j:02d}':float(w) for j,w in zip(ids,values)}
spur_vertices=0
for i in selected:
    if old[i]<45:continue
    main_p,main_gap,unused=project(points[i],nodes)
    branch_p,branch_gap,branch_s=project(points[i],spur)
    if branch_gap<main_gap and branch_s>.008:
        release=smooth(.025,.12,branch_s)
        values={n:w*release for n,w in chain_weights(branch_p-.5,'tip_spur_',6).items()}
        values['attack_tentacle_47']=1-release;spur_vertices+=1
    else:
        values=chain_weights(main_p-.5,'attack_tentacle_',57)
        # Both skin branches leave the same junction frame, rather than two
        # incompatible FK frames separated by half a metre of empty guide.
        junction_blend=1-smooth(.025,.09,float(np.linalg.norm(points[i]-junction)))
        values={n:w*(1-junction_blend) for n,w in values.items()}
        values['attack_tentacle_47']=values.get('attack_tentacle_47',0)+junction_blend
    assign(body,i,values);changed.add(i)
report={'revision':'SurfaceFitV12','tip_vertices_rebound':len(changed),'spur_vertices':spur_vertices,'spur_bones':6,'unchanged_main_joints':47,'garments':{},'gameplay_tested':False,'attack_motion':'V10 driver and timing unchanged; distal rest guide follows actual fork','ccd':False}
body.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in body.data.loop_triangles]
flesh_weights=[weights(body,v) for v in body.data.vertices]
flesh_tree=BVHTree.FromPolygons(points.tolist(),triangles,all_triangles=True)
def support(name,side,kind):
    if kind=='sleeve':return name.startswith('leg_L2_' if side=='L' else 'leg_R4_')
    if name in ('body','body_front','body_rear'):return True
    if name.startswith('attack_tentacle_'):return side=='R' and int(name.rsplit('_',1)[1])<=9
    return kind=='lower' and name.startswith('leg_'+side)
def surface(side,kind):
    faces=[tri for tri in triangles if sum(sum(w for n,w in flesh_weights[i].items() if support(n,side,kind)) for i in tri)>2.1]
    return BVHTree.FromPolygons(points.tolist(),faces,all_triangles=True),faces
trees={(side,kind):surface(side,kind) for side in ('L','R') for kind in ('upper','lower','sleeve')}
def attach(p,side,kind):
    tree,faces=trees[(side,kind)];q,n,f,gap=tree.find_nearest(Vector(p));ids=faces[f]
    bary=np.clip(np.array(barycentric_transform(q,*[Vector(points[i]) for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1);bary/=max(1e-8,bary.sum())
    values={}
    for i,factor in zip(ids,bary):
        for name,w in flesh_weights[i].items():values[name]=values.get(name,0)+w*factor
    return np.array(q),np.array(n),gap,values
def outer_contact(p,margin):
    """Resolve remaining contact with a donor crossing the torso support."""
    q,n,f,d=flesh_tree.find_nearest(Vector(p));ids=triangles[f]
    if (Vector(p)-q).dot(n)>=margin:return np.array(p),None
    bary=np.clip(np.array(barycentric_transform(q,*[Vector(points[i]) for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1);bary/=max(1e-8,bary.sum())
    w={}
    for i,factor in zip(ids,bary):
        for name,value in flesh_weights[i].items():w[name]=w.get(name,0)+value*factor
    return np.array(q+n*margin),w
def rebuild_shell(proxy):
    visible=bpy.data.objects[proxy.name.replace('_SimulationProxy','')];mats=list(visible.data.materials)
    visible.data=proxy.data.copy();visible.data.materials.clear()
    for mat in mats:visible.data.materials.append(mat)
    for g in list(visible.vertex_groups):visible.vertex_groups.remove(g)
    for g in proxy.vertex_groups:visible.vertex_groups.new(name=g.name)
    for v in proxy.data.vertices:
        for g in v.groups:visible.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');visible.select_set(True);bpy.context.view_layer.objects.active=visible
    shell=visible.modifiers.new('Bounded 4mm surface shell V12','SOLIDIFY');shell.thickness=.004;shell.offset=1;shell.use_even_offset=False;shell.thickness_clamp=.5
    bpy.ops.object.modifier_apply(modifier=shell.name)
    for f in visible.data.polygons:f.use_smooth=True
for proxy in [o for o in scene.objects if o.type=='MESH' and o.name.endswith('_SimulationProxy')]:
    sleeve='Sleeve' in proxy.name;side='L' if 'Left' in proxy.name or 'Sleeve1_' in proxy.name else 'R'
    original=np.array([v.co[:] for v in proxy.data.vertices]);targets=[];normals=[];fields=[];clearance=[]
    for p in original:
        kind='sleeve' if sleeve else 'upper' if p[2]>1.18 else 'lower'
        q,n,gap,w=attach(p,side,kind)
        if sleeve:offset=.018+min(.006,gap*.03)
        else:
            upper=smooth(1.02,1.30,p[2]);offset=(.055+.035*(1-smooth(.35,.90,p[2])))*(1-upper)+.020*upper
            offset=min(offset,max(.020,gap))
        targets.append(q+n*offset);normals.append(n);fields.append(w);clearance.append(offset)
    targets=np.array(targets);normals=np.array(normals);links=adjacency(proxy)
    # Relax displacement rather than flattening the original torn topology.
    delta=targets-original
    for _ in range(5):
        delta=np.array([d*.72+np.mean([delta[j] for j in links[i]],axis=0)*.28 if links[i] else d for i,d in enumerate(delta)])
    fitted=original+delta
    for i,p in enumerate(fitted):
        kind='sleeve' if sleeve else 'upper' if original[i,2]>1.18 else 'lower'
        q,n,gap,w=attach(p,side,kind)
        signed=float(np.dot(p-q,n));offset=clearance[i]
        # Final local contact uses the same surface from which skin weights are
        # transferred, rather than fitting a different rigid envelope per pose.
        fitted[i]=q+n*offset;fields[i]=w
        for _ in range(4):
            fitted[i],contact_weights=outer_contact(fitted[i],.017)
            if contact_weights is None:break
            fields[i]=contact_weights
    for v,p,w in zip(proxy.data.vertices,fitted,fields):v.co=Vector(p);assign(proxy,v.index,w)
    proxy.data.update()
    # Keep winding consistent with the contacted flesh for backstop normals.
    bm=bmesh.new();bm.from_mesh(proxy.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    facing=sum(f.normal.dot(Vector(normals[f.verts[0].index]))*f.calc_area() for f in bm.faces)
    if facing<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(proxy.data);bm.free();proxy.data.update()
    color=proxy.data.color_attributes['ClothTravel'];travel=[]
    minz,maxz=float(fitted[:,2].min()),float(fitted[:,2].max())
    for i,p in enumerate(fitted):
        # Broad torso/sleeve support is skin driven; only a narrow distal cuff
        # and hanging hem can depart from the fitted surface.
        if sleeve:amount=.010*(1-smooth(minz+.02,minz+.10,p[2]))
        else:amount=.035*(1-smooth(.70,1.20,p[2]))
        if amount<.0075:amount=0.
        c=color.data[i].color;color.data[i].color=(amount/.45,c[1],c[2],1);travel.append(amount)
    # Projection around anatomical creases can collapse neighbouring samples.
    # Clean the simulation surface before copying its visible thickness; UE's
    # cloth factory rejects even a single zero-area simulation triangle.
    bm=bmesh.new();bm.from_mesh(proxy.data);before_vertices=len(bm.verts);before_faces=len(bm.faces)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0003)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0003)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    small=[f for f in bm.faces if f.calc_area()<2e-8]
    if small:bmesh.ops.delete(bm,geom=small,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(proxy.data);bm.free();proxy.data.update()
    cleanup={'merged_vertices':before_vertices-len(proxy.data.vertices),'removed_faces':before_faces-len(proxy.data.polygons)}
    travel=[v.color[0]*.45 for v in proxy.data.color_attributes['ClothTravel'].data]
    rebuild_shell(proxy)
    report['garments'][proxy.name]={'vertices':len(proxy.data.vertices),'cleanup':cleanup,'dynamic_vertices':sum(v>.0075 for v in travel),'max_travel_cm':max(travel)*100,'median_refit_cm':float(np.median(np.linalg.norm(fitted-original,axis=1))*100),'surface_clearance_cm':(np.percentile(clearance,[0,50,100])*100).tolist()}
    print(proxy.name,report['garments'][proxy.name],flush=True)
# Bring the shoulder binding onto the robe it restrains, including its skin.
strap=bpy.data.objects.get('BC_ShoulderRestraint');robe=bpy.data.objects['BC_LeftTornRobe_SimulationProxy'];robe.data.calc_loop_triangles()
rp=[v.co.copy() for v in robe.data.vertices];rt=[tuple(t.vertices) for t in robe.data.loop_triangles];tree=BVHTree.FromPolygons(rp,rt,all_triangles=True)
# Original strap has 98 ribbon vertices and a matching 98-vertex thickness
# layer. Fit the centre ribbon once, then retain the leather's real thickness.
oldstrap=np.array([v.co[:] for v in strap.data.vertices]);half=len(oldstrap)//2
for i in range(half):
    p=Vector((oldstrap[i]+oldstrap[i+half])*.5)
    q,n,f,d=tree.find_nearest(p);ids=rt[f]
    flesh_q,flesh_n,flesh_face,flesh_gap=flesh_tree.find_nearest(p)
    # Above the robe, the strap still follows the shoulder, rather than being
    # clamped down to the robe boundary and collapsing its upper rows.
    if d>flesh_gap+.012:
        q=Vector(flesh_q);n=Vector(flesh_n);offset=.025
        _,w=outer_contact(q,.001)
    else:
        bary=np.clip(np.array(barycentric_transform(q,*[rp[j] for j in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1);bary/=max(1e-8,bary.sum())
        w={}
        for j,factor in zip(ids,bary):
            for name,value in weights(robe,robe.data.vertices[j]).items():w[name]=w.get(name,0)+value*factor
        if n.dot(flesh_n)<0:n=-n
        offset=.007
    thickness=float(np.linalg.norm(oldstrap[i]-oldstrap[i+half]))
    center=np.array(q+n*offset)
    for _ in range(4):
        center,contact_weights=outer_contact(center,.023)
        if contact_weights is None:break
        w=contact_weights
    q,n,_,_=flesh_tree.find_nearest(Vector(center))
    q=Vector(center)-n*offset
    strap.data.vertices[i].co=q+n*(offset+thickness*.5)
    strap.data.vertices[i+half].co=q+n*(offset-thickness*.5)
    assign(strap,i,w);assign(strap,i+half,w)
strap.data.update()
# Move the identification plate and its letter together onto the refitted
# restraint, preserving their relative thickness and sharing one skin frame.
plate=bpy.data.objects.get('BC_M_Tag');stamp=bpy.data.objects.get('BC_M_Stamp')
if plate:
    strap.data.calc_loop_triangles();sp=[v.co.copy() for v in strap.data.vertices];st=[tuple(t.vertices) for t in strap.data.loop_triangles]
    strap_tree=BVHTree.FromPolygons(sp,st,all_triangles=True)
    center=sum((v.co for v in plate.data.vertices),Vector())/len(plate.data.vertices)
    q,n,f,d=strap_tree.find_nearest(center);_,outward,_,_=flesh_tree.find_nearest(q)
    if n.dot(outward)<0:n=-n
    ids=st[f];bary=np.clip(np.array(barycentric_transform(q,*[sp[j] for j in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1);bary/=max(1e-8,bary.sum())
    w={}
    for j,factor in zip(ids,bary):
        for name,value in weights(strap,strap.data.vertices[j]).items():w[name]=w.get(name,0)+value*factor
    rotation=Vector((-1,0,0)).rotation_difference(n);target=q+n*.012
    for ob in (plate,stamp):
        if not ob:continue
        for v in ob.data.vertices:v.co=target+rotation@(v.co-center);assign(ob,v.index,w)
        ob.data.update()
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_SurfaceFitV12.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in ('MESH','ARMATURE'):o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_SurfaceFitV12.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BOUND_SURFACE_FIT_V12_EXPORTED',flush=True)
