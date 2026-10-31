"""Small original hard-surface toolkit for the scoped apartment kitchen.
Metres, +Z up, manufactured front = -Y. Mesh groups, not actor-per-screw.
"""
from pathlib import Path
import bpy, bmesh, math, inspect
from mathutils import Vector, Matrix
from collections import defaultdict
G=defaultdict(lambda:dict(v=[],f=[],m=[],smooth=[]))
M={}
C={}

def clear():
    G.clear();C.clear()
    global _K
    _K=0
    for c in list(bpy.data.collections):
        if c.name.startswith(('KIT_', 'CTX_')):bpy.data.collections.remove(c)
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)

def tag(k,label):
    e=G[k]['audit'][-1]
    if e['label'] and e['label']!=f"{e['primitive']}_{e['serial']:03d}" and e['label'] not in [e['primitive'],'BasinShell']:
        raise RuntimeError('Unconsumed primitive '+e['label'])
    e['label']=label

def mat(key):
    if isinstance(key,str) and key in M:return M[key]
    return key

def poly(k,vs,fs,m,smooth=False):
    if isinstance(m,str):m=mat(m)
    d=G[k];off=len(d['v']);d['v'].extend(tuple(v) for v in vs)
    d['f'].extend(tuple(off+i for i in f) for f in fs)
    d['m'].extend([m]*len(fs));d['smooth'].extend([smooth]*len(fs) if isinstance(smooth,bool) else smooth)
    primitive=inspect.stack()[1].function
    serial=len(d.get('audit',[]))
    d.setdefault('audit',[]).append(dict(start=len(d['f'])-len(fs),count=len(fs),primitive=primitive,serial=serial,label=f'{primitive}_{serial:03d}'))

def box(k,c,size,m,r=0,segments=3):
    if not r:
        a,b,h=[x*.5 for x in size]
        vs=[(c[0]+dx,c[1]+dy,c[2]+dz) for dx,dy,dz in [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
        fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        poly(k,vs,fs,m);return
    bpy.ops.mesh.primitive_cube_add(size=1,location=c)
    o=bpy.context.object;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=o.modifiers.new('Manufactured edge radius','BEVEL');bevel.width=min(r,min(size)*.45);bevel.segments=segments
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    fs=[tuple(p.vertices) for p in o.data.polygons]
    poly(k,vs,fs,m,smooth=False)
    bpy.data.objects.remove(o,do_unlink=True)

def basis(axis):
    n=Vector(axis).normalized()
    a=Vector((0,0,1)).cross(n) if abs(n.z)<.95 else Vector((1,0,0))
    a.normalize();return n,a,n.cross(a)

def lathe(k,c,axis,profile,m,n=48):
    """Revolved closed section. Axis rings share one pole, never coincident rings.

    Optional single-axis profiles describing a solid receive explicit caps.
    Multi-axis vessel profiles already include their inner and outer surfaces.
    """
    nvec,u,v=basis(axis);c=Vector(c);vs=[];fs=[]
    bm=bmesh.new()
    rings=[]
    for z,r in profile:
        if abs(r)<1e-9:rings.append([bm.verts.new(c+nvec*z)])
        else:
            ring=[bm.verts.new(c+nvec*z+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n))) for i in range(n)]
            rings.append(ring)
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    # Drop only truly duplicated rings (same axial plane AND same radius).
    # A legitimate flat annulus has a different radius and must be kept.
    cleaned=[rings[0]]
    for cur in rings[1:]:
        prev=cleaned[-1]
        if len(prev)==len(cur)>1:
            axial=abs((prev[0].co-cur[0].co).dot(nvec))
            if axial<=1e-9 and all((a.co-b.co).length<=1e-9 for a,b in zip(prev,cur)):
                continue
        cleaned.append(cur)
    # Two axis poles at the same axial position (common in vessel profiles that
    # start and end on the axis at z=0) would each generate a cap disc at the
    # same plane. Keep only one so the bottom is a single disc.
    if len(rings)>1 and len(rings[0])==1 and len(rings[-1])==1:
        if abs((rings[0][0].co-rings[-1][0].co).dot(nvec))<=1e-9:
            rings=rings[:-1]
    rings=cleaned=rings
    for a,b in zip(rings,rings[1:]):
        if len(a)==1 and len(b)==n:
            for i in range(n):fs.append((a[0].index,b[(i+1)%n].index,b[i].index))
        elif len(a)==n and len(b)==1:
            for i in range(n):fs.append((a[i].index,a[(i+1)%n].index,b[0].index))
        elif len(a)==n and len(b)==n:
            for i in range(n):fs.append((a[i].index,a[(i+1)%n].index,b[(i+1)%n].index,b[i].index))
    # Close only genuinely open ends. A profile whose first and last ring are
    # the same circle is already a closed section; capping it would duplicate
    # the side faces and register as self-intersection.
    def _same_ring(a,b):
        return len(a)==len(b) and all((x.co-y.co).length<=1e-9 for x,y in zip(a,b))
    closed_section=len(rings)>1 and _same_ring(rings[0],rings[-1])
    # Cap only ends that are genuinely open rings. When a profile starts or
    # ends on the axis, the revolved triangles already close that end, so an
    # extra flat disc would overlap the side wall (self-intersection).
    if not closed_section:
        # Cap with the ring that is actually open, never a wider disc.
        if len(rings[0])==n and len(rings[1])>1:fs.append(tuple(v.index for v in reversed(rings[0])))
        if len(rings[-1])==n and len(rings[-2])>1:fs.append(tuple(v.index for v in rings[-1]))
    for face in fs:bm.faces.new([bm.verts[i] for i in face])
    # Coordinates and faces come from the same BMesh indexing as the audit copy.
    poly(k,[tuple(v.co) for v in bm.verts],fs,m,True)
    bm.free()

