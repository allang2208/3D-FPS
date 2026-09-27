"""Rebuild both adapters with flowing shoulders; optical bodies remain authored."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;slide=bpy.data.objects['M1911_Slide']
surface=BVHTree.FromPolygons([root.inverted()@slide.matrix_world@v.co for v in slide.data.vertices],[list(p.vertices) for p in slide.data.polygons])
def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def mesh_object(name,verts,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    # The contact floor follows a curved slide. Triangulate its non-planar cap
    # and loft quads explicitly before exact machining operations.
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material);return ob
def bevel(ob,width,segments=4):
    select(ob);mod=ob.modifiers.new('Continuous radiused edges','BEVEL');mod.width=width;mod.segments=segments
    mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
def subtract(ob,cutter):
    if not cutter.data.materials:cutter.data.materials.append(ob.data.materials[0])
    select(ob);mod=ob.modifiers.new('Rear sight clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
def outline(hx,hy,r):
    return [(cx+r*math.cos(math.radians(angle+i*90/16)),cy+r*math.sin(math.radians(angle+i*90/16)))
      for cx,cy,angle in [(hx-r,hy-r,0),(-hx+r,hy-r,90),(-hx+r,-hy+r,180),(hx-r,-hy+r,270)] for i in range(16)]
def physical_uv(ob):
    me=ob.data
    while len(me.uv_layers)<4:me.uv_layers.new(name='UV'+str(len(me.uv_layers)))
    for index in [0,3]:
        uv=me.uv_layers[index];uv.name='M1911CoatingPhysicalUV' if index==3 else 'UVMap'
        for p in me.polygons:
            axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(p.normal[k]))]
            for li in p.loop_indices:
                v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.1+.5,v[axes[1]]/.1+.5)
def preserve_body(original,adapter):
    old=original.data;polys=[p for p in old.polygons if p.material_index!=adapter]
    used=sorted({vi for p in polys for vi in p.vertices});mapping={vi:i for i,vi in enumerate(used)}
    me=bpy.data.meshes.new('UnchangedOpticalBody');me.from_pydata([old.vertices[i].co for i in used],[],[[mapping[i] for i in p.vertices] for p in polys]);me.update()
    for mat in old.materials:me.materials.append(mat)
    normals=[]
    for new,prior in zip(me.polygons,polys):
        new.material_index=prior.material_index;new.use_smooth=prior.use_smooth
        normals.extend(old.corner_normals[li].vector.copy() for li in prior.loop_indices)
    for prior in old.uv_layers:
        uv=me.uv_layers.new(name=prior.name)
        for new,oldp in zip(me.polygons,polys):
            for li,oldli in zip(new.loop_indices,oldp.loop_indices):uv.data[li].uv=prior.data[oldli].uv
    for prior in old.color_attributes:
        new=me.color_attributes.new(name=prior.name,type=prior.data_type,domain=prior.domain)
        if prior.domain=='CORNER':
            for p,oldp in zip(me.polygons,polys):
                for li,oldli in zip(p.loop_indices,oldp.loop_indices):new.data[li].color=prior.data[oldli].color
        else:
            for oldvi,newvi in mapping.items():new.data[newvi].color=prior.data[oldvi].color
    me.normals_split_custom_set(normals);original.data=me
def cylinder(name,position,radius,depth,material,segments=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=position,rotation=(math.pi/2,0,0))
    ob=bpy.context.object;ob.name=name;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);ob.data.materials.append(material);return ob
records={}
specs={
 'holographic':{'source':'M1911CompactFit20260913/M1911_CompactOptics_Editable.blend','object':'M1911_holographic',
  'bottom':(.0198,.01065,.0042),'top':(.0275,.01525,.0050),'aim':(-.003595801,0,.0284642816),
  'old_asset':'/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_holographic'},
 'panoramic_red_dot':{'source':'M1911SculptedMount20260913/M1911_SculptedMount_Editable.blend','object':'M1911_panoramic_red_dot',
  'bottom':(.0148,.01045,.0037),'top':(.0182,.01165,.0043),'aim':(.013175,0,.02015),
  'old_asset':'/Game/Weapons/M1911/SculptedMount20260913/Meshes/SM_M1911_panoramic_red_dot'}}
for key,spec in specs.items():
    bpy.ops.wm.open_mainfile(filepath=str(S/spec['source']));original=bpy.data.objects[spec['object']]
    for ob in list(bpy.context.scene.objects):
        if ob!=original:bpy.data.objects.remove(ob,do_unlink=True)
    original.hide_set(False);original.hide_render=False
    adapter=next(i for i,m in enumerate(original.data.materials) if 'AdapterSteel' in m.name);steel=original.data.materials[adapter]
    preserve_body(original,adapter)
    # A smooth loft carries the actual slide footprint into the unchanged optic
    # interface. There is no separate overhanging plate or abrupt leg-to-plate step.
    verts=[];rings=[];segments=64;levels=22
    bottom=spec['bottom'];top=spec['top'];base=outline(*bottom)
    floors=[]
    for x,y in base:
        hit,_,_,_=surface.ray_cast(Vector((y,.030-x,.08)),Vector((0,0,-1)),.07)
        if hit is None:raise RuntimeError('No slide contact under '+key)
        floors.append(hit.z-.0495-.00010)
    for j in range(levels+1):
        t=j/levels;blend=t*t*t*(10+t*(-15+6*t))
        hx,hy,r=[a+(b-a)*blend for a,b in zip(bottom,top)]
        ring=[]
        for i,(x,y) in enumerate(outline(hx,hy,r)):
            ring.append(len(verts));verts.append((x,y,floors[i]*(1-t)))
        rings.append(ring)
    faces=[tuple(reversed(rings[0])),tuple(rings[-1])]
    for a,b in zip(rings,rings[1:]):
        for i in range(segments):faces.append((a[i],a[(i+1)%segments],b[(i+1)%segments],b[i]))
    saddle=mesh_object('Flowing_'+key+'_Saddle',verts,faces,steel)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.0272));cutter=bpy.context.object;cutter.name='IronSightRelief'
    cutter.dimensions=(.08,.0144,.050);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bevel(cutter,.00165,8);subtract(saddle,cutter);bevel(saddle,.00045,5)
    parts=[saddle]
    # Flush fasteners break up the broad shoulder without protruding blocks.
    for side in [-1,1]:
        for x in [-bottom[0]*.57,bottom[0]*.57]:
            z=-.0043;bvh=BVHTree.FromPolygons([v.co for v in saddle.data.vertices],[list(p.vertices) for p in saddle.data.polygons])
            hit,_,_,_=bvh.ray_cast(Vector((x,side*.03,z)),Vector((0,-side,0)),.03)
            if hit is None:raise RuntimeError('No fastener shoulder '+str((key,side,x,z,len(saddle.data.polygons),min(floors),max(floors))))
            recess=cylinder('ShallowCounterbore',(x,hit.y-side*.0002,z),.00135,.00085,steel)
            subtract(saddle,recess)
            head=cylinder('FlushFastener',(x,hit.y-side*.00038,z),.00103,.00024,steel);bevel(head,.00008,3)
            socket=cylinder('HexPocket',(x,hit.y-side*.00020,z),.00047,.0004,steel,6);subtract(head,socket);parts.append(head)
    for ob in parts:
        for p in ob.data.polygons:p.use_smooth=True
        select(ob);mod=ob.modifiers.new('Broad plane and curved shoulder normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=35
        bpy.ops.object.modifier_apply(modifier=mod.name);physical_uv(ob)
    select(original)
    for ob in parts:ob.select_set(True)
    bpy.ops.object.join();name='SM_M1911_'+key+'_Rounded20260927';original.name=name
    tri=original.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    original.data.uv_layers.active_index=0;original.data.uv_layers[0].active_render=True
    for label,point in {'AimCenter':spec['aim'],'MountForward':(.03,0,0),'MountUp':(0,0,.03)}.items():
        child=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(child);child.parent=original;child.location=point;child.select_set(True)
    file=E/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/('M1911_'+key+'_RoundedMount_Editable.blend')))
    records[key]={'source':str(S/spec['source']),'fbx':str(file),'old_asset':spec['old_asset'],
     'asset':spec['old_asset'],'materials':[m.name for m in original.data.materials],
     'mount_root_m':[0,.030,.0495],'aim_local_m':spec['aim'],'base_half_dimensions_m':bottom,'top_half_dimensions_m':top,
     'coating_uv':3,'edge_radius_m':.00045,'triangles':len(original.data.polygons),'game_tested':False,
     'method':'Actual slide-contact footprint; continuous rounded loft; radiused iron-sight tunnel; flush socket heads; retained optic geometry/UV/normals/aim point'}
(O/'optics_authoring.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('M1911_BOTH_ROUNDED_MOUNTS_AUTHORED',flush=True)
