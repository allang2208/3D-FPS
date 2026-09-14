"""Fit accepted pistol optics/devices to the actual 715 barrel shroud.
No animation changes or preview renders. All dimensions below are author metres.
"""
import ast, bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
rig=bpy.data.objects['SK_DW715_Manny'];root=rig.data.bones['WPN_root'].matrix_local.copy();inv=root.inverted()
barrel=bpy.data.objects['DW715_BarrelShroud']
surface=BVHTree.FromPolygons([inv@v.co for v in barrel.data.vertices],[list(p.vertices) for p in barrel.data.polygons])
bpy.ops.wm.read_factory_settings(use_empty=True)
report={}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def subset(ob,keep):
    """Remove the old pistol saddle without losing surviving corner normals/UVs."""
    old=ob.data;polys=[p for p in old.polygons if keep(old.materials[p.material_index].name)]
    ids=sorted({v for p in polys for v in p.vertices});mapping={v:i for i,v in enumerate(ids)}
    loops=[i for p in polys for i in p.loop_indices];normals=[old.corner_normals[i].vector.copy() for i in loops]
    me=bpy.data.meshes.new(ob.name+'_Fitted');me.from_pydata([old.vertices[i].co for i in ids],[],[[mapping[i] for i in p.vertices] for p in polys]);me.update()
    for m in old.materials:me.materials.append(m)
    for p,q in zip(me.polygons,polys):p.material_index=q.material_index;p.use_smooth=q.use_smooth
    for uv in old.uv_layers:
        layer=me.uv_layers.new(name=uv.name)
        for i,j in enumerate(loops):layer.data[i].uv=uv.data[j].uv
    for color in old.color_attributes:
        layer=me.color_attributes.new(name=color.name,type=color.data_type,domain=color.domain)
        for i,j in enumerate(loops if color.domain=='CORNER' else ids):layer.data[i].color=color.data[j].color
    me.normals_split_custom_set(normals);ob.data=me

def physical_uv(ob,index):
    while len(ob.data.uv_layers)<=index:ob.data.uv_layers.new(name='UV'+str(len(ob.data.uv_layers)))
    layer=ob.data.uv_layers[index];layer.name='DW715FinishUV'
    for p in ob.data.polygons:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in p.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/.1+.5,v[axes[1]]/.1+.5)

def solid(name,verts,faces,mat,uvname):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mat)
    physical_uv(ob,0);me.uv_layers[0].name=uvname
    color=me.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');me.color_attributes.active_color=color
    for c in color.data:c.color=(1,0,1,1)
    select(ob);bevel=ob.modifiers.new('Rounded machined edges','BEVEL');bevel.width=.00022;bevel.segments=3;bevel.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob

def bridge(name,length,bottom_width,top_width,z_top,contact,mat,uvname,center_x=0):
    nx,ny=16,6;top=[];bottom=[]
    for ix in range(nx+1):
        for iy in range(ny+1):
            x=center_x+(ix/nx-.5)*length;by=(iy/ny-.5)*bottom_width
            top.append((x,(iy/ny-.5)*top_width,z_top));bottom.append((x,by,contact(x,by)))
    count=len(top);faces=[]
    for ix in range(nx):
        for iy in range(ny):
            a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
            faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
    edge=list(range(ny+1))+[ix*(ny+1)+ny for ix in range(1,nx+1)]+[nx*(ny+1)+iy for iy in range(ny-1,-1,-1)]+[ix*(ny+1) for ix in range(nx-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
    return solid(name,top+bottom,faces,mat,uvname)

def export(ob,key,sockets,uv_index,info):
    select(ob);physical_uv(ob,uv_index);ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    folder=O/key;folder.mkdir(exist_ok=True)
    for name,point in sockets.items():
        empty=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(empty);empty.parent=ob;empty.location=point;empty.select_set(True)
    file=folder/('SM_TacticalDevice.fbx' if key in ['laser','flashlight'] else 'SM_DW715_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    report[key]=dict(fbx=str(file),uv_index=uv_index,slots=[m.name for m in ob.data.materials],
                     bounds_m={'min':[min(v.co[i] for v in ob.data.vertices) for i in range(3)],'max':[max(v.co[i] for v in ob.data.vertices) for i in range(3)]},sockets_m={k:list(v) for k,v in sockets.items()},**info)
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'DW715_Attachment_Editable.blend'))
    print('DW715_ATTACHMENT_AUTHORED',key,flush=True)