def cyl(k,a,b,r,m,n=32):
    # a and b are absolute endpoints in the component frame, not a + length.
    # Store the closed section around its centre, with b-a as the full axis.
    delta=Vector(b)-Vector(a);length=delta.length
    if length<=1e-9:raise ValueError('Cylinder endpoints must be distinct')
    lathe(k,(Vector(a)+Vector(b))*.5,delta,[(-length*.5,r),(length*.5,r)],m,n)

def ring(k,c,axis,outer,inner,h,m,n=64):
    nvec,u,v=basis(axis);c=Vector(c);vs=[];fs=[]
    for z,r in [(-h/2,outer),(h/2,outer),(h/2,inner),(-h/2,inner)]:vs.extend(c+nvec*z+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for i in range(n))
    for j in range(4):
        for i in range(n):ni=(i+1)%n;nj=(j+1)%4;fs.append((j*n+i,j*n+ni,nj*n+ni,nj*n+i))
    poly(k,vs,fs,m,True)

def torus(k,c,axis,major,minor,m,n=48,sides=8):
    nvec,u,v=basis(axis);c=Vector(c);vs=[];fs=[]
    for i in range(n):
        t=i*math.tau/n;d=u*math.cos(t)+v*math.sin(t)
        for j in range(sides):
            a=j*math.tau/sides;vs.append(c+d*(major+minor*math.cos(a))+nvec*minor*math.sin(a))
    for i in range(n):
        for j in range(sides):fs.append((i*sides+j,((i+1)%n)*sides+j,((i+1)%n)*sides+(j+1)%sides,i*sides+(j+1)%sides))
    poly(k,vs,fs,m,True)

def tube(k,points,r,m,n=12):
    ps=[]
    for p in points:
        p=Vector(p)
        if not ps or (p-ps[-1]).length>1e-8:ps.append(p)
    if len(ps)<2:raise ValueError('Tube needs two distinct path points')
    vs=[];fs=[];prev=None
    for i,p in enumerate(ps):
        t=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        if prev is None:
            a=Vector((0,0,1)).cross(t) if abs(t.z)<.95 else Vector((1,0,0))
        else:
            a=prev-t*prev.dot(t)
        a.normalize();b=t.cross(a);prev=a
        vs.extend(p+r*(a*math.cos(j*math.tau/n)+b*math.sin(j*math.tau/n)) for j in range(n))
    for i in range(len(ps)-1):
        for j in range(n):nj=(j+1)%n;fs.append((i*n+j,i*n+nj,(i+1)*n+nj,(i+1)*n+j))
    fs.extend([tuple(reversed(range(n))),tuple((len(ps)-1)*n+j for j in range(n))]);poly(k,vs,fs,m,True)

