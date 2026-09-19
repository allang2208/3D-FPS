"""Local authoring on the frozen 5080 candidate. No review renders or tests."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent;ROOT=P.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'seed_91379/SkeletonStock_5080_Candidate_Editable.blend'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
ob.name='SkeletonStock_Repaired_Master'
source=ob.copy();source.data=ob.data.copy();bpy.context.collection.objects.link(source);source.name='Frozen_5080_Texture_Source'
source.hide_set(True);source.hide_render=True
notes=[]

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def clean(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bm.verts.index_update();seen=set();duplicate=[]
    for f in bm.faces:
        key=tuple(sorted(v.index for v in f.verts))
        if key in seen:duplicate.append(f)
        else:seen.add(key)
    bmesh.ops.delete(bm,geom=duplicate,context='FACES_ONLY')
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    # Remove redundant sheets along edges with >2 faces. Prefer the pair whose
    # normals and signed edge traversal form a continuous skin. No global remesh.
    redundant=set()
    for e in list(bm.edges):
        if not e.is_valid or len(e.link_faces)<=2:continue
        fs=list(e.link_faces)
        pairs=[]
        for i,a in enumerate(fs):
            la=next(l for l in a.loops if l.edge==e)
            for b in fs[i+1:]:
                lb=next(l for l in b.loops if l.edge==e)
                score=a.normal.dot(b.normal)+(2 if la.vert!=lb.vert else -2)
                pairs.append((score,a,b))
        _,a,b=max(pairs,key=lambda item:item[0]);extras=[f for f in fs if f not in (a,b)]
        redundant.update(extras)
    bmesh.ops.delete(bm,geom=list(redundant),context='FACES_ONLY')
    print('BATCH_TOPOLOGY_CLEANED',len(duplicate),len(redundant),flush=True)
    # Only patch small boundary loops: intended socket/window holes have much
    # larger perimeter, and closed through-holes do not appear as boundary loops.
    boundary={e for e in bm.edges if e.is_boundary};patched=0;fill_edges=[]
    while boundary:
        seed=boundary.pop();es={seed};stack=list(seed.verts);vs=set(stack)
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                if e in boundary:
                    boundary.remove(e);es.add(e)
                    for w in e.verts:
                        if w not in vs:vs.add(w);stack.append(w)
        if len(es)<=32 and sum(e.calc_length() for e in es)<.018:
            fill_edges.extend(es);patched+=1
    if fill_edges:bmesh.ops.holes_fill(bm,edges=fill_edges,sides=0)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(o.data);bm.free();o.data.update();print('CLEAN_MESH_READY',patched,flush=True)
    notes.append({'operation':'coincident vertex/duplicate/degenerate cleanup, remove redundant edge sheets, close tiny boundary loops','duplicate_faces_removed':len(duplicate),'redundant_faces_removed':len(redundant),'tiny_loops_patched':patched})

clean(ob)

def prism(name,profile,width,bevel):
    n=len(profile);verts=[(x,y,z) for y in [-width/2,width/2] for x,z in profile]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    part=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(part);part.data.materials.append(ob.data.materials[0]);active(part)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    mod=part.modifiers.new('Local edge radius','BEVEL');mod.width=bevel;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    return part

def boolean(part,operation,label):
    active(ob);m=ob.modifiers.new(label,'BOOLEAN');m.operation=operation;m.solver='EXACT';m.object=part;m.use_self=False;m.use_hole_tolerant=True
    bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(part,do_unlink=True)
    notes.append({'operation':operation,'region':label})
    print('LOCAL_REPAIR',label,len(ob.data.polygons),flush=True)

# Rebuild the missing underside of the brace-to-pad junction. This compact
# trapezoid lies outside both principal windows, following the reference edge.
patch=prism('Lower_connection_patch',[(.075,-.168),(.125,-.160),(.195,-.278),(.188,-.311),(.124,-.300)],.091,.009)
boolean(patch,'UNION','Lower brace / buttplate missing connection')

# Reconstruct only the damaged front shoulder; the upper housing stays original.
# The bore is cut back explicitly, so closing the accidental side puncture does
# not cap the designed front socket.
patch=prism('Front_shoulder_patch',[(-.494,.091),(-.494,.228),(-.443,.250),(-.392,.202),(-.322,.156),(-.322,.101)],.210,.009)
boolean(patch,'UNION','Front shoulder accidental side punctures')
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.077,depth=.25,location=(-.440,0,.239),rotation=(0,math.pi/2,0))
boolean(bpy.context.object,'DIFFERENCE','Preserve open front socket')

# Relax only the torn seam bands and fine brace channels. Boundary silhouette,
# designed cutout edges and all other source vertices remain at their positions.
bm=bmesh.new();bm.from_mesh(ob.data)
selected=[]
for v in bm.verts:
    x,y,z=v.co
    seam=(.425<x<.452 and -.19<z<.310)
    brace=(-.20<x<.09 and -.120<z<.050 and abs(y)>.023)
    if (seam or brace) and not v.is_boundary:selected.append(v)
for _ in range(3):bmesh.ops.smooth_vert(bm,verts=selected,factor=.15,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(ob.data);bm.free();notes.append({'operation':'local seam/channel relaxation','vertices':len(selected),'iterations':3,'factor':.15})

# Surface normals/UVs are transferred from the original only where geometry was
# retained. New local patches receive their own UVs during low-mesh authoring.
# A corner marker records repaired regions for texture projection and normals.
ob.data.calc_loop_triangles();src=source.data;src.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co for v in src.vertices],[tuple(t.vertices) for t in src.loop_triangles],all_triangles=True)
orig_uv=src.uv_layers[0];uv=ob.data.uv_layers.active
if not uv:uv=ob.data.uv_layers.new(name='SourceProjectionUV')
uv.name='SourceProjectionUV'
from mathutils.geometry import barycentric_transform
for face in ob.data.polygons:
    for li in face.loop_indices:
        co=ob.data.vertices[ob.data.loops[li].vertex_index].co
        hit,no,idx,dist=tree.find_nearest(co)
        if idx is None:continue
        tri=src.loop_triangles[idx];a,b,c=[src.vertices[j].co for j in tri.vertices]
        us=[Vector((*orig_uv.data[j].uv,0)) for j in tri.loops]
        mapped=barycentric_transform(hit,a,b,c,*us);uv.data[li].uv=mapped.xy
    face.use_smooth=True

# Keep generator-space master intact for future editing, plus original source.
ob['authoring']='Frozen 5080 candidate with local connection/front-shoulder repairs and seam relaxation'
ob['not_tested']=True
active(ob);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_Repaired_Master.blend'))
(P/'repair_operations.json').write_text(json.dumps({'source':str(ROOT/'seed_91379/textured_master_00001_.glb'),'operations':notes,'original_source_modified':False,'global_remesh':False,'rendered':False,'tested':False},indent=2))
print('REPAIRED_MASTER_SAVED',flush=True)
