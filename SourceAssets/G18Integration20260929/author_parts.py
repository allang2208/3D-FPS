"""Fit existing pistol accessories to G18 interfaces; retain optic detail."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;E=O/'Attachments';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
records={};icon_geometry={}
def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def export(ob,key,source_asset='',sockets=None):
    ob.name='SM_G18_'+key;select(ob)
    for child in ob.children:
        if child.type=='EMPTY':child.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(E/(ob.name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    records[key]={'fbx':str(E/(ob.name+'.fbx')),'source_asset':source_asset,'slots':[m.name for m in ob.data.materials]}
    ob.data.calc_loop_triangles();uv=ob.data.uv_layers.active
    icon_geometry[key]={'vertices':[list(ob.matrix_world@v.co) for v in ob.data.vertices],
        'triangles':[list(t.vertices) for t in ob.data.loop_triangles],
        'uv':[[list(uv.data[i].uv) for i in t.loops] for t in ob.data.loop_triangles] if uv else [],'material':[t.material_index for t in ob.data.loop_triangles]}
    bpy.ops.wm.save_as_mainfile(filepath=str(E/(ob.name+'_Editable.blend')))

bpy.ops.wm.open_mainfile(filepath=str(O/'Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];root=r.data.bones['WPN_root'].matrix_local.copy();rinv=root.inverted()
mag=bpy.data.objects['G18_G18_mag'];body=bpy.data.objects['G18_G18']
bodycoords=[rinv@v.co for v in body.data.vertices]
surface=BVHTree.FromPolygons(bodycoords,[list(p.vertices) for p in body.data.polygons],all_triangles=True)
rail_hit=surface.ray_cast(Vector((.008,-.073,-.15)),Vector((0,0,1)))[0]
rail_height=rail_hit.z if rail_hit else -.001
# Preserve the factory shell and top feed interface. Split the bottom ring,
# translate the floorplate along the native magazine axis, and bridge the gap.
coords=[rinv@v.co for v in mag.data.vertices];old=mag.data;old.uv_layers.active_index=0
CUT=-.102;DELTA=Vector((0,.0252,-.080));verts=[];faces=[];uvs=[]
def clipped(poly,upper):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[0].z-CUT;db=b[0].z-CUT;ia=da>=-1e-8 if upper else da<=1e-8;ib=db>=-1e-8 if upper else db<=1e-8
        if ia:out.append(a)
        if ia!=ib:
            q=da/(da-db);out.append((a[0].lerp(b[0],q),a[1].lerp(b[1],q)))
    return out
def polygon(poly,move=Vector()):
    if len(poly)<3:return
    base=len(verts);verts.extend([root@(p+move) for p,uv in poly]);uvs.extend([uv for p,uv in poly]);faces.append(tuple(range(base,len(verts))))
for face in old.polygons:
    poly=[(coords[old.loops[i].vertex_index],Vector(old.uv_layers.active.data[i].uv)) for i in face.loop_indices]
    above=clipped(poly,True);below=clipped(poly,False);polygon(above);polygon(below,DELTA)
    cuts=[p for p in above if abs(p[0].z-CUT)<1e-7]
    if len(cuts)==2:
        a,b=cuts
        # Repeat the lower shell coating across the new strip; top UV stays exact.
        polygon([a,b,(b[0]+DELTA,b[1]+Vector((0,.08))),(a[0]+DELTA,a[1]+Vector((0,.08)))])
mesh=bpy.data.meshes.new('G18_ExtendedShell');mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
for f in mesh.polygons:
    for li,vi in zip(f.loop_indices,f.vertices):uv.data[li].uv=uvs[vi]
mesh.materials.append(bpy.data.materials['M_G18_Magazine']);ext=bpy.data.objects.new('SM_G18_ext_mag',mesh);bpy.context.collection.objects.link(ext)
export(ext,'ext_mag');records['ext_mag'].update(extension_m=list(DELTA),cut_m=CUT,frame='native G18 skeletal reference')
factory=mag.copy();factory.data=mag.data.copy();bpy.context.collection.objects.link(factory);factory.modifiers.clear();factory.parent=None;factory.matrix_world=Matrix.Identity(4);export(factory,'factory_magazine')
# Grip overlay follows the actual polymer grip, excluding the trigger guard.
ob=body.copy();ob.data=body.data.copy();bpy.context.collection.objects.link(ob);ob.modifiers.clear();ob.parent=None;ob.matrix_world=Matrix.Identity(4)
bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();remove=[]
for v in bm.verts:
    p=rinv@v.co
    if not(p.y>.001 and -.098<p.z<-.013):remove.append(v)
    else:v.co+=v.normal*.00035
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(ob.data);bm.free();export(ob,'GripSurface')
# Use the actual G18 mesh for its catalog image and numeric-only slot pictures.
for part,key in ((body,'factory'),):
    objects=[body,mag,bpy.data.objects['G18_G18_bullet']];vs=[];fs=[];uv=[]
    for obj in objects:
        offset=len(vs);vs.extend([list(rinv@v.co) for v in obj.data.vertices]);obj.data.calc_loop_triangles()
        for t in obj.data.loop_triangles:
            fs.append([offset+i for i in t.vertices]);uv.append([list(obj.data.uv_layers.active.data[i].uv) for i in t.loops])
    icon_geometry[key]={'vertices':vs,'triangles':fs,'uv':uv,'texture':'T_G18_Base_color.png'}

sources={
 'holographic':('M1911ReticleReadability20260927/Exports/SM_M1911_holographic_ReadableReticle20260927.fbx','/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_holographic'),
 'panoramic_red_dot':('M1911ReticleReadability20260927/Exports/SM_M1911_panoramic_red_dot_ReadableReticle20260927.fbx','/Game/Weapons/M1911/SculptedMount20260913/Meshes/SM_M1911_panoramic_red_dot'),
 'suppressor':('M1911CompactFit20260913/FBX/suppressor.fbx','/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_suppressor'),
 'tactical_suppressor':('ReferenceSuppressor5080_20260913/GameIntegration/M1911/SM_TacticalSuppressor.fbx','/Game/Weapons/TacticalSuppressor20260913/M1911/SM_TacticalSuppressor'),
 'brake':('M1911MuzzleRedDot20260913/SM_M1911_brake.fbx','/Game/Weapons/M1911/MuzzleRedDot20260913/Meshes/SM_M1911_brake'),
 'laser':('M1911CompactFit20260913/laser/SM_TacticalDevice.fbx','/Game/Weapons/M1911/CompactFit20260913/laser/SM_TacticalDevice'),
 'flashlight':('M1911CompactFit20260913/flashlight/SM_TacticalDevice.fbx','/Game/Weapons/M1911/CompactFit20260913/flashlight/SM_TacticalDevice')}
for key,(file,asset) in sources.items():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(S/file))
    objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];ob=objects[0]
    if len(objects)>1:
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
    if key in ('laser','flashlight'):
        # Source frame is the pistol root; translate its under-rail saddle onto
        # the measured G18 rail and carry emission sockets by the same delta.
        top=max(v.co.z for v in ob.data.vertices);delta=Vector((0,.010,rail_height-top+.0002))
        for v in ob.data.vertices:v.co+=delta
        for c in ob.children:
            if c.type=='EMPTY':c.location+=delta
    if key in ('holographic','panoramic_red_dot'):
        # G18 slide is flat. Replace only the curved 1911 contact plate.
        adapters={i for i,m in enumerate(ob.data.materials) if 'adapter' in m.name.lower()}
        if adapters:
            bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in adapters],context='FACES');bm.to_mesh(ob.data);bm.free()
        plate=bpy.data.materials.new('M_G18_AttachmentFinish');bpy.ops.mesh.primitive_cube_add(size=1,location=(-.002,0,-.0064));base=bpy.context.object;base.dimensions=(.036,.026,.0064)
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);base.data.materials.append(plate)
        mod=base.modifiers.new('Machined saddle edge','BEVEL');mod.width=.0007;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
        select(ob);base.select_set(True);bpy.ops.object.join()
    export(ob,key,asset)
    records[key]['source_file']=str(S/file)
    if key in ('laser','flashlight'):records[key]['rail_height_m']=rail_height
(O/'attachment_authoring.json').write_text(json.dumps(records,indent=2))
(O/'icon_geometry.json').write_text(json.dumps(icon_geometry,separators=(',',':')))
print('G18_ATTACHMENTS_SAVED',flush=True)
