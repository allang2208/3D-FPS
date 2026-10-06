"""V2 gun-specific mounts for the approved blessed emitter.

Host geometry is the exported current runtime weapon in its attachment frame.
No old laser body or curved body collar is imported. M16's actual handguard
bands are retained explicitly; RSH's rail interface is rebuilt as an offset
bracket. Metres, canonical +X optical axis / +Z mounting direction.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model';R=O/'MountRepair'
SPECS={
    'M4':(-.055,-.032,-.010,.001),
    'AKM':(-.057,-.033,-.008,.008),
    'QBZ191':(-.057,-.032,-.012,-.004),
    'M1911':(-.058,-.032,-.009,.009),
    'G18':(-.058,-.032,-.009,.009),
    'PitViper2011':(-.062,-.043,-.012,.012),
    'DanWesson715':(-.054,-.027,-.005,.005),
    'ASH12':(-.057,-.032,-.008,.008),
    'A762':(-.057,-.030,-.008,.008),
    'SVD':(-.058,-.020,-.012,-.004),
    'PKM':(-.055,-.030,.001,.011),
    'LMG201':(-.066,-.054,-.008,.004),
    'HK416':(-.068,-.047,-.010,-.003),
}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def solid(name,vertices,faces,mat,bevel=0):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if bevel:
        select(ob);m=ob.modifiers.new('Machined edge radius','BEVEL');m.width=bevel;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
    return ob

def taper(name,bottom,top,mat,bevel=0):
    # Bounds per layer: x0,x1,y0,y1,z; finite surfaces interlock at the seat.
    vertices=[]
    for x0,x1,y0,y1,z in (bottom,top):vertices.extend([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)])
    return solid(name,vertices,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,bevel)

def box(name,bounds,mat,bevel=0):
    x0,x1,y0,y1,z0,z1=bounds
    return taper(name,(x0,x1,y0,y1,z0),(x0,x1,y0,y1,z1),mat,bevel)

def uv_map(ob):
    # A contact quad can straddle a rail step. Project each exported triangle
    # independently so the steep half cannot collapse its tangent UVs.
    select(ob);tri=ob.modifiers.new('Contact UV triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    mesh=ob.data;uv=mesh.uv_layers.new(name='SurfaceUV')
    for face in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.015,p[axes[1]]/.015)

def sample_pad(tree,bounds,s):
    x0,x1,y0,y1=bounds;nx=max(4,math.ceil((x1-x0)/.001));ny=max(4,math.ceil((y1-y0)/.001))
    rows=[]
    for ix in range(nx+1):
        for iy in range(ny+1):
            x=x0+(x1-x0)*ix/nx;y=y0+(y1-y0)*iy/ny
            hit=tree.ray_cast(Vector((x,y,.0185*s)),Vector((0,0,1)),.12)[0]
            rows.append([x,y,hit.z if hit else None])
    heights=sorted(p[2] for p in rows if p[2] is not None)
    if not heights:raise RuntimeError('Host contact footprint misses the firearm')
    # A shoe spans rail grooves and openings; it must not sprout deep spikes
    # into an opening's far wall. Its outer mating surface follows the host.
    floor=heights[0];ceiling=floor+.004*s
    for p in rows:p[2]=min(p[2],ceiling) if p[2] is not None else floor
    return rows,nx,ny,floor

def contact_pad(name,rows,nx,ny,base,mat):
    n=len(rows);vertices=[(x,y,base) for x,y,z in rows]+[(x,y,z+.00012) for x,y,z in rows];faces=[]
    for ix in range(nx):
        for iy in range(ny):
            a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
            faces.extend([(a,b,c,d),(d+n,c+n,b+n,a+n)])
    perimeter=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
    faces.extend((a,a+n,b+n,b) for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]))
    return solid(name,vertices,faces,mat)

def bolt(name,x,y,z,s,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0016*s,depth=.0008*s,location=(x,y,z),rotation=(math.pi/2,0,0))
    ob=bpy.context.object;ob.name=name;ob.data.materials.append(mat);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bevel=ob.modifiers.new('Fastener edge','BEVEL');bevel.width=.00012*s;bevel.segments=2;bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob

def rsh_offset(emitter,frame,mat,black,s):
    # These are the native narrow RSH rail and web coordinates. The old
    # circular-body saddle is deliberately absent; the new ledge meets the
    # blessed body's flat keyed block, including the rearward longitudinal gap.
    def native(name,vertices,faces):return solid(name,[frame.transposed()@(Vector(p)-emitter) for p in vertices],faces,mat,.00015)
    def extrude(name,x0,x1,section):
        n=len(section);v=[(x,y,z) for x in (x0,x1) for y,z in section]
        return native(name,v,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
    for sign in (-1,1):extrude('RSH narrow rail jaw',-.0075,.0075,[(sign*y,z) for y,z in ((.00829,-.001),(.0107,-.001),(.0107,.0019),(.0093,.0034),(.00829,.0018))])
    extrude('RSH under-rail bearing',-.0075,.0075,[(-.0107,-.004),(.0107,-.004),(.0107,0),(-.0107,0)])
    extrude('RSH continuous offset web',-.0075,.0075,[(-.009,-.004),(-.025,-.004),(-.025,.0355),(-.0215,.0355),(-.0215,.0005),(-.009,.0005)])
    taper('RSH keyed cantilever',(-.055*s,-.034*s,-.0065*s,.0065*s,.0175*s),(-.054*s,-.011,-.005,.003,.0180),mat,.00022)
    # Root of the cantilever overlaps the web; no disconnected front endpoint.
    box('RSH ledge into offset web',(-.027,-.010,-.005,.003,.0165,.0180),mat,.00016)
    for x in (-.004,.004):
        p=frame.transposed()@(Vector((x,-.0254,.013))-emitter)
        # Screws face the same side as the native bracket, along canonical Z.
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0016,depth=.0012,location=p)
        ob=bpy.context.object;ob.name='RSH web fastener';ob.data.materials.append(black);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

def retained_m16(e,emitter,frame):
    with bpy.data.libraries.load(str(R/'Inputs/BlessedLaser_M16_mount_source.blend'),link=False) as (src,dst):dst.objects=['SM_BlessedLaser_M16']
    ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.name='M16 original handguard bands and bearing'
    bm=bmesh.new();bm.from_mesh(ob.data)
    # Explicit material identity names the old curved device collar. Other
    # source pieces are the two handguard bands and their actual bearing plate.
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if ob.data.materials[f.material_index].name.startswith('Blessed') or 'MI_M16_R01_mount_dd24f6556b' in ob.data.materials[f.material_index].name],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
    ob.data.transform(frame.transposed().to_4x4()@Matrix.Translation(-emitter)@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
    return ob

def run():
    base=json.loads((R/'Inputs/authoring-v1.json').read_text());plans=json.loads((R/'surface_plan.json').read_text());report={};(R/'Editable').mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    for family,e in base.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        emitter=Vector(e['emitter_blender_m']);f=Vector(e['forward_blender']);up=Vector(plans[family]['up']);frame=Matrix((f,up.cross(f),up)).transposed();s=e['scale']
        with bpy.data.libraries.load(str(O/'BlessedLaser_GameMaster.blend'),link=False) as (src,dst):dst.objects=['SM_BlessedLaser_Master']
        body=dst.objects[0];bpy.context.collection.objects.link(body);body.name='Approved sealed emitter body';body.data.transform(Matrix.Scale(s,4))
        mats={m.name:m for m in body.data.materials};graphite=mats['Blessed_Graphite'];black=mats['Blessed_Black'];retained={};contact={}
        geo=json.loads((R/'Hosts'/(family+'-geometry.json')).read_text());tree=BVHTree.FromPolygons([frame.transposed()@(Vector(v)-emitter) for v in geo['vertices']],geo['faces'])
        if family=='RSH12':
            rsh_offset(emitter,frame,graphite,black,s);contact={'kind':'native narrow rail jaws, continuous offset web, flat keyed cantilever'}
        else:
            if family=='M16':
                kept=retained_m16(e,emitter,frame)
                # The inherited combined mesh carries abandoned UV sets. The
                # retained strap geometry now shares the new graphite finish
                # and one physical UV set, rather than exporting nine channels.
                kept.data.materials.clear();kept.data.materials.append(graphite)
                for face in kept.data.polygons:face.material_index=0
                for uv in list(kept.data.uv_layers):kept.data.uv_layers.remove(uv)
                # Native strap-bearing underside, sampled from the retained
                # interface itself, not the old collar's overall bounds.
                tree=BVHTree.FromPolygons([v.co for v in kept.data.vertices],[list(p.vertices) for p in kept.data.polygons])
                bounds=tuple(v*s for v in (-.055,-.032,-.008,.008))
            else:bounds=tuple(v*s for v in SPECS[family])
            footprints=[bounds]
            if family=='SVD':footprints=[tuple(v*s for v in b) for b in [(-.058,-.050,-.012,-.004),(-.027,-.020,-.012,-.004)]]
            samples=[sample_pad(tree,b,s) for b in footprints];base_z=min(p[3] for p in samples)-.0024*s
            x0,x1,y0,y1=bounds
            # Flat dovetail receiver interlocks 0.35 mm into the approved key.
            box('Keyed seat gasket',(-.056*s,-.034*s,-.0070*s,.0070*s,.01745*s,.0184*s),black,.00016*s)
            taper('Solid tapered attachment neck',(-.055*s,-.035*s,-.0065*s,.0065*s,.0181*s),(x0+.0005*s,x1-.0005*s,y0+.0005*s,y1-.0005*s,base_z+.00035*s),graphite,.00025*s)
            box('Upper clamp crossbar',(x0,x1,y0,y1,base_z-.0004*s,base_z+.0008*s),graphite,.00016*s)
            for i,(rows,nx,ny,floor) in enumerate(samples):contact_pad('Host matched contact pad '+str(i+1),rows,nx,ny,base_z,graphite)
            for side,y in ((-1,y0),(1,y1)):
                for x in (x0+(x1-x0)*.25,x0+(x1-x0)*.75):bolt('Captive clamp bolt',x,y-side*.00015*s,base_z+.00065*s,s,black)
            contact={'kind':'host surface fitted closed clamp' if family!='M16' else 'original handguard bands with new keyed closed neck','footprints_m':footprints,'contact_height_min_m':[p[3] for p in samples],'shoe_base_m':base_z}
        # New source objects retain editable independent mechanical parts.
        for ob in list(bpy.context.scene.objects):
            if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True);continue
            if ob!=body:uv_map(ob)
        bpy.ops.wm.save_as_mainfile(filepath=str(R/'Editable'/('BlessedLaser_'+family+'_MountV2.blend')))
        objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:ob.select_set(True)
        bpy.context.view_layer.objects.active=body;bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SM_BlessedLaser_'+family
        mesh.data.transform(Matrix.Translation(emitter)@frame.to_4x4());select(mesh);bpy.ops.object.material_slot_remove_unused()
        tri=mesh.modifiers.new('Explicit game triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
        for name,pos in e['sockets_ue_cm'].items():
            sock=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(sock);sock.parent=mesh;sock.location=(pos[0]/100,-pos[1]/100,pos[2]/100);sock.select_set(True)
        path=O/'Exports'/('SM_BlessedLaser_'+family+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(O/'Fitted'/('BlessedLaser_'+family+'.blend')))
        mesh.data.calc_loop_triangles()
        report[family]={**e,'fbx':str(path),'up_blender':list(up),'retained_materials':retained,'slots':[m.name for m in mesh.data.materials],'triangles':len(mesh.data.loop_triangles),'contact_geometry':contact,'mount_revision':2,'host_source':str(R/'Hosts'/(family+'-geometry.json')),'legacy_body_fragments_retained':False}
        print('BLESSED_MOUNT_V2_EXPORTED',family,flush=True)
    (O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(R/'mount-v2-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':run()