for key in ['holographic','panoramic_red_dot']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src=S/('M1911CompactFit20260913/FBX/holographic.fbx' if key=='holographic' else 'M1911SculptedMount20260913/SM_M1911_panoramic_red_dot.fbx')
    bpy.ops.import_scene.fbx(filepath=str(src));ob=next(x for x in bpy.context.scene.objects if x.type=='MESH')
    for x in list(bpy.context.scene.objects):
        if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
    subset(ob,lambda name:'AdapterSteel' not in name);ob.name='SM_DW715_'+key
    # Existing compact body: 0.55 holographic / 0.62 panoramic. Enlarge only
    # the holo reticle; panoramic already has the accepted 1.395 mm red dot.
    aim=Vector((-.003595801,0,.028464282) if key=='holographic' else (.013175,0,.02015))
    reticle_scale=1.35 if key=='holographic' else 1.
    ids={v for p in ob.data.polygons if 'Reticle' in ob.data.materials[p.material_index].name for v in p.vertices}
    normals=[n.vector.copy() for n in ob.data.corner_normals]
    for i in ids:
        v=ob.data.vertices[i].co;v.y=aim.y+(v.y-aim.y)*reticle_scale;v.z=aim.z+(v.z-aim.z)*reticle_scale
    for i,loop in enumerate(ob.data.loops):
        if loop.vertex_index in ids:normals[i].y/=reticle_scale;normals[i].z/=reticle_scale;normals[i].normalize()
    ob.data.update();ob.data.normals_split_custom_set(normals)
    mount_z=.0615;mount_y=-.120
    def contact(x,y):
        hit=surface.ray_cast(Vector((y,mount_y-x,.12)),Vector((0,0,-1)),.2)[0]
        if hit is None:raise RuntimeError('Missing 715 upper shroud contact')
        return hit.z-mount_z-.00012
    adapter=bpy.data.materials.new('DW715_AdapterSteel')
    saddle=bridge('DW715_UpperShroudSaddle',.049 if key=='holographic' else .037,.011,.025 if key=='holographic' else .023,0,contact,adapter,ob.data.uv_layers[0].name)
    select(ob);saddle.select_set(True);bpy.ops.object.join()
    export(ob,key,{'AimCenter':aim,'MountForward':Vector((.03,0,0)),'MountUp':Vector((0,0,.03))},3,
           dict(source=str(src),mount_root_m=[0,mount_y,mount_z],body_scale=.55 if key=='holographic' else .62,reticle_additional_scale=reticle_scale,panoramic_dot_diameter_m=.001395 if key=='panoramic_red_dot' else None))

