"""Detail V2: fitted receiver panels and a machined, ventilated upper forend.
Authoring coordinates remain identical to the existing attachment. This is a
static visual shell: native stock, grips, moving bolt and animation stay intact.
"""
import bpy, bmesh, json, math, runpy
from pathlib import Path
from mathutils import Vector

O=Path(__file__).resolve().parent
BASE=O.parent
SOURCE=BASE.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'
for folder in ('Exports','Textures','Icons'): (O/folder).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),use_scripts=False)
existing=list(bpy.data.objects)
for ob in existing: ob.hide_render=True; ob.hide_set(True)
parts=[]

def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m

# WS1.1 project dark treated-metal approximation, not a measured raw-metal swatch.
coat=material('M24_AAS_CoatedMetal',(.032,.034,.037),1.,.395)
steel=material('M24_AAS_SatinSteel',(.074,.078,.083),1.,.335)
interior=material('M24_AAS_Interior',(.009,.010,.011),0.,.62)

def finish(ob,name,mat=coat,bevel=.00035,segments=3):
    ob.name=name;ob.data.materials.clear();ob.data.materials.append(mat)
    if bevel:
        mod=ob.modifiers.new('Manufactured radius','BEVEL');mod.width=bevel
        mod.segments=segments;mod.limit_method='ANGLE';mod.angle_limit=math.radians(25)
        mod.use_clamp_overlap=True;mod.harden_normals=True
    mod=ob.modifiers.new('Planar corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50
    for p in ob.data.polygons:p.use_smooth=True
    parts.append(ob);return ob

def mesh(name,verts,faces,mat=coat,bevel=.00035):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    # The modeller owns these new faces; orient them before bevel/normal authoring.
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    return finish(ob,name,mat,bevel)

def box(name,pos,size,mat=coat,bevel=.00035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(ob,name,mat,bevel)

def cylinder(name,pos,radius,depth,axis='X',mat=steel,vertices=40,bevel=.00018):
    rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=pos,rotation=rot)
    ob=bpy.context.object;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return finish(ob,name,mat,bevel)

def prism_x(name,yz,x0,x1,mat=coat,bevel=.00035):
    n=len(yz);verts=[(x,y,z) for x in (x0,x1) for y,z in yz]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,bevel)

def prism_y(name,xz,y0,y1,mat=coat,bevel=.00035):
    n=len(xz);verts=[(x,y,z) for y in (y0,y1) for x,z in xz]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,bevel)

def apply(ob):
    bpy.context.view_layer.objects.active=ob
    for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)

def cut(ob,cutter):
    apply(cutter)
    mod=ob.modifiers.new('Machined recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.context.view_layer.objects.active=ob
    while list(ob.modifiers).index(mod)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)

def slot(ob,pos,size,radius):cut(ob,box('aperture tool',pos,size,coat,radius))

def fastener(host,sign,y,z,outer,r=.0022):
    # Recess is genuinely cut in the carrier; the washer and socket have depth.
    cut(host,cylinder('counterbore tool',(sign*(outer+.0001),y,z),r*1.23,.00145,'X',coat,40,.00012))
    ring=cylinder('Captive screw seat',(sign*(outer-.00040),y,z),r*1.11,.00065,'X',interior,40,.00012)
    head=cylinder('Socket head',(sign*(outer+.00010),y,z),r,.0010,'X',steel,40,.00014)
    cut(head,cylinder('hex socket tool',(sign*(outer+.00055),y,z),r*.52,.0010,'X',steel,6,.000055))
    return ring,head

# Keep the current lower perimeter and the clear bolt/ejection corridor.
receiver_profile=[(-.065,.068),(.041,.054),(.091,.059),(.120,.080),(.265,.083),
                  (.282,.097),(.280,.106),(.093,.106),(.030,.086),(-.065,.087)]
for sign in (-1,1):
    side=prism_x('Receiver contoured side plate',receiver_profile,sign*.02225,sign*.02575,bevel=.00055)
    # A shallow pocket leaves a solid web; it does not open the working receiver.
    pocket=[(.114,.088),(.125,.0858),(.248,.0885),(.262,.094),(.258,.1005),(.120,.1005)]
    cut(side,prism_x('receiver pocket tool',pocket,sign*.02490,sign*.0275,bevel=.00055))
    for y,z in ((-.047,.079),(.070,.078),(.132,.094),(.249,.094)):
        fastener(side,sign,y,z,.02490 if y>.12 else .02575,.0020)
    # Short, interrupted reinforcing webs follow the pocket rather than float above it.
    for y in (.167,.203,.229):
        web=prism_x('Receiver pocket web',[(y-.0017,.0879),(y+.0012,.088),
                 (y+.0012,.100),(y-.0017,.100)],sign*.02465,sign*.02550,bevel=.00020)
    # Angled fore-end transition shares the front attachment boundary.
    shoulder=prism_x('Receiver to forend shoulder',[(.270,.090),(.290,.107),(.307,.109),
                         (.307,.138),(.291,.139),(.281,.105)],sign*.0218,sign*.0273,bevel=.0005)
    fastener(shoulder,sign,.298,.117,.0273,.0021)

