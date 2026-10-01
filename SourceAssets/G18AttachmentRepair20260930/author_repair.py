"""G18 magazine shell and measured slide-to-optic interfaces. No preview run."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
record={};icons={}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def export(ob,key):
    select(ob)
    for c in ob.children:
        if c.type=='EMPTY':c.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(E/(ob.name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(E/(ob.name+'_Editable.blend')))
    record[key]['fbx']=str(E/(ob.name+'.fbx'))
    ob.data.calc_loop_triangles()
    icons[key]={'vertices':[list(ob.matrix_world@v.co) for v in ob.data.vertices],'triangles':[list(t.vertices) for t in ob.data.loop_triangles],'uv':[[list(ob.data.uv_layers.active.data[l].uv) for l in t.loops] for t in ob.data.loop_triangles],'material':[t.material_index for t in ob.data.loop_triangles]}

# Keep the factory feed mouth, bottom plate, seating and all contact coordinates.
# The initial author had made disconnected face islands and wound the strip
# against the neighboring shell. Join the matching cut vertices and propagate
# the factory shell orientation across those faces before FBX triangulation.
bpy.ops.wm.open_mainfile(filepath=str(S/'Attachments/SM_G18_ext_mag_Editable.blend'))
ob=bpy.data.objects['SM_G18_ext_mag'];bm=bmesh.new();bm.from_mesh(ob.data)
before=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
open_edges=[e for e in bm.edges if e.is_boundary]
if open_edges:
    bmesh.ops.holes_fill(bm,edges=open_edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
record['ext_mag']={'input':str(S/'Attachments/SM_G18_ext_mag_Editable.blend'),'repair':'weld shared cut rings, close shell seams, outward face winding','merged_vertices':before-len(bm.verts),'filled_boundary_edges':len(open_edges),'remaining_boundary_edges':sum(e.is_boundary for e in bm.edges),'frame':'unchanged skeletal reference','geometry_delta_m':[0,0,0]}
bm.to_mesh(ob.data);bm.free();ob.data.update();export(ob,'ext_mag')

# Express both contact surfaces in the existing attachment frame. Runtime maps
# optic +X to the barrel direction. FBX maps Blender +Y to Unreal -Y.
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];inv=r.data.bones['WPN_root'].matrix_local.inverted()
body=bpy.data.objects['G18_G18'];coords=[inv@v.co for v in body.data.vertices]
slide=BVHTree.FromPolygons(coords,[list(p.vertices) for p in body.data.polygons])
rear=inv@r.data.bones['WPN_RearSight'].head_local
origin=rear+Vector((0,-.016,.0045))

def roof(x,y):
    point=Vector((-y,origin.y-x,.10));hit=slide.ray_cast(point,Vector((0,0,-1)))[0]
    if hit is None:raise RuntimeError('Slide contact surface absent at '+str(point))
    return hit.z-origin.z-.00018

def block_mesh(name,rings,top_bvh):
    # Closed shell with stepped dovetail shoulders. Top and bottom caps use
    # separate structured grids; side faces share the perimeter vertex indices.
    NX=18;NY=12;verts=[];faces=[];perimeters=[]
    for ri,(xmin,xmax,halfwidth,height) in enumerate(rings):
        base=len(verts)
        for i in range(NX+1):
            for j in range(NY+1):
                x=xmin+(xmax-xmin)*i/NX;y=-halfwidth+2*halfwidth*j/NY
                if ri==0:z=roof(x,y)
                elif ri==len(rings)-1:
                    hit=top_bvh.ray_cast(Vector((x,y,-.08)),Vector((0,0,1)))[0]
                    if hit is None:raise RuntimeError('Optic foot absent at '+str((x,y)))
                    z=hit.z+.00020
                else:z=height
                verts.append((x,y,z))
        ix=lambda i,j:base+i*(NY+1)+j
        perimeters.append([ix(i,0) for i in range(NX)]+[ix(NX,j) for j in range(NY)]+[ix(i,NY) for i in range(NX,0,-1)]+[ix(0,j) for j in range(NY,0,-1)])
        if ri in (0,len(rings)-1):
            for i in range(NX):
                for j in range(NY):
                    q=(ix(i,j),ix(i+1,j),ix(i+1,j+1),ix(i,j+1));faces.append(q if ri else q[::-1])
    for a,b in zip(perimeters,perimeters[1:]):
        for k in range(len(a)):n=(k+1)%len(a);faces.append((a[k],a[n],b[n],b[k]))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        for l in p.loop_indices:
            v=mesh.vertices[mesh.loops[l].vertex_index].co;uv.data[l].uv=(v.x/.04,v.y/.04)
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    part=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(part);return part

for key in ('holographic','panoramic_red_dot'):
    bpy.ops.wm.open_mainfile(filepath=str(S/f'Attachments/SM_G18_{key}_Editable.blend'))
    ob=bpy.data.objects['SM_G18_'+key]
    old_adapters={i for i,m in enumerate(ob.data.materials) if 'adapter' in m.name.lower() or 'g18_attachmentfinish' in m.name.lower()}
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in old_adapters],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
    ob.data.calc_loop_triangles()
    materials={i for i,m in enumerate(ob.data.materials) if 'Body' in m.name}
    foot=BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[list(t.vertices) for t in ob.data.loop_triangles if t.material_index in materials],all_triangles=True)
    top_half=.0105 if key=='holographic' else .0073
    # Footprint stays ahead of the original rear sight. Taper the upper seat to
    # each optic's actual bottom width, leaving lens/reticle/AimCenter unchanged.
    rings=[(-.004,.014,.0105,None),(-.004,.014,.0105,-.0059),(-.0036,.0136,.0085,-.0049),(-.004,.014,top_half,-.0029),(-.004,.014,top_half,None)]
    mat=bpy.data.materials.get('M_G18_AttachmentFinish') or bpy.data.materials.new('M_G18_AttachmentFinish')
    saddle=block_mesh('G18_Measured_Dovetail_Seat',rings,foot);saddle.data.materials.append(mat)
    select(saddle);bevel=saddle.modifiers.new('Machined perimeter bevel','BEVEL');bevel.width=.00018;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.45
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    parts=[saddle]
    for x in (.001,.010):
        for side in (-1,1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0009,depth=.00045,location=(x,side*.01055,-.0055),rotation=(math.pi/2,0,0))
            bolt=bpy.context.object;bolt.name='G18_Rail_Clamp_Fastener';bolt.data.materials.append(mat);parts.append(bolt)
    select(ob)
    for p in parts:p.select_set(True)
    bpy.ops.object.join()
    record[key]={'input':str(S/f'Attachments/SM_G18_{key}_Editable.blend'),'repair':'profiled closed adapter, lower surface sampled on G18 slide, upper surface sampled on optic foot','mount_origin_root_m':list(origin),'base_contact_mm':[18,21],'optic_contact_width_mm':2*top_half*1000,'original_optic_and_aim_center_preserved':True,'surface_embed_mm':.2}
    export(ob,key)
(O/'authoring.json').write_text(json.dumps(record,indent=2))
(O/'icon_geometry.json').write_text(json.dumps(icons,separators=(',',':')))
print('G18_ATTACHMENT_REPAIR_AUTHORED',flush=True)
