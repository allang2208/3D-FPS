"""Replace the estimated fore-end shoe with a closed surface-matched shoe."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from grip_math import load
S=O.parent/'Super90Foregrips20261007';X=O/'Exports';X.mkdir(exist_ok=True)
d=load('SK_Super90_V7');mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)))
inv=mount.inverted();verts=[inv@Vector((p[0]/100,-p[1]/100,p[2]/100)) for p in d['vertices']]
gun={i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.startswith('WPN_'))>.5}
faces=[f for f in d['faces'] if all(i in gun for i in f)];tree=BVHTree.FromPolygons(verts,faces)
nx,ny=56,20;lower=[];upper=[];gaps=[]
for ix in range(nx+1):
    x=-.057+.114*ix/nx
    for iy in range(ny+1):
        y=-.0105+.021*iy/ny;hit=tree.ray_cast(Vector((x,y,.0033)),Vector((0,0,1)),.05)[0]
        if hit is None:raise RuntimeError('No native fore-end surface at '+str((x,y)))
        old=.03075-.025*math.sqrt(1-(y/.0213)**2)+.00015
        gaps.append((hit.z-old)*1000)
        lower.append((x,y,.0033));upper.append((x,y,hit.z+.00015))
n=len(lower);pad_faces=[]
for ix in range(nx):
    for iy in range(ny):
        a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;e=a+ny+1
        pad_faces.extend([(a,b,c,e),(e+n,c+n,b+n,a+n)])
rim=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
pad_faces.extend((a,a+n,b+n,b) for a,b in zip(rim,rim[1:]+rim[:1]))
report={'old_shoe_gap_mm':{'min':min(gaps),'max':max(gaps),'mean':sum(gaps)/len(gaps)},'contact_samples':len(upper),'parts':{}}
for kind in ('vertical','tactical_vertical','canted','prism','angled'):
    bpy.ops.wm.open_mainfile(filepath=str(S/'Exports'/('SM_Super90_'+kind+'_Editable.blend')))
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    # Keep the existing rail and bolts; replace only the estimated curved shoe
    # above the rail's 3.5 mm top plane, including its bevel edge triangles.
    bm=bmesh.new();bm.from_mesh(body.data)
    candidates=[f for f in bm.faces if body.data.materials[f.material_index].name.startswith('Super90_Foregrip_Saddle')]
    selected=set();visited=set()
    for face in candidates:
        if face in visited:continue
        group=[];queue=[face];visited.add(face)
        while queue:
            f=queue.pop();group.append(f)
            for edge in f.edges:
                for g in edge.link_faces:
                    if g not in visited and g.material_index==face.material_index:visited.add(g);queue.append(g)
        if max(v.co.z for f in group for v in f.verts)>.0036:selected.update(group)
    bmesh.ops.delete(bm,geom=list(selected),context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(body.data);bm.free()
    # The angled body's top is not a plane: aligning only its highest vertex
    # leaves a visible slit below the rail. Fill just the real top interface.
    bodytree=BVHTree.FromPolygons([v.co for v in body.data.vertices],
        [list(f.vertices) for f in body.data.polygons if not body.data.materials[f.material_index].name.startswith('Super90_Foregrip_Saddle')])
    gx,gy=76,16;contacts={};cells=[]
    for ix in range(gx+1):
        for iy in range(gy+1):
            x=-.057+.114*ix/gx;y=-.0075+.015*iy/gy
            hit=bodytree.ray_cast(Vector((x,y,.002)),Vector((0,0,-1)),.011)[0]
            if hit is not None:contacts[(ix,iy)]=(x,y,min(0.,hit.z)-.00015)
    for ix in range(gx):
        for iy in range(gy):
            cell=[(ix,iy),(ix+1,iy),(ix+1,iy+1),(ix,iy+1)]
            if all(p in contacts for p in cell) and max(-contacts[p][2] for p in cell)>.0003:cells.append(cell)
    if cells:
        used=sorted({p for cell in cells for p in cell});ids={p:i for i,p in enumerate(used)};count=len(used)
        sv=[contacts[p] for p in used]+[(contacts[p][0],contacts[p][1],.00015) for p in used];sf=[];edges={}
        for cell in cells:
            ind=[ids[p] for p in cell];sf.extend([tuple(reversed(ind)),tuple(i+count for i in ind)])
            for a,b in zip(ind,ind[1:]+ind[:1]):
                edge=tuple(sorted((a,b)))
                if edge in edges:edges[edge]=None
                else:edges[edge]=(a,b)
        for edge in edges.values():
            if edge:
                a,b=edge;sf.append((a,b,b+count,a+count))
        sm=bpy.data.meshes.new('Grip to rail contact');sm.from_pydata(sv,[],sf);sm.update()
        bm=bmesh.new();bm.from_mesh(sm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(sm);bm.free()
        shim=bpy.data.objects.new('Closed grip upper interface',sm);bpy.context.collection.objects.link(shim)
        sm.materials.append(next(m for m in body.data.materials if m.name.startswith('Super90_Foregrip_Saddle')))
        for source_uv in body.data.uv_layers:
            uv=sm.uv_layers.new(name=source_uv.name)
            for f in sm.polygons:
                axes=sorted(range(3),key=lambda a:abs(f.normal[a]))[:2]
                for li in f.loop_indices:
                    p=sm.vertices[sm.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
        bpy.ops.object.select_all(action='DESELECT');shim.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    mesh=bpy.data.meshes.new('Native fore-end matched shoe');mesh.from_pydata(lower+upper,[],pad_faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    pad=bpy.data.objects.new('Closed fitted shoe',mesh);bpy.context.collection.objects.link(pad)
    mesh.materials.append(next(m for m in body.data.materials if m.name.startswith('Super90_Foregrip_Saddle')))
    for source_uv in body.data.uv_layers:
        layer=mesh.uv_layers.new(name=source_uv.name)
        for f in mesh.polygons:
            axes=sorted(range(3),key=lambda a:abs(f.normal[a]))[:2]
            for li in f.loop_indices:
                v=mesh.vertices[mesh.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/.04+.5,v[axes[1]]/.04+.5)
    bpy.ops.object.select_all(action='DESELECT');pad.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    body.name='SM_Super90_'+kind;tri=body.modifiers.new('Fitted shoe triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(X/(body.name+'_Editable.blend')))
    fbx=X/(body.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    report['parts'][kind]={'fbx':str(fbx),'slots':[m.name for m in body.data.materials],
        'rail_interface_cells':len(cells),'rail_interface_max_gap_mm':max((-contacts[p][2]*1000 for cell in cells for p in cell),default=0)}
    print('GRIP_SHOE_AUTHORED '+kind,flush=True)
(O/'mounts.json').write_text(json.dumps(report,indent=2))
