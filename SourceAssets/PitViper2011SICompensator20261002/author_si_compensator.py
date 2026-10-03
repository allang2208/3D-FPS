"""Author the fitted SI body extension and export the existing integrated part."""
import bpy,bmesh,json,math,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent;P=O.parents[1]
SOURCE=O.parent/'PitViper2011Integration20261002'
NAME='SM_PitViper2011_SICompensator'
raw=json.loads((SOURCE/'canonical_parts.json').read_text())
auth=json.loads((SOURCE/'Single/authoring.json').read_text())
part=next(v for v in raw if v['identity']=='2011pv barrel compensator_2' and v['material']=='h-190')
marker=Vector(auth['markers_source_m']['WPN_SOCKET_Muzzle'])
# Actual large back-facing mounting plane; the farther rear bbox point is the sight tab.
back_groups={}
for f in part['faces']:
    pts=[Vector(part['verts'][i]) for i in f]
    n=(pts[1]-pts[0]).cross(pts[2]-pts[0])
    if n.length<1e-9 or n.normalized().y<.9 or max(v.y for v in pts)-min(v.y for v in pts)>.00005:continue
    y=round(sum(v.y for v in pts)/len(pts),5)
    area=sum((pts[i]-pts[0]).cross(pts[i+1]-pts[0]).length*.5 for i in range(1,len(pts)-1))
    area0,points=back_groups.get(y,(0,[]));back_groups[y]=(area0+area,points+pts)
mount_y,(mount_area,mount_points)=max(back_groups.items(),key=lambda item:item[1][0])
rear_width=max(p.x for p in mount_points)-min(p.x for p in mount_points)
bottom=min(p.z for p in mount_points)-marker.z;top=max(p.z for p in mount_points)-marker.z
source_mount=Vector((0,mount_y,marker.z))
source_to_part=Matrix(((0,-1,0,mount_y),(1,0,0,0),(0,0,1,-marker.z),(0,0,0,1)))
sys.path.insert(0,str(P/'Tools/Weapons'))
from pit_viper_si_extension import derive_interface,shell_loft
interface=derive_interface(raw,source_to_part)
top=interface['top_m'];bottom=interface['bottom_m'];nose=interface['native_muzzle_x_m']

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['stage']='SI native muzzle extension source; engine saving recorded separately; not game tested'
scene['name']='SI 枪口补偿器 · 2011 限定改造'
scene['reference']=str(O/'Reference/SI-compensator-user-reference.png')
edit=bpy.data.collections.new('01_SI_Editable');scene.collection.children.link(edit)
cuts=bpy.data.collections.new('02_ConstructiveCutters');scene.collection.children.link(cuts)
refs=bpy.data.collections.new('03_PitViper_InterfaceReference');scene.collection.children.link(refs)
exports=bpy.data.collections.new('04_ExportMesh');scene.collection.children.link(exports)

def move_to(ob,col):
    for old in list(ob.users_collection):old.objects.unlink(ob)
    col.objects.link(ob);return ob
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=ob
def material(name,color,rough,metal):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*color,1);return m
black=material('SI_2011_CleanAnodized',(.021,.023,.026),.38,1)
black['UE_Master']='/Game/Weapons/WeaponSurface/Master/M_WeaponSurface'
black['UE_Parent']='/Game/Weapons/PitViper2011/Integrated20261002/Materials/MI_PitViper2011_h_190'
recess=material('SI_RecessSteel',(.008,.009,.011),.57,1)
recess['UE_Reference']='/Game/Weapons/M4MuzzlesV1/MI_MuzzleRecess'
ink=material('SI_GrayLaserMark',(.44,.46,.48),.68,0)
metal_slots=[black,recess,ink]

def micro_finish(m):
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1600
    noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.5
    coord=m.node_tree.nodes.new('ShaderNodeTexCoord');m.node_tree.links.new(coord.outputs['Object'],noise.inputs['Vector'])
    bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.025;bump.inputs['Distance'].default_value=.000001
    m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
micro_finish(black);micro_finish(recess)

def mesh(name,vertices,faces,col=edit):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);col.objects.link(ob)
    for m in metal_slots:data.materials.append(m)
    return ob
def rectangle_section(w,z0,z1,chamfer):
    y=w/2;c=chamfer
    return [(-y+c,z0),(y-c,z0),(y,z0+c),(y,z1-c),(y-c,z1),(-y+c,z1),(-y,z1-c),(-y,z0+c)]

