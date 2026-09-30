"""Cut only the fixed receiver at the existing B53 feed route.

Export a triangle patch, retaining the original native triangles everywhere
outside the cut. No belt, bone, animation, material asset or camera is changed.
"""
import bpy,bmesh,json,gzip,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent
S=json.loads((O/'source.json').read_text());A=json.loads((O/'authoring_inputs.json').read_text())
parts=json.load(gzip.open(O/'patch_source.json.gz','rt'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
slots=[s['name'] for s in S['slots']]
materials=[bpy.data.materials.new(n) for n in slots]
cutmat=bpy.data.materials.new('F57_NewCutSurface');cut_index=len(materials)
root=next(b['rest'] for b in S['bones'] if b['name']=='WPN_root')
T=Matrix.LocRotScale(Vector(root[:3]),Quaternion((root[6],*root[3:6])),Vector(root[7:]))
NT=T.to_3x3().inverted().transposed()


def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob


def key(points,mi):
    return mi,tuple(sorted(tuple(round(float(x),7) for x in p) for p in points))


def attribute(me,name,values):
    a=me.attributes.new(name,'INT','FACE')
    for x,v in zip(a.data,values):x.value=int(v)


def bary(point,triangle):
    a,b,c=map(Vector,triangle);v0=b-a;v1=c-a;v2=Vector(point)-a
    d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1)
    denom=d00*d11-d01*d01
    if abs(denom)<1e-22:return (1.,0.,0.)
    v=(d11*v2.dot(v0)-d01*v2.dot(v1))/denom
    w=(d00*v2.dot(v1)-d01*v2.dot(v0))/denom
    return (1-v-w,v,w)


def make_tool():
    xmin,ymin,zmin=A['opening_min_root_m'];xmax,ymax,zmax=A['opening_max_root_m'];r=A['corner_radius_m']
    profile=[]
    for y,z,angle in [(ymax-r,zmax-r,0),(ymin+r,zmax-r,90),(ymin+r,zmin+r,180),(ymax-r,zmin+r,270)]:
        for j in range(10):
            a=math.radians(angle+90*j/10);profile.append((y+r*math.cos(a),z+r*math.sin(a)))
    n=len(profile);p=[(x,y,z) for x in (xmin,xmax) for y,z in profile]
    f=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new('F57_FeedOpeningTool');me.from_pydata(p,[],f);me.materials.append(cutmat)
    attribute(me,'native_triangle',[-1]*len(f))
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    return ob


tool=make_tool();buffers={};remove=[];report=[]
for part in parts:
    me=bpy.data.meshes.new(part['name']);me.from_pydata(part['p'],[],part['t'])
    for m in materials+[cutmat]:me.materials.append(m)
    uv=me.uv_layers.new(name='UV0')
    for i,p in enumerate(me.polygons):
        p.material_index=part['mi'][i];p.use_smooth=True
        for j,li in enumerate(p.loop_indices):uv.data[li].uv=part['uv'][i][j]
    me.normals_split_custom_set([n for row in part['n'] for n in row])
    attribute(me,'native_triangle',part['source_ids'])
    ob=bpy.data.objects.new(part['name'],me);bpy.context.collection.objects.link(ob)
    # A marked cutter material identifies the new thickness surfaces and lets
    # the edge bevel affect only the new opening, leaving all old hard edges.
    active(ob);mod=ob.modifiers.new('B53 route clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool;mod.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    me=ob.data
    weights=me.attributes.get('bevel_weight_edge') or me.attributes.new('bevel_weight_edge','FLOAT','EDGE')
    edge_lookup={tuple(sorted(e.vertices)):e.index for e in me.edges};adj={i:[] for i in range(len(me.edges))}
    for p in me.polygons:
        for e in p.edge_keys:adj[edge_lookup[tuple(sorted(e))]].append(p.material_index==cut_index)
    for i,vals in adj.items():weights.data[i].value=float(any(vals) and not all(vals))
    mod=ob.modifiers.new('New lip edge radius','BEVEL');mod.limit_method='WEIGHT';mod.width=A['new_edge_bevel_m'];mod.segments=3;mod.use_clamp_overlap=True;mod.material=cut_index
    bpy.ops.object.modifier_apply(modifier=mod.name)
    me=ob.data;bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm,dist=5e-8,edges=list(bm.edges))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(38)
    bm.to_mesh(me);bm.free();me.update()
    # The source normals of retained/native faces are not replaced. The
    # following normals are used only on newly generated lip/bevel triangles.
    mod=ob.modifiers.new('Cut face normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=45
    bpy.ops.object.modifier_apply(modifier=mod.name)
    me=ob.data;me.calc_loop_triangles()
    cut_slot=slots.index('M_LMG201_F37_Interior') if len(set(part['mi']))>1 else part['mi'][0]
    for p in me.polygons:
        if p.material_index!=cut_index:continue
        # Explicit physical projection for new caps; old UVs stay on old faces.
        axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
        for li in p.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            me.uv_layers.active.data[li].uv=(co[axes[0]]/.08,co[axes[1]]/.08)
    original={key([part['p'][v] for v in tri],mi):sid for tri,mi,sid in zip(part['t'],part['mi'],part['source_ids'])}
    by_id={sid:i for i,sid in enumerate(part['source_ids'])}
    kept=set();added=0
    source_attr=me.attributes.get('native_triangle')
    for tri in me.loop_triangles:
        poly=me.polygons[tri.polygon_index];mi=poly.material_index
        points=[me.vertices[v].co for v in tri.vertices]
        previous=original.get(key(points,mi))
        if previous is not None:
            kept.add(previous);continue
        is_cut=mi==cut_index
        if is_cut:mi=cut_slot
        sid=source_attr.data[poly.index].value if source_attr and not is_cut else -1
        source_i=by_id.get(sid)
        if source_i is None:sid=-1
        row=buffers.setdefault(mi,{'slot':slots[mi],'material':S['slots'][mi]['material'],'bone':'WPN_root','p':[],'n':[],'uv':[],'t':[],'color_source':[],'color_bary':[]})
        start=len(row['p'])
        for vi,li in zip(tri.vertices,tri.loops):
            pos=me.vertices[vi].co
            weights=(1.,0.,0.)
            if sid>=0:
                weights=bary(pos,[part['p'][v] for v in part['t'][source_i]])
                normal=sum((Vector(part['n'][source_i][k])*weights[k] for k in range(3)),Vector()).normalized()
            else:normal=me.corner_normals[li].vector
            row['p'].append(list(T@pos));row['n'].append(list((NT@normal).normalized()))
            row['uv'].append(list(me.uv_layers.active.data[li].uv));row['color_source'].append(sid);row['color_bary'].append(weights)
        row['t'].append([start,start+1,start+2]);added+=1
    retired=sorted(set(part['source_ids'])-kept);remove+=retired
    # The source scene uses real material slot names too, not the cutter marker.
    for poly in me.polygons:
        if poly.material_index==cut_index:poly.material_index=cut_slot
    ob['binding']='WPN_root';ob['revision']='FeedMouth57 local patch'
    report.append({'part':part['name'],'original_faces':len(part['source_ids']),'native_faces_retained':len(kept),'removed_faces':len(retired),'new_faces':added})
    print('F57_AUTHOR',report[-1],flush=True)

tool.hide_render=True;tool.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_FeedMouth57.blend'))
with gzip.open(O/'mesh_buffers.json.gz','wt') as f:json.dump(list(buffers.values()),f)
(O/'removals.json').write_text(json.dumps({'source_body_sha256':S['sha256'],'remove_triangle_ids':remove},indent=2))
(O/'authoring.json').write_text(json.dumps({'parts':report,'removed_faces':len(remove),'new_faces':sum(len(r['t']) for r in buffers.values()),'opening':A,'runtime_tested':False},indent=2))