def pipe(k,points,r=.008,m='Steel',n=20):
    ps=[Vector(p) for p in points];path=[ps[0]]
    for i in range(1,len(ps)-1):
        p=ps[i];a=(p-ps[i-1]).normalized();b=(ps[i+1]-p).normalized()
        reach=min(.05,(p-ps[i-1]).length*.40,(ps[i+1]-p).length*.40)
        start=p-a*reach;end=p+b*reach
        for j in range(9):t=j/8;path.append((1-t)**2*start+2*t*(1-t)*p+t*t*end)
    path.append(ps[-1]);tube(k,path,r,m,n)

def prism(k,outline,z0,z1,m):
    n=len(outline);vs=[(x,y,z) for z in [z0,z1] for x,y in outline]
    fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    poly(k,vs,fs,m)

def text(k,body,c,size=.015,m='Paper',normal=(0,-1,0)):
    data=bpy.data.curves.new('label','FONT');data.body=body;data.size=size;data.align_x='CENTER';data.extrude=.00002;data.bevel_depth=0;data.fill_mode='BOTH';data.resolution_u=4
    o=bpy.data.objects.new('engraving',data);bpy.context.scene.collection.objects.link(o)
    o.location=c;o.rotation_euler=Vector(normal).to_track_quat('Z','Y').to_euler()
    bpy.context.view_layer.objects.active=o
    for other in bpy.context.selected_objects:other.select_set(False)
    o.select_set(True);bpy.ops.object.convert(target='MESH')
    # Font conversion duplicates front/back cap vertices; weld only coincident
    # points before recalculating the closed embossed letter shells.
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();bm.verts.index_update();bm.faces.index_update();bm.to_mesh(o.data);bm.free()
    poly(k,[o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],m)
    bpy.data.objects.remove(o,do_unlink=True)

def join(k,old,label='joined_primitive'):
    """Topology-preserving regroup for provenance/audit; not a geometric union."""
    d=G[k];names=set(old) if isinstance(old,(list,tuple,set)) else {old}
    indices=[i for i,e in enumerate(d.get('audit',[])) if e['primitive'] in names or e['label'] in names]
    if not indices:raise KeyError(str(names))
    if len(indices)!=len(names):raise KeyError('Incomplete join '+str(names))
    d['audit'].append(dict(start=d['audit'][indices[0]]['start'],count=sum(d['audit'][i]['count'] for i in indices),primitive=label,serial=0,label=label))
    for i in sorted(indices,reverse=True):
        e=d['audit'].pop(i)
        for later in d['audit']:
            if later['start']>e['start']:later['start']-=e['count']

def _compact_faces(vertices,faces):
    used=sorted({i for f in faces for i in f});remap={old:i for i,old in enumerate(used)}
    return [vertices[i] for i in used],[tuple(remap[i] for i in f) for f in faces]

def _operand(d,e,source_transform=None):
    vertices,fs=_compact_faces(d['v'],d['f'][e['start']:e['start']+e['count']])
    me=bpy.data.meshes.new('KIT_Operand');me.from_pydata(vertices,[],fs);me.update()
    for m in d['m'][e['start']:e['start']+e['count']]:me.materials.append(m)
    for p,old in zip(me.polygons,d['m'][e['start']:e['start']+e['count']]):p.material_index=me.materials.find(old.name)
    o=bpy.data.objects.new('_OP_Kitchen',me);bpy.context.scene.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();bm.verts.index_update();bm.faces.index_update();bm.to_mesh(me);bm.free()
    o.matrix_world=source_transform.copy() if source_transform is not None else Matrix.Identity(4)
    return o

def _finish_op(ob):
    return [(list(p.vertices),ob.data.materials[p.material_index],p.use_smooth) for p in ob.data.polygons]

