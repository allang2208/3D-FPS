"""Fit accepted compact game devices to a new RSH right-side offset bracket.
Keep device geometry, UVs and optical masks; author only the mounting hardware.
No renders, gameplay or acceptance tests.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

O=Path(__file__).resolve().parent;S=O.parent
(O/'Exports').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
source=json.loads((S/'M1911CompactFit20260913/tactical_authoring.json').read_text())
raw=json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text())
alignment=Matrix(json.loads((S/'RSH12Speedloader20261003/Single/authoring.json').read_text())['alignment'])
# Author +X forward, -Y shooter's right; FBX changes Y to UE +Y right.
seat=Vector((0,-.1395,.0194712))
to_canonical=Matrix(((0,1,0,seat.x),(-1,0,0,seat.y),(0,0,1,seat.z),(0,0,0,1)))
reflect=Matrix.Diagonal((1,-1,1,1))
native=reflect@alignment
point=native@seat
forward=(native.to_3x3()@Vector((0,-1,0))).normalized()
up=(native.to_3x3()@Vector((0,0,1))).normalized()
report={'parts':{},'mount':{'root_point_m':list(point),'root_forward':list(forward),'root_up':list(up)},
 'rail_center_canonical_m':list(seat),'rail_width_m':.016536,'side':'right from shooter viewpoint',
 'source_body':'M1911CompactFit20260913; existing accepted compact laser and flashlight',
 'source_contact':'Rsh-12 by Medji, CC BY 4.0; Docs/ThirdParty/RSH12-Medji-CCBY4.md',
 'runtime_tested':False,'rendered':False}

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def body_only(ob):
    old=ob.data
    polys=[p for p in old.polygons if 'Collar' not in old.materials[p.material_index].name]
    ids=sorted({v for p in polys for v in p.vertices});lookup={v:i for i,v in enumerate(ids)}
    loops=[i for p in polys for i in p.loop_indices]
    normals=[old.corner_normals[i].vector.copy() for i in loops]
    me=bpy.data.meshes.new('Accepted_compact_body')
    me.from_pydata([old.vertices[i].co for i in ids],[],[[lookup[i] for i in p.vertices] for p in polys]);me.update()
    me.materials.append(old.materials[polys[0].material_index])
    for p,q in zip(me.polygons,polys):p.use_smooth=q.use_smooth
    for uv in old.uv_layers:
        layer=me.uv_layers.new(name=uv.name)
        for i,j in enumerate(loops):layer.data[i].uv=uv.data[j].uv
    for color in old.color_attributes:
        layer=me.color_attributes.new(name=color.name,type=color.data_type,domain=color.domain)
        for i,j in enumerate(loops if color.domain=='CORNER' else ids):layer.data[i].color=color.data[j].color
        if old.color_attributes.active_color and color.name==old.color_attributes.active_color.name:me.color_attributes.active_color=layer
    me.normals_split_custom_set(normals);ob.data=me

def finish(ob,material,uvnames):
    select([ob]);m=ob.modifiers.new('Machined edge breaks','BEVEL');m.width=.00025;m.segments=3;m.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=m.name)
    ob.data.materials.append(material)
    for name in uvnames:
        uv=ob.data.uv_layers.new(name=name)
        for face in ob.data.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(face.normal[j]))]
            for li in face.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    color=ob.data.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');ob.data.color_attributes.active_color=color
    for c in color.data:c.color=(1,0,1,1)
    return ob

def solid(name,verts,faces,material,uvnames):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    return finish(ob,material,uvnames)

def extrude(name,x0,x1,section,mat,uv):
    n=len(section);v=[(x,y,z) for x in (x0,x1) for y,z in section]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return solid(name,v,f,mat,uv)

def box(name,loc,size,mat,uv):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return finish(ob,mat,uv)

for kind in ('laser','flashlight'):
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911CompactFit20260913'/kind/'M1911_Device_Editable.blend'))
    ob=bpy.data.objects['SM_TacticalDevice']
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    body_only(ob)
    # Original upward clamp faces inward after rolling the body onto the right side.
    rotation=Matrix.Rotation(-math.pi/2,4,'X')@Matrix.Rotation(math.pi/2,4,'Z')
    original_emitter=Vector(source[kind]['emitter_blender_m'])
    emitter=Vector((.010,-.0405,.030))
    transform=Matrix.Translation(emitter-rotation@original_emitter)@rotation
    ob.data.transform(transform);ob.data.update();ob.name='SM_RSH12_'+kind
    bodymat=ob.data.materials[0];bodymat.name='RSH_Tactical_'+kind
    # Match the retained polymer finish in the editable source as well as UE.
    bs=next(n for n in bodymat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    links=bodymat.node_tree.links
    for socket in ('Base Color','Roughness','Metallic'):
        pin=bs.inputs[socket]
        if pin.links and pin.links[0].from_node.type=='MIX_RGB':
            mix=pin.links[0].from_node
            if socket=='Base Color':
                if mix.inputs[1].links:links.new(mix.inputs[1].links[0].from_socket,pin)
                else:links.remove(pin.links[0]);pin.default_value=mix.inputs[1].default_value
            else:
                for link in list(mix.inputs[2].links):links.remove(link)
                value=.56 if socket=='Roughness' else 0
                mix.inputs[2].default_value=(value,value,value,1)
    uv=[u.name for u in ob.data.uv_layers]
    mat=bpy.data.materials.new('RSH_Tactical_Mount');mat.use_nodes=True
    bs_mount=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs_mount.inputs['Base Color'].default_value=(.034746,.034748,.034736,1)
    bs_mount.inputs['Metallic'].default_value=1;bs_mount.inputs['Roughness'].default_value=.473583
    parts=[]
    # The forward-only clamp ends ahead of the existing foregrip seat and hand.
    for sign in (-1,1):
        sec=[(sign*y,z) for y,z in ((.00829,-.001),(.0107,-.001),(.0107,.0019),(.0093,.0034),(.00829,.0018))]
        parts.append(extrude('Narrow rail jaw',-.0075,.0075,sec,mat,uv))
    parts.append(box('Under-rail bearing', (0,0,-.002),(.015,.0214,.004),mat,uv))
    # One continuous chamfered offset web rises outside the shroud's side wall.
    sec=[(-.009,-.004),(-.025,-.004),(-.025,.0355),(-.0215,.0355),(-.0215,.0005),(-.009,.0005)]
    parts.append(extrude('Right offset web',-.0075,.0075,sec,mat,uv))
    # Saddle follows the actual donor body rather than bridging its bounding box.
    surface=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
    nx,nz=8,6;top=[];bottom=[]
    for ix in range(nx+1):
        for iz in range(nz+1):
            x=-.021+ix/nx*.025;z=emitter.z-.005+iz/nz*.010
            hit=surface.ray_cast(Vector((x,0,z)),Vector((0,-1,0)),.10)[0]
            top.append((x,-.0235,z));bottom.append((x,hit.y-.00010 if hit else None,z))
    valid=[v for v in bottom if v[1] is not None]
    if not valid:raise RuntimeError('No donor body contact for '+kind)
    bottom=[p if p[1] is not None else (p[0],min(valid,key=lambda q:(q[0]-p[0])**2+(q[2]-p[2])**2)[1],p[2]) for p in bottom]
    count=len(top);faces=[]
    for ix in range(nx):
        for iz in range(nz):
            a=ix*(nz+1)+iz;b=a+1;c=b+nz+1;d=a+nz+1
            faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
    edge=list(range(nz+1))+[ix*(nz+1)+nz for ix in range(1,nx+1)]+[nx*(nz+1)+iz for iz in range(nz-1,-1,-1)]+[ix*(nz+1) for ix in range(nx-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
    parts.append(solid('Body contact saddle',top+bottom,faces,mat,uv))
    for x in (-.004,.004):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0016,depth=.0012,location=(x,-.0254,.013),rotation=(math.pi/2,0,0))
        screw=bpy.context.object;screw.name='Offset bracket fastener';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        parts.append(finish(screw,mat,uv))
    select([*parts,ob]);bpy.ops.object.join()
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    mod=ob.modifiers.new('Export triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    fbx=O/'Exports'/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    sockets={'Emitter':[emitter.x*100,-emitter.y*100,emitter.z*100],
             'AimGuide':[(emitter.x+.03)*100,-emitter.y*100,emitter.z*100]}
    for name,loc in [('Emitter',emitter),('AimGuide',emitter+Vector((.03,0,0))),('RailContact',Vector((0,0,0)))]:
        empty=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(empty);empty.location=loc;empty.empty_display_size=.005
    bpy.ops.file.pack_all();blend=O/(kind+'_Editable.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report['parts'][kind]={'fbx':str(fbx),'blend':str(blend),'sockets_cm':sockets,'triangles':len(ob.data.polygons),
                          'slots':[m.name for m in ob.data.materials],'source':str(S/'M1911CompactFit20260913'/kind/'M1911_Device_Editable.blend')}
    ref=bpy.data.collections.new('Reference_RSH_DoNotExport');bpy.context.scene.collection.children.link(ref)
    inv=to_canonical.inverted()
    for p in raw:
        if p['name']=='10_l':continue
        me=bpy.data.meshes.new('REF_'+p['name']);me.from_pydata([inv@Vector(v) for v in p['verts']],[],p['faces']);me.update()
        ro=bpy.data.objects.new(me.name,me);ref.objects.link(ro);ro.hide_select=True
    ref.hide_render=True;bpy.ops.wm.save_as_mainfile(filepath=str(O/(kind+'_FitSource.blend')))
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    print('RSH_TACTICAL_AUTHORED',kind,len(ob.data.polygons),flush=True)
