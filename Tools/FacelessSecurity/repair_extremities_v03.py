"""Keep complete exposed extremities and rebuild watertight duty boots.

The V01 open foot shell was voxel remeshed before its ankle was capped,
which discarded almost all of its upper. Cap the volume first, then open
the finished ankle. Preserve the rest of the accepted security clothing.
"""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
ROOT=BASE.parent/'V03'
for d in ['Authoring','Delivery','Motion']:(ROOT/d).mkdir(parents=True,exist_ok=True)
# Recover the exact original anatomical fit and source surface without
# rerunning any garment or material authoring.
prefix=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_character.py').read_text(encoding='utf-8').split('# Appended to the native skeleton')[0]
ns={};exec(compile(prefix,'security_fit_inputs','exec'),ns)
MAP={k:v.copy() for k,v in ns['MAP'].items()};TARGET=ns['TARGET'];body_sample=ns['body_sample'];matrix=ns['matrix']
source_vertices=[tuple(v.co) for v in ns['body'].data.vertices]
source_faces=[tuple(p.vertices) for p in ns['body'].data.polygons]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/FacelessSecurity_V01.blend'))
rig=bpy.data.objects['root'];rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
body=bpy.data.objects['Security_CompleteBody'];old_display=bpy.data.objects['Security_OutfitBody']
leather=bpy.data.materials['Security_Leather'];trim=bpy.data.materials['Security_Trim'];hardware=bpy.data.materials['Security_Hardware']

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def smoothstep(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def uv(o):
    layer=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
    for f in o.data.polygons:
        for li in f.loop_indices:
            p=o.data.vertices[o.data.loops[li].vertex_index].co
            layer.data[li].uv=(p.y/.20,p.z/.20) if abs(f.normal.x)>.5 else (p.x/.20,p.z/.20)
        f.use_smooth=True
def make(name,verts,faces,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);uv(o);return o
def foot_weights(p,side,sole=False):
    if sole:return {'foot_'+side:1.}
    # A duty boot keeps its toe box intact. Only the flexible upper ankle
    # gradually follows the calf; finger or opposite-leg weights are excluded.
    calf=.65*smoothstep(.105,.235,p.z)
    return {'foot_'+side:1-calf,'calf_'+side:calf}
def bind(o,side,sole=False):
    o.vertex_groups.clear();o.modifiers.clear()
    for n in ['foot_'+side,'calf_'+side]:o.vertex_groups.new(name=n)
    for v in o.data.vertices:
        ws=foot_weights(v.co,side,sole);v.co=matrix(ws).inverted()@v.co
        for n,w in ws.items():
            if w>0:o.vertex_groups[n].add([v.index],w,'REPLACE')
    o.data.update()
    # Geometry normals are rebuilt after inverse fitting instead of keeping
    # normals belonging to the previously collapsed surface.
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    m=o.modifiers.new('NativeHumanoidSkin','ARMATURE');m.object=rig

# Reconstruct the displayed body from the intact already bound body. Surface
# decisions are made in the source authoring pose, with full wrist overlap
# and feet retained underneath the separately made boots.
display=body.copy();display.data=body.data.copy();bpy.context.collection.objects.link(display)
display.name='Security_OutfitBody_V03';display.hide_render=False;display.hide_set(False)
groups={g.index:g.name for g in display.vertex_groups}
src=[]
for v in display.data.vertices:
    ws={groups[g.group]:g.weight for g in v.groups};p=matrix(ws)@v.co;src.append(p)
    if p.z<.25:
        side='l' if p.x>=0 else 'r';new=foot_weights(p,side)
        for g in list(v.groups):display.vertex_groups[g.group].remove([v.index])
        for n,w in new.items():
            group=display.vertex_groups.get(n) or display.vertex_groups.new(name=n)
            if w>0:group.add([v.index],w,'REPLACE')
        v.co=matrix(new).inverted()@p
bm=bmesh.new();bm.from_mesh(display.data);bm.verts.ensure_lookup_table()
remove=[]
for f in bm.faces:
    c=sum((src[v.index] for v in f.verts),Vector())/len(f.verts)
    side='l' if c.x>=0 else 'r';w=Vector(TARGET[side]['wrist']);e=Vector(TARGET[side]['elbow'])
    wrist=(c-w).dot((w-e).normalized())
    if not (c.z>1.628 or (abs(c.x)>.29 and .65<c.z<1.14 and wrist>-.055) or c.z<.23):remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(display.data);bm.free();bpy.data.objects.remove(old_display,do_unlink=True);display.name='Security_OutfitBody'

for o in list(bpy.context.scene.objects):
    if o.name.startswith(('Security_Boot_','Security_BootSole_','Security_BootWelt_','Security_BootLaces_','Security_BootEyelet_')):bpy.data.objects.remove(o,do_unlink=True)
boot_report={}
for side,sign in [('l',1),('r',-1)]:
    me=bpy.data.meshes.new('ClosedFootInput_'+side);me.from_pydata(source_vertices,[],source_faces);me.update()
    o=bpy.data.objects.new('Security_Boot_'+side,me);bpy.context.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if any(sign*v.co.x<.06 for v in f.verts)],context='FACES')
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,.245),plane_no=(0,0,1),clear_outer=True)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
    # Close all open loops before volume remeshing.
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:
        v.co+=v.normal*.014;v.co.z=max(.024,v.co.z)
    bm.to_mesh(me);bm.free()
    rem=o.modifiers.new('ClosedLeatherVolume','REMESH');rem.mode='VOXEL';rem.voxel_size=.0045;rem.use_smooth_shade=True;apply(o,rem)
    sm=o.modifiers.new('LeatherLastSmooth','SMOOTH');sm.factor=.35;sm.iterations=5;apply(o,sm)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,.225),plane_no=(0,0,1),clear_outer=True)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    dec=o.modifiers.new('BootSurfaceBudget','DECIMATE');dec.ratio=.28;apply(o,dec)
    o.data.materials.append(leather);uv(o)
    solid=o.modifiers.new('LeatherThickness','SOLIDIFY');solid.thickness=.003;solid.offset=-1;apply(o,solid)
    pts=np.array([v.co for v in o.data.vertices]);boot_report[side]={'authoring_bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'vertices':len(pts)}
    # Sole perimeter is the footprint of the real source surface, sampled
    # radially in plan view; it is independent of an open-mesh ray miss.
    center=np.array([sign*.226,.010]);low=pts[pts[:,2]<.075]
    outline=[];N=80
    for i in range(N):
        t=2*math.pi*i/N;d=np.array([math.sin(t),-math.cos(t)]);q=low[:,:2]-center
        along=q@d;cross=np.abs(q[:,0]*d[1]-q[:,1]*d[0]);valid=along[(cross<.015)&(along>0)]
        radius=(float(np.max(valid)) if len(valid) else .065)+.003
        outline.append(center+d*radius)
    # Smooth only the outline to remove scanline stair steps.
    a=np.array(outline)
    for _ in range(3):a=(np.roll(a,1,0)+2*a+np.roll(a,-1,0))/4
    verts=[(float(p[0]),float(p[1]),z) for z in [.002,.010,.036] for p in a]
    faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(2) for i in range(N)]
    faces+=[tuple(reversed(range(N))),tuple(2*N+i for i in range(N))]
    sole=make('Security_BootSole_'+side,verts,faces,trim)
    # Small leather tongue and lace crossbars use the rebuilt front surface.
    o.data.calc_loop_triangles()
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromPolygons([v.co.copy() for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
    for j,z in enumerate(np.linspace(.095,.207,7)):
        paths=[]
        for k,x in enumerate([sign*.205-.024,sign*.205+.024]):
            h=tree.ray_cast(Vector((x,-.5,float(z))),Vector((0,1,0)),.8)
            if h[0] is None:continue
            paths.append(h[0]+Vector((0,-.004,0)))
        if len(paths)!=2:continue
        d=(paths[1]-paths[0]).normalized();up=Vector((0,0,1));depth=d.cross(up).normalized()
        vv=[tuple(p+up*sz*.0015+depth*sy*.0015) for p in paths for sz,sy in [(-1,-1),(-1,1),(1,1),(1,-1)]]
        lace=make('Security_BootLaces_'+side+'_'+str(j),vv,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(3,2,1,0),(4,5,6,7)],trim);bind(lace,side)
    bind(o,side);bind(sole,side,True)
body.hide_set(True);body.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V03.blend'))
(ROOT/'geometry_repair.json').write_text(json.dumps({'boots':boot_report,'body_display_triangles':sum(len(p.vertices)-2 for p in display.data.polygons),'source_body_preserved':True,'hands':'Full fingers, palms and 5.5 cm proximal wrist overlap retained','feet':'Body feet retained under rebuilt closed-volume leather boots','other_garments':'Preserved V01','rendered':False,'game_tested':False},indent=2))
# Reuse the established mesh exporter, changing only the authoring revision.
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V03')
exec(compile(src,'export_security_v03','exec'))