device_auth=json.loads((S/'M1911CompactFit20260913/tactical_authoring.json').read_text())
for key in ['laser','flashlight']:
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911CompactFit20260913'/key/'M1911_Device_Editable.blend'))
    ob=bpy.data.objects['SM_TacticalDevice']
    for x in list(bpy.context.scene.objects):
        if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
    subset(ob,lambda name:'Collar' not in name)
    # Keep the accepted compact body and optical mask; move it clear of the
    # ejector/front-hand region. The new saddle samples this gun's underside.
    offset=Vector((0,-.051,.023));ob.data.transform(Matrix.Translation(offset));ob.data.update()
    emitter=Vector(device_auth[key]['emitter_blender_m'])+offset
    device_surface=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
    nx,ny=6,14;top=[];bottom=[]
    for iy in range(ny+1):
        for ix in range(nx+1):
            x=(ix/nx-.5)*.010;y=-.145+(iy/ny-.5)*.026
            upper=surface.ray_cast(Vector((x,y,-.10)),Vector((0,0,1)),.25)[0]
            lower=device_surface.ray_cast(Vector((x,y,.10)),Vector((0,0,-1)),.2)[0]
            if upper is None:raise RuntimeError('Missing 715 lower shroud contact')
            top.append((x,y,upper.z+.00012));bottom.append((x,y,lower.z-.00012 if lower else None))
    valid=[p for p in bottom if p[2] is not None]
    if not valid:raise RuntimeError('No tactical-body contact under 715')
    bottom=[p if p[2] is not None else (p[0],p[1],min(valid,key=lambda q:(q[0]-p[0])**2+(q[1]-p[1])**2)[2]) for p in bottom]
    count=len(top);faces=[]
    for iy in range(ny):
        for ix in range(nx):
            a=iy*(nx+1)+ix;b=a+1;c=b+nx+1;d=a+nx+1;faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
    edge=list(range(nx+1))+[iy*(nx+1)+nx for iy in range(1,ny+1)]+[ny*(nx+1)+ix for ix in range(nx-1,-1,-1)]+[iy*(nx+1) for iy in range(ny-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
    collar=bpy.data.materials.new('DW715_Tactical_Collar');saddle=solid('DW715_LowerShroudSaddle',top+bottom,faces,collar,ob.data.uv_layers[0].name)
    select(ob);saddle.select_set(True);bpy.ops.object.join()
    export(ob,key,{'Emitter':emitter,'AimGuide':emitter+Vector((0,-.03,0))},1,
           dict(source=device_auth[key]['source'],source_compact=str(S/'M1911CompactFit20260913'/key/'M1911_Device_Editable.blend'),body_scale=device_auth[key]['body_scale'],offset_m=list(offset),mount_root_m=[0,0,0],source_forward='author -Y / UE +Y'))

# Bake a dedicated 10 cm coating tile from the current 715 metal author graph.
# This tile replaces only coating color/ORM; original UV0 structure normals stay.
bpy.ops.wm.read_factory_settings(use_empty=True)
tree=ast.parse((S/'DanWesson715MetalFinish20260914/bake_finish.py').read_text())
parts=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='author_material' or isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FINISH' for t in x.targets)]
exec(compile(ast.Module(body=parts,type_ignores=[]),'715_finish_author_material','exec'))
mat=author_material('Frame',False);bpy.ops.mesh.primitive_plane_add(size=.1);plane=bpy.context.object;plane.data.materials.append(mat)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_selected_to_active=False;s.render.bake.margin=8
nodes=mat.node_tree.nodes;links=mat.node_tree.links;output=next(x for x in nodes if x.type=='OUTPUT_MATERIAL');em=nodes.new('ShaderNodeEmission');target=nodes.new('ShaderNodeTexImage');nodes.active=target
folder=O/'Textures';folder.mkdir(exist_ok=True);textures={}
for kind in ['BaseColor','ORM']:
    image=bpy.data.images.new('T_DW715_Attachment_'+kind,width=1024,height=1024,alpha=False);image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';target.image=image
    value=nodes[mat['base_node']].outputs[mat['base_socket']] if kind=='BaseColor' else nodes[mat['orm_node']].outputs[0]
    links.new(value,em.inputs[0]);links.new(em.outputs[0],output.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(folder/(image.name+'.png'));image.file_format='PNG';image.save();textures[kind]=image.filepath_raw
links.new(next(x for x in nodes if x.type=='BSDF_PRINCIPLED').outputs[0],output.inputs['Surface'])
(O/'finish.json').write_text(json.dumps({'textures':textures,'physical_tile_m':.1,'reference':'DanWesson715MetalFinish20260914/Frame','normal_policy':'Retain original structural UV0 normals'},indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DW715_AttachmentFinish_Editable.blend'))
print('DW715_ATTACHMENTS_SOURCE_COMPLETE',flush=True)