# A bent-section wall with closed upper/lower returns, replacing the old boxes.
# The lower support-contact surface remains on the original skeletal mesh.
wall=[(.0208,.1075),(.0249,.1090),(.0280,.1130),(.0280,.1345),(.0227,.1442),
      (.0190,.145),(.0190,.1412),(.0242,.1334),(.0242,.1146),(.0208,.1112)]
for sign in (-1,1):
    side=prism_y('Chamfered ventilated handguard',[(sign*x,z) for x,z in wall],.288,.602,bevel=.00042)
    for y in (.321,.367,.413,.459,.505,.551):
        slot(side,(sign*.026,y,.124),(.015,.034,.0105),.0037)
    # Small upper ventilation slots are cut through the angled return.
    for y in (.329,.383,.437,.491,.545,.581):
        slot(side,(sign*.0228,y,.1397),(.016,.022,.0040),.0015)
    for y in (.299,.390,.480,.589):fastener(side,sign,y,.1128,.0276,.00165)
    # Separate rail carrier with fitted lower feet and true dovetail tooth sections.
    carrier=box('Side rail mounting spine',(sign*.0295,.527,.124),(.0060,.094,.009),bevel=.00035)
    for y in (.490,.564):
        box('Rail locating foot',(sign*.028,y,.124),(.0040,.011,.013),bevel=.00025)
    for j in range(7):
        y=.499+j*.0095
        xz=[(.0310,.117),(.0320,.1148),(.0358,.1168),(.0358,.1312),(.0320,.1332),(.0310,.1310)]
        prism_y('Side dovetail tooth',[(sign*x,z) for x,z in xz],y,y+.0054,bevel=.00024)
    for y in (.490,.564):fastener(carrier,sign,y,.124,.0325,.0020)

# Closed front/rear bands have a real barrel opening and an outer chamfered rim.
outer=[(-.0206,.1078),(.0206,.1078),(.0282,.114),(.0282,.1348),(.0227,.1448),
       (-.0227,.1448),(-.0282,.1348),(-.0282,.114)]
for y,depth in ((.289,.0055),(.601,.0060)):
    ring=prism_y('Forend end collar',outer,y-depth/2,y+depth/2,bevel=.0005)
    cut(ring,cylinder('barrel clearance',(0,y,.115),.020,depth+.012,'Y',coat,64,.0003))

# Rail retains the previous sight-facing height and centerline. Each ridge is
# one machined cross section instead of two stacked rectangular blocks.
railbase=[(-.0095,.1426),(.0095,.1426),(.0100,.1455),(-.0100,.1455)]
prism_y('Continuous top rail spine',railbase,.282,.611,bevel=.00022)
railtooth=[(-.0090,.1448),(.0090,.1448),(.0130,.1463),(.0130,.1477),(.0107,.1503),
           (-.0107,.1503),(-.0130,.1477),(-.0130,.1463)]
for j in range(33):
    y=.286+j*.010
    prism_y('Top dovetail ridge',railtooth,y-.0031,y+.0031,bevel=.00022)

# Apply only authored features. Large planar faces retain weighted normals.
for ob in parts:
    bpy.context.view_layer.objects.active=ob;apply(ob)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
    # UV0 uses physical 4 cm tiles. The normal texture and exported tangent
    # basis use this same UV channel; UV1 is reserved for the unique mask atlas.
    uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='Surface4cm')
    uv.name='Surface4cm'
    for poly in ob.data.polygons:
        n=poly.normal;axis=max(range(3),key=lambda k:abs(n[k]))
        for li in poly.loop_indices:
            p=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
            if axis==0:u,v=p.y,p.z*(1 if n.x>0 else -1)
            elif axis==1:u,v=p.x,p.z*(-1 if n.y>0 else 1)
            else:u,v=p.y,p.x*(-1 if n.z>0 else 1)
            uv.data[li].uv=(u/.04,v/.04)

bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join();body=bpy.context.object;body.name='M24_AdvancedAction_DetailBody'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
body.data.uv_layers.new(name='SurfaceMaskAtlas');body.data.uv_layers.active_index=1
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.004,area_weight=.1,correct_aspect=True)
bpy.ops.object.mode_set(mode='OBJECT')
body.data.uv_layers.active_index=0
body.data.uv_layers[0].active_render=True
tri=body.modifiers.new('Export triangulation','TRIANGULATE')
if hasattr(tri,'keep_custom_normals'):tri.keep_custom_normals=True
apply(body);body.data.calc_loop_triangles()

out=O/'Exports/SM_M24_m24_advanced_action.fbx'
bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1,bake_anim=False,
    use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_AdvancedAction_DetailV2.blend'))
report=dict(revision='DetailV2',models={'m24_advanced_action':dict(file=str(out),objects=[body.name],
    triangles=len(body.data.loop_triangles))},source=str(SOURCE),materials=[m.name for m in body.data.materials],
    stock='Native stock retained',host_modified=False,animations_changed=False,runtime_tested=False,
    uv0_tile_cm=4,mask_uv_channel=1,mask_resolution=2048,normal_convention='OpenGL; UE flips green once',
    features=['contoured receiver pocket and reinforcing webs','recessed hex fasteners',
    'chamfered handguard returns and true ventilation openings','fitted rail feet and dovetail rails',
    'closed end collars with barrel clearance'])
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_DETAIL_V2_GEOMETRY_SAVED',report['models']['m24_advanced_action']['triangles'],flush=True)