# The rear cap comes from the actual factory nose, including its side-elevation
# lower rake and compound side bevels. Its silhouette is extruded, never widened.
length=nose+interface['extension_length_m']
V,F=shell_loft(interface,length,top)
body=mesh('SI_MainShell_Editable',V,F)
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()

def cutter_box(name,loc,size,radius=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name
    ob.dimensions=size;active(ob);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for m in metal_slots:ob.data.materials.append(m)
    for f in ob.data.polygons:f.material_index=1
    if radius:
        mod=ob.modifiers.new('Rounded aperture','BEVEL');mod.width=radius;mod.segments=4;mod.affect='EDGES'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    move_to(ob,cuts);ob.display_type='WIRE';ob.hide_render=True;return ob
def cutter_cylinder(name,loc,radius,depth,axis='X',segments=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=loc)
    ob=bpy.context.object;ob.name=name
    ob.rotation_euler=(0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0) if axis=='Y' else (0,0,0)
    active(ob);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    for m in metal_slots:ob.data.materials.append(m)
    for f in ob.data.polygons:f.material_index=1
    move_to(ob,cuts);ob.display_type='WIRE';ob.hide_render=True;return ob
def subtract(target,cutter):
    mod=target.modifiers.new(cutter.name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    mod.material_mode='INDEX'

# Visual passage and vents for a game model; not manufacturing or ballistic specifications.
subtract(body,cutter_cylinder('Bore_OpenPassage',(length/2,0,0),.0049,length+.040))
seat_front=interface['barrel_seat_front_m']
subtract(body,cutter_cylinder('Viper_ActualBarrelSeat',((seat_front-.004)/2,0,0),interface['barrel_seat_radius_m'],seat_front+.004))
subtract(body,cutter_cylinder('Outlet_Recess',(length-.00025,0,0),.00625,.0013))
subtract(body,cutter_box('Rear_RoofPort',(nose+.0078,0,top-.0018),(.0078,.0174,.012),.0007))
for i,x in enumerate((.0184,.0240)):
    subtract(body,cutter_box('TopCrossVent_'+str(i+1),(nose+x,0,top-.0025),(.00265,.033,.013),.00045))
subtract(body,cutter_box('Side_RectangularPort',(nose+.0094,0,.0002),(.0057,.034,.0057),.0009))
for row,z in enumerate((-.0065,-.0090)):
    for col,x in enumerate((.0170,.0197)):
        subtract(body,cutter_cylinder('Side_MicroVent_'+str(row)+'_'+str(col),(nose+x,0,z),.00065,.034,axis='Y',segments=28))
for side in (-1,1):
    subtract(body,cutter_box('Side_LowerPanel_'+str(side),(nose+.0095,side*(interface['body_width_m']/2+.0001),-.0105),(.0115,.0010,.0017),.00035))

bevel=body.modifiers.new('Machined edge fillets','BEVEL');bevel.width=.00025;bevel.segments=3
bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(30);bevel.use_clamp_overlap=True
norm=body.modifiers.new('Preserve plane normals','WEIGHTED_NORMAL');norm.keep_sharp=True;norm.weight=45
for f in body.data.polygons:f.use_smooth=True
body['variant']='pit_viper_si_compensator'
body['role']='Body extension of the actual Viper nose: reciprocal side rake, identical width, native front retained'
body['interface_contract']=json.dumps(interface)
body['datum']='Origin at principal factory rear mounting plane, +X forward, +Y right, +Z up; meters'

# Keep the WHOLE native front section. The original skeletal section is hidden
# by the established SI integration; this replacement therefore includes it.
native=mesh('SI_Native2011_RearInterfaceAndSightBridge',[source_to_part@Vector(v) for v in part['verts']],part['faces'])
if len(part.get('uv',[]))==len(part['verts']):
    uv=native.data.uv_layers.new(name='UV0')
    for face in native.data.polygons:
        for li in face.loop_indices:uv.data[li].uv=part['uv'][native.data.loops[li].vertex_index]
bm=bmesh.new();bm.from_mesh(native.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(native.data);bm.free();native.data.update()
native['role']='Complete Viper factory muzzle housing retained; SI extends its exact nose without a gap or widened collar'
subtract(native,cutter_cylinder('Native_ViperBarrelSeat',(-.0006,0,0),interface['barrel_seat_radius_m'],.0020))
for f in native.data.polygons:f.use_smooth=False
surface_bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())

def mark_surface(x,z,side):
    hit,normal,face,distance=surface_bvh.ray_cast(Vector((x,side*.050,z)),Vector((0,-side,0)),.10)
    if hit is None:raise RuntimeError('SI marking needs a supporting housing surface')
    return hit.y+side*.000012

def badge_mesh(name,points,side,center=(.0030,.0036)):
    # Thin laser-mark ribbon lies on the actual main-shell side facet.
    v=[];f=[];width=.000095
    for a,b in zip(points,points[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1];ln=math.hypot(dx,dz)
        ox,oz=-dz/ln*width/2,dx/ln*width/2;offset=len(v)
        for x,z in [(a[0]+ox,a[1]+oz),(a[0]-ox,a[1]-oz),(b[0]-ox,b[1]-oz),(b[0]+ox,b[1]+oz)]:
            px,pz=center[0]+x,center[1]+z
            v.append((px,mark_surface(px,pz,side),pz))
        f.append(tuple(offset+i for i in (0,1,2,3)))
    ob=mesh(name,v,f)
    for face in ob.data.polygons:face.material_index=2
    return ob
def text_mark(name,text,x,z,size,side):
    bpy.ops.object.text_add(location=(x,side*.01314,z));ob=bpy.context.object;ob.name=name;move_to(ob,edit)
    ob.data.body=text;ob.data.size=size;ob.data.align_x='CENTER';ob.data.align_y='CENTER'
    ob.data.extrude=0;ob.data.space_character=1.1;ob.data.materials.append(ink)
    # Text local XY -> shell XZ; front normal points toward the corresponding side.
    ob.rotation_euler=(math.pi/2 if side<0 else -math.pi/2,0,0)
    if side>0:ob.rotation_euler[1]=math.pi
    ob['role']='Original typographic SI name and visual heat label; not copied image texture'
    active(ob);bpy.ops.object.convert(target='MESH')
    ob=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for vertex in ob.data.vertices:vertex.co.y=mark_surface(vertex.co.x,vertex.co.z,side)
    return ob
marks=[]
for side in (-1,1):
    marks.append(badge_mesh('SI_HeatTriangle_'+str(side),[(-.00105,-.0006),(.00105,-.0006),(0,.0011),(-.00105,-.0006)],side,center=(nose+.0043,.0032)))
    marks.append(text_mark('SI_HotText_'+str(side),'HOT',nose+.0043,.0016,.00085,side))
    marks.append(text_mark('SI_LimitedName_'+str(side),'SI',nose+.0098,-.0105,.0010,side))

def socket(name,pos):
    ob=bpy.data.objects.new('SOCKET_'+name,None);edit.objects.link(ob);ob.location=pos;ob.empty_display_size=.003
    ob.empty_display_type='ARROWS';return ob
sockets=[socket('MountRear',(0,0,0)),socket('Muzzle',(length,0,0)),socket('AimGuide',(length+.025,0,0))]

# Context geometry is available for later Blender review, hidden in the editable component scene.
for src in raw:
    if src['identity'] not in ('2011pv slide_1','2011pv frame_12','2011pv barrel compensator_2'):continue
    if src['identity']=='2011pv barrel compensator_2' and src['material']=='h-190':continue
    ref=mesh('REFERENCE_'+src['identity']+'_'+src['material'],[source_to_part@Vector(v) for v in src['verts']],src['faces'],refs)
    if src['material']=='copper':ref.data.materials[0]=material('Reference2011Copper',(.47932,.171441,.0331048),.30,1)
    elif src['material']=='polymer':ref.data.materials[0]=material('Reference2011Polymer',(.025,.027,.029),.74,0)
    ref.hide_render=True;ref.hide_set(True);ref['reference_only']=True
for ob in cuts.objects:ob.hide_set(True)
for socket_ob in sockets:socket_ob.hide_set(True)

scene.world=bpy.data.worlds.new('SI authoring world');scene.world.color=(.07,.07,.07)
scene.render.film_transparent=True
scene.view_settings.view_transform='AgX'
# Prepared viewpoints do not render or constitute acceptance.
for label,pos in [('Side',(length/2,-.10,0)),('ThreeQuarter',(length+.055,-.065,.035)),('Bore',(length+.08,0,.002))]:
    bpy.ops.object.camera_add(location=pos);cam=bpy.context.object;cam.name='Camera_'+label
    target=Vector((length/2,0,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=.060
    if label=='ThreeQuarter':scene.camera=cam
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=.10;area.spaces.active.region_3d.view_location=(.01,0,0)
active(body)
editable=O/'Blender/SICompensator_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(editable))

# Freeze evaluated geometry for exports, leaving all live cutters in the editable source.
deps=bpy.context.evaluated_depsgraph_get();pieces=[]
for ob in [body,native]+marks:
    evaluated=ob.evaluated_get(deps)
    data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
    copy=bpy.data.objects.new('EXPORT_'+ob.name,data);exports.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();pieces.append(copy)
for ob in edit.objects:
    if ob.type not in ('EMPTY',):ob.hide_set(True);ob.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for ob in pieces:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join()
game=pieces[0];game.name=NAME
active(game);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(game.data)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
bm.to_mesh(game.data);bm.free();game.data.update()
for face in game.data.polygons:face.use_smooth=True
game.data.set_sharp_from_angle(angle=math.radians(35))
for uv in list(game.data.uv_layers):game.data.uv_layers.remove(uv)
game.data.uv_layers.new(name='UV0')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.015)
bpy.ops.object.mode_set(mode='OBJECT')
for n in (1,2,3):
    layer=game.data.uv_layers.new(name='UV'+str(n))
    for face in game.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in face.loop_indices:
            v=game.data.vertices[game.data.loops[li].vertex_index].co
            layer.data[li].uv=(v[axes[0]]/.1,v[axes[1]]/.1)
active(game)
for ob in sockets:ob.hide_set(False);ob.select_set(True)
fbx=O/'Exports'/(NAME+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
active(game)
obj=O/'Exports'/(NAME+'.obj')
bpy.ops.wm.obj_export(filepath=str(obj),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_materials=True)
for ob in sockets:ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Blender/SICompensator_ExportReady.blend'))

record={'status':'blender_authored_and_exported','name':'SI 枪口补偿器','part':'pit_viper_si_compensator',
 'intended_host':'ue_pit_viper2011','intended_slot':'muzzle','limited':True,
 'reference':str(O/'Reference/SI-compensator-user-reference.png'),
 'editable_blend':str(editable),'export_blend':str(O/'Blender/SICompensator_ExportReady.blend'),'fbx':str(fbx),'obj':str(obj),
 'source_interface':str(SOURCE/'canonical_parts.json'),'source_part':part['identity']+' / '+part['material'],
 'principal_rear_plane_source_y_m':mount_y,'mount_area_m2':mount_area,'rear_width_m':rear_width,
 'source_mount_m':list(source_mount),'source_to_part':[list(row) for row in source_to_part],
 'axis':'+X forward, +Y right, +Z up; meters; rear mounting face datum',
 'body_length_m':length,'extension_length_m':interface['extension_length_m'],'body_width_m':interface['body_width_m'],'native_sight_bridge_retained':True,
 'interface_revision':'20261003 body extension: actual side-view muzzle rake, compound corners, exact full body width; complete native muzzle retained',
 'interface_contract':interface,
 'sockets_blender_m':{ob.name:list(ob.location) for ob in sockets},
 'mount_relative_to_current_factory_muzzle_m':[-(mount_y-marker.y),0,0],
 'features':['Exact reciprocal native muzzle nose cap','native side-view lower rake and side bevels extended along bore axis','full-length native width without a flared collar','complete native muzzle front and sight bridge retained','measured barrel seating recess','faceted black housing','open axial passage','rear roof port','two top-to-side transverse slots','rounded side window','four small side holes per side','native-rake front lower ramp','gray SI and HOT marks'],
 'materials':[m.name for m in game.data.materials],
 'triangles':sum(len(f.vertices)-2 for f in game.data.polygons),'vertices':len(game.data.vertices),
 'rendered':False,'game_tested':False,'ue_imported':False,'catalog_published':False,
 'future_integration':'Use the established SI asset and unchanged mounting datum. Keep the original skeletal h-190 section hidden: the static replacement now contains that complete native housing plus its fitted SI extension. Muzzle and AimGuide sockets move forward by the authored extension.',
 'provenance':'User-provided image used as visual reference; original Blender housing, ports and marks. Retained interface/sight geometry from Low Poly TTI JW4 Pit Viper 2011 by D_U, original integration records CC BY 4.0, https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153. Reference dimensions are game fitting values, not manufacturer or production specifications.'}
record['fbx_sha256']=hashlib.sha256(fbx.read_bytes()).hexdigest()
(O/'authoring_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('SI_COMPENSATOR_BLENDER_AUTHORED_AND_EXPORTED',record['triangles'],flush=True)