def boolean_group(k,names,label,operation='UNION',cutter=None,source_transform=None):
    """Local same-material union or real socket; preserves all unrelated faces."""
    d=G[k]
    selected_indices=[]
    for name in names:
        matches=[i for i,e in enumerate(d['audit']) if e['label']==name]
        if len(matches)!=1:raise RuntimeError('Boolean operand not unique '+name)
        selected_indices.append(matches[0])
    if not selected_indices:raise RuntimeError('Missing boolean operands '+str(names))
    selected=[d['audit'][i] for i in selected_indices]
    if len(selected)!=len(names) or any(e['label']!=n for e,n in zip(selected,names)):
        raise RuntimeError('Boolean operand selection incomplete '+str(names)+' != '+str([e['label'] for e in selected]))
    keep=[e for i,e in enumerate(d['audit']) if i not in selected_indices]
    obs=[_operand(d,e,source_transform) for e in selected]
    bpy.context.view_layer.update()
    if cutter is not None:
        ob=obs[0];mod=ob.modifiers.new('Real socket','BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=cutter
    else:
        ob=obs[0]
        for other in obs[1:]:
            mod=ob.modifiers.new('Continuous ceramic joint','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=other
            bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active=ob
    if cutter is not None:bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();bm.verts.index_update();bm.faces.index_update();bm.to_mesh(ob.data);bm.free()
    ob.data.update()
    result=_finish_op(ob);result_vertices=[v.co.copy() for v in ob.data.vertices]
    if not result:raise RuntimeError('Boolean returned empty geometry '+label)
    # Every operand shares the authored component transform, so its local data
    # is already in the component frame. Never leave a mesh at world origin.
    new=dict(v=[],f=[],m=[],smooth=[],audit=[])
    for e in keep:
        if e['label']==label:continue
        off=len(new['v']);vertices,faces=_compact_faces(d['v'],d['f'][e['start']:e['start']+e['count']])
        new['v'].extend(vertices);new['f'].extend(tuple(off+i for i in f) for f in faces)
        new['m'].extend(d['m'][e['start']:e['start']+e['count']]);new['smooth'].extend(d['smooth'][e['start']:e['start']+e['count']])
        new['audit'].append(dict(start=len(new['f'])-e['count'],count=e['count'],primitive=e['primitive'],serial=e['serial'],label=e['label']))
    vertices,faces=_compact_faces(result_vertices,[r[0] for r in result])
    off=len(new['v']);new['v'].extend(vertices)
    new['f'].extend(tuple(off+i for i in face) for face in faces);new['m'].extend(r[1] for r in result);new['smooth'].extend(r[2] for r in result)
    new['audit'].append(dict(start=len(new['f'])-len(result),count=len(result),primitive=label,serial=0,label=label))
    d.clear();d.update(new)
    for o in obs:bpy.data.objects.remove(o,do_unlink=True)


def rounded_rect(w,h,r,z=0,segments=6):
    pts=[]
    for cx,cy,start in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for i in range(segments+1):
            a=math.radians(start+i*90/segments);pts.append((cx+r*math.cos(a),cy+r*math.sin(a),z))
    return pts

def rounded_basin(k,c,top_rings,bottom,m='Steel'):
    """Rounded rectangular open bowl with a real interior, not a dark plane."""
    x,y,z=c;allpts=[]
    rings=top_rings
    for w,h,r,zz in rings:
        allpts.extend([(x+px,y+py,zz) for px,py,_ in rounded_rect(w,h,r,zz)])
    n=len(allpts)//len(rings);fs=[]
    for j in range(len(rings)-1):
        for i in range(n):ni=(i+1)%n;fs.append((j*n+i,j*n+ni,(j+1)*n+ni,(j+1)*n+i))
    # The underside is already closed by the explicit outer floor cap below.
    # Closed outer shell: rim joins the outside of the wall, underside caps the
    # bottom. The inner bowl and drain remain independently inspectable.
    # The visible inner wall ends at its floor. An outer bottom cap and one
    # external wall return to the original rim, making one closed solid shell.
    last=top_rings[-1]
    bottom=(last[0],last[1],last[2],last[3]-.003)
    # Use the same outer wall section all the way to the flange. The counter
    # aperture follows the section at z=-5mm instead of cutting through a
    # widening, incorrectly sloped shoulder.
    # The first outer ring is exactly the aperture: top inner flange = 7 mm;
    # outer flange = 4 mm, so the 3 mm horizontal return meets at z=4 mm.
    # The aperture runs from z=-5 mm up to the counter top z=0.
    outer=[(w+.003,h+.003,r+.0015,zz-.003) for w,h,r,zz in reversed(top_rings[1:])]
    # Outer floor already occupies its own datum. Build a monotonic wall to a
    # vertical neck at the counter aperture, then a genuine horizontal flange.
    outer=outer[1:]
    neck=(top_rings[0][0]+.003,top_rings[0][1]+.003,top_rings[0][2]+.0015)
    flange=(top_rings[0][0]+.012,top_rings[0][1]+.012,top_rings[0][2]+.006)
    outer[-1]=(*neck,-.005)
    outer.extend([(*neck,0),(*flange,0),(*flange,.007)])
    for ring_spec in [bottom]+outer:
        w,h,r,zz=ring_spec;allpts.extend([(x+px,y+py,zz) for px,py,_ in rounded_rect(w,h,r,zz)])
    # Inner floor and outer floor are opposite faces of a 3 mm bottom.
    fs.append(tuple(reversed(range((len(rings)-1)*n,len(rings)*n))))
    fs.append(tuple(range(len(rings)*n,(len(rings)+1)*n)))
    for j in range(len(outer)):
        a=(len(rings)+j)*n;b=a+n
        for i in range(n):ni=(i+1)%n;fs.append((a+i,b+i,b+ni,a+ni))
    for i in range(n):ni=(i+1)%n;fs.append((i,ni,len(allpts)-n+ni,len(allpts)-n+i))
    poly(k,allpts,fs,m,True)

def bolt(k,c,axis=(0,-1,0),r=.004,m='Steel'):
    p=Vector(c);n=Vector(axis).normalized();lathe(k,p,n,[(0,r*1.22),(.002,r*1.22),(.002,r),(.005,r)],m,16)

def finish(materials,root):
    """Generate UV0 metres, retain physical bevel normals, no fake normal maps."""
    out=root/'FBX';out.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    rows=[]
    for k,d in G.items():
        mesh=bpy.data.meshes.new('KIT_'+k);mesh.from_pydata(d['v'],[],d['f']);mesh.update()
        ob=bpy.data.objects.new(k if k.startswith('KIT_') else 'KIT_'+k,mesh)
        col=bpy.data.collections.get('KIT_Source');col.objects.link(ob)
        slots=list(dict.fromkeys(d['m']))
        for m in slots:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='UVMap')
        for f,sm in zip(mesh.polygons,d['smooth']):
            f.material_index=slots.index(d['m'][f.index]);f.use_smooth=sm
            axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
            for li in f.loop_indices:
                p=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=(p[axes[0]],p[axes[1]])
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
        # Non-destructive authored normal stack; bevel geometry is already baked.
        wn=ob.modifiers.new('Area weighted corner normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=30
        bpy.context.view_layer.objects.active=ob;ob.select_set(True)
        try:bpy.ops.object.modifier_apply(modifier=wn.name)
        except RuntimeError:ob.modifiers.remove(wn)
        # Preserve source polygon order for original-primitive audits. FBX export
        # performs the final triangulation; applying it here would invalidate the
        # authored face spans and manufacture holes in audit-only copies.
        mesh=ob.data;uv=mesh.uv_layers.active
        for f in mesh.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
            for li in f.loop_indices:
                p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
        # Local component origins may sit at a countertop or hinge, so negative
        # local z is intentional for a bowl/apron, not an authoring error.
        ob['MaterialSlots']=','.join(m.name for m in slots)
        ob['SourceUnits']='metres; authored UV0 in metres; local component origin'
        ob['AuditPrimitives']=';'.join(str(x['start'])+':'+str(x['count'])+':'+str(x['primitive'])+':'+str(x['serial'])+':'+str(x['label']) for x in d.get('audit',[]))
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=out/f'SM_KP_{k}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',add_leaf_bones=False)
        rows.append(dict(key=k.removeprefix('KIT_'),name='SM_KP_'+k.removeprefix('KIT_'),fbx=str(fbx),triangles=sum(len(p.vertices)-2 for p in mesh.polygons),materials=[m.name for m in slots]))
        ob.select_set(False)
    return rows
