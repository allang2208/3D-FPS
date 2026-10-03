"""Four precise warehouse container families, with separate moving meshes. No render/test."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/WarehouseContainers20261002'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
MAP={
 'Wood':'/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/Abandoned/MI_WBK_WSBench_BenchWood_R3',
 'Steel':'/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
 'Rubber':'/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
 'Paint':BASE+'/Materials/M_Warehouse_ToolPaint',
 'Case':BASE+'/Materials/M_Warehouse_CasePaint',
 'Plastic':BASE+'/Materials/M_Warehouse_PolymerGreen',
 'Labels':BASE+'/Materials/M_Warehouse_Labels'}
MATS={k:bpy.data.materials.new('RS_'+k) for k in MAP};parts=[];records=[];prototypes={}

def select(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def finish(obj,mat,bevel=.003):
    obj.data.materials.clear();obj.data.materials.append(MATS[mat]);select(obj)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Manufactured edge','BEVEL');mod.width=bevel;mod.segments=3
        mod.limit_method='ANGLE';mod.use_clamp_overlap=True;mod.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    uv=obj.data.uv_layers.new(name='UVMap')
    for face in obj.data.polygons:
        dims=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(face.normal[a]))]
        scale=1.72 if mat=='Wood' else 1.
        for li in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co;uv.data[li].uv=(p[dims[0]]/scale,p[dims[1]]/scale)
    if bevel:
        mod=obj.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.append(obj);return obj

def box(c,s,mat='Steel',bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.scale=s
    return finish(o,mat,min(bevel,min(s)*.25))

def cylinder(c,r,h,mat='Steel',axis=(0,0,1),sides=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=h,location=c)
    o=bpy.context.object;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return finish(o,mat,min(.0015,r*.18))

def tube(points,r=.007,mat='Steel'):
    curve=bpy.data.curves.new('Connected handle','CURVE');curve.dimensions='3D';curve.resolution_u=8
    curve.bevel_depth=r;curve.bevel_resolution=3;curve.use_fill_caps=True
    sp=curve.splines.new('POLY');sp.points.add(len(points)-1)
    for p,co in zip(sp.points,points):p.co=(*co,1)
    o=bpy.data.objects.new('Handle',curve);bpy.context.scene.collection.objects.link(o);select(o)
    bpy.ops.object.convert(target='MESH');o=bpy.context.object
    for f in o.data.polygons:f.use_smooth=True
    return finish(o,mat,0)

def label(c,w,h,row):
    # The atlas has six 800x400 panels. Labels use the same physical 2:1 aspect.
    mesh=bpy.data.meshes.new('Printed shipping label')
    mesh.from_pydata([(c[0]-w/2,c[1],c[2]-h/2),(c[0]+w/2,c[1],c[2]-h/2),
        (c[0]+w/2,c[1],c[2]+h/2),(c[0]-w/2,c[1],c[2]+h/2)],[],[(0,3,2,1)])
    mesh.update();o=bpy.data.objects.new('Shipping label',mesh);bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(MATS['Labels']);uv=mesh.uv_layers.new(name='UVMap')
    v0=1-(row+1)/6;v1=1-row/6
    coords=[(1,v0),(0,v0),(0,v1),(1,v1)]
    for li in mesh.polygons[0].loop_indices:uv.data[li].uv=coords[mesh.loops[li].vertex_index]
    parts.append(o)

def fasteners(x,y,z,axis=(0,1,0)):
    cylinder((x,y,z),.006,.004,axis=axis,sides=12)

def latch(x,y,z):
    box((x,y,z),(.058,.007,.108),'Steel',.002)
    box((x,y+.009,z+.015),(.027,.013,.045),'Steel',.003)
    tube([(x-.012,y+.021,z-.025),(x-.012,y+.03,z+.004),(x+.012,y+.03,z+.004),(x+.012,y+.021,z-.025)],.003)
    for dz in (-.042,.042):fasteners(x,y+.005,z+dz)

def hinges(width,depth,height):
    for x in (-width*.30,width*.30):
        box((x,-depth/2-.005,height-.035),(.085,.008,.07),'Steel',.002)
        cylinder((x,-depth/2,height),.012,.11,axis=(1,0,0))
        for dx in (-.025,.025):fasteners(x+dx,-depth/2-.01,height-.037,axis=(0,-1,0))

def side_handle(x,z,depth=.26):
    for y in (-depth/2,depth/2):
        box((x,y,z),(.014,.045,.07),'Steel',.003)
        cylinder((x,y,z),.015,.021,axis=(1,0,0))
    tube([(x,-depth/2,z),(x+.04,-depth/2,z-.045),(x+.04,depth/2,z-.045),(x,depth/2,z)],.009)

def emit(name,pivot=(0,0,0),hulls=()):
    global parts
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    bpy.context.scene.cursor.location=pivot;bpy.ops.object.origin_set(type='ORIGIN_CURSOR');obj.location=(0,0,0)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    if not obj.data.uv_layers.get('DetailLocal'):
        uv=obj.data.uv_layers.new(name='DetailLocal');src=obj.data.uv_layers['UVMap']
        for a,b in zip(uv.data,src.data):a.uv=b.uv
    # Match the accepted workbench wood material's UV and vertex-color inputs.
    src=obj.data.uv_layers['UVMap'];detail=obj.data.uv_layers['DetailLocal']
    age=obj.data.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face in obj.data.polygons:
        wood=obj.data.materials[face.material_index].name=='RS_Wood'
        for li in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co
            if wood:detail.data[li].uv=(src.data[li].uv.x-10,src.data[li].uv.y-10)
            age.data[li].color=(.96,.96,.96,1) if wood else (.09+.08*max(0,math.sin(p.x*.8+p.y*.65+p.z*2.3)),0,0,1)
    for i,(c,s) in enumerate(hulls):
        bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(c)-Vector(pivot));co=bpy.context.object
        co.name='UCX_'+name+'_'+str(i);co.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    collision=[o for o in bpy.data.objects if o.name.startswith('UCX_'+name+'_')]
    for co in collision:co.select_set(True)
    bpy.context.view_layer.objects.active=obj
    file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=name,fbx=str(file),asset=BASE+'/Meshes/'+name,materials={m.name:MAP[m.name[3:]] for m in obj.data.materials},
        triangles=len(obj.data.polygons),nanite=True,collision=bool(hulls),pivot_blender_m=list(pivot)))
    for co in collision:bpy.data.objects.remove(co,do_unlink=True)
    parts=[];obj.hide_set(True);return obj

def wood_crate():
    w,d,h=1.04,.78,.76
    # Fork feet and thick planks carry the crate; every face has actual wall thickness.
    for x in (-.34,.34):box((x,0,.043),(.095,d,.086),'Wood',.004)
    for i in range(7):box((-.445+i*.148,0,.109),(.143,d,.041),'Wood',.003)
    for z in (.20,.35,.50,.65):
        for y in (-d/2+.021,d/2-.021):box((0,y,z),(w-.10,.042,.143),'Wood',.003)
        for x in (-w/2+.022,w/2-.022):box((x,0,z),(.044,d-.084,.143),'Wood',.003)
    for x in (-w/2+.038,w/2-.038):
        for y in (-d/2+.04,d/2-.04):
            box((x,y,.435),(.07,.07,.61),'Wood',.004)
            box((x+(1 if x>0 else -1)*.038,y,.435),(.008,.085,.62),'Steel',.0015)
            box((x,y+(1 if y>0 else -1)*.038,.435),(.085,.008,.62),'Steel',.0015)
            for z in (.17,.33,.53,.71):fasteners(x,y+(1 if y>0 else -1)*.043,z)
    for x in (-.29,.29):
        for y in (-d/2-.004,d/2+.004):box((x,y,.44),(.034,.007,.63),'Steel',.001)
    hinges(w,d,h);label((0,d/2+.009,.51),.32,.16,0)
    for x in (-.29,.29):latch(x,d/2+.008,.66)
    side_handle(w/2+.013,.47);side_handle(-w/2-.013,.47)
    shell=[((0,0,.107),(w,d,.04)),((0,-d/2+.03,.43),(w,.065,.64)),
        ((0,d/2-.03,.43),(w,.065,.64)),((-w/2+.03,0,.43),(.065,d,.64)),((w/2-.03,0,.43),(.065,d,.64))]
    emit('SM_Warehouse_WoodCrate_Body',hulls=shell)
    for i in range(7):box((-.445+i*.148,0,h+.019),(.143,d+.014,.038),'Wood',.003)
    for y in (-.285,.285):box((0,y,h+.046),(w,.058,.018),'Wood',.003)
    for x in (-.29,.29):box((x,0,h+.048),(.035,d+.018,.008),'Steel',.001)
    emit('SM_Warehouse_WoodCrate_Lid',pivot=(0,-d/2,h))
    prototypes['WoodCrate']=dict(body='SM_Warehouse_WoodCrate_Body',door='SM_Warehouse_WoodCrate_Lid',
        hinge=[0,d*50,h*100],opening_motion='Lid',opened_roll=105,caption='加固运输木箱',storage_pages=2,dimensions_m=[w,d,h+.06])

def tote():
    w,d,h=.62,.44,.41;t=.014
    rings=[(-w/2+.025,-d/2+.025,.02),(w/2-.025,-d/2+.025,.02),(w/2-.025,d/2-.025,.02),(-w/2+.025,d/2-.025,.02)]
    outertop=[(-w/2,-d/2,h),(w/2,-d/2,h),(w/2,d/2,h),(-w/2,d/2,h)]
    vs=rings+outertop+[(x+(t if x<0 else -t),y+(t if y<0 else -t),z+.018) for x,y,z in rings]+[(x+(t if x<0 else -t),y+(t if y<0 else -t),z) for x,y,z in outertop]
    fs=[(0,3,2,1),(8,9,10,11)]
    for i in range(4):j=(i+1)%4;fs.extend([(i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i+4,j+4,j+12,i+12)])
    mesh=bpy.data.meshes.new('Tapered hollow polymer shell');mesh.from_pydata(vs,[],fs);mesh.update()
    o=bpy.data.objects.new('Tote shell',mesh);bpy.context.scene.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for y in (-d/2,d/2):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(0,y,h-.055));cut=bpy.context.object;cut.scale=(.15,.08,.039)
        select(o);mod=o.modifiers.new('Hand grip opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
    finish(o,'Plastic',.002)
    for y in (-d/2,d/2):
        box((0,y,h), (w+.008,.023,.023),'Plastic',.005)
        for x in (-.245,-.17,.17,.245):box((x,y,.22),(.014,.022,.30),'Plastic',.003)
    for x in (-w/2,w/2):box((x,0,h),(.023,d,.023),'Plastic',.005)
    for x in (-.22,.22):box((x,0,.013),(.048,d-.052,.026),'Rubber',.005)
    hinges(w,d,h);label((.16,d/2+.009,.25),.15,.075,1)
    for x in (-.20,.20):box((x,d/2+.017,h-.022),(.048,.025,.046),'Rubber',.006)
    emit('SM_Warehouse_Tote_Body',hulls=[((0,0,.03),(w-.04,d-.04,.04)),((0,-d/2,.22),(w,.035,.38)),
        ((0,d/2,.22),(w,.035,.38)),((-w/2,0,.22),(.035,d,.38)),((w/2,0,.22),(.035,d,.38))])
    box((0,0,h+.017),(w+.03,d+.03,.029),'Plastic',.009)
    for y in (-d/2,d/2):box((0,y,h+.035),(w+.03,.018,.018),'Plastic',.005)
    for x in (-w/2,w/2):box((x,0,h+.035),(.018,d,.018),'Plastic',.005)
    for x in (-.20,.20):box((x,0,h+.036),(.018,d-.025,.016),'Plastic',.004)
    emit('SM_Warehouse_Tote_Lid',pivot=(0,-d/2,h))
    prototypes['Tote']=dict(body='SM_Warehouse_Tote_Body',door='SM_Warehouse_Tote_Lid',hinge=[0,d*50,h*100],
        opening_motion='Lid',opened_roll=105,caption='带盖周转箱',storage_pages=1,dimensions_m=[w+.03,d+.03,h+.044])

def metal_case():
    w,d,h=.96,.67,.63
    box((0,0,.043),(w,d,.058),'Case',.007)
    for y in (-d/2+.012,d/2-.012):box((0,y,.34),(w,.024,.56),'Case',.007)
    for x in (-w/2+.012,w/2-.012):box((x,0,.34),(.024,d,.56),'Case',.007)
    for x in (-.38,.38):
        for y in (-.24,.24):box((x,y,.015),(.12,.09,.028),'Rubber',.009)
    for x in (-w/2,w/2):
        for y in (-d/2,d/2):
            box((x,y,.34),(.047,.047,.57),'Steel',.006)
            for z in (.10,.35,.56):fasteners(x,y+.027,z)
    for y in (-d/2,d/2):
        for x in (-.34,0,.34):box((x,y,.34),(.025,.009,.43),'Case',.004)
        box((0,y,h-.009),(w,.026,.03),'Rubber',.003)
    hinges(w,d,h);side_handle(w/2+.02,.37,.22);side_handle(-w/2-.02,.37,.22)
    for x in (-.30,.30):latch(x,d/2+.017,h-.055)
    label((0,d/2+.024,.39),.29,.145,2)
    emit('SM_Warehouse_MetalCase_Body',hulls=[((0,0,.04),(w,d,.06)),((0,-d/2+.02,.34),(w,.04,.57)),
        ((0,d/2-.02,.34),(w,.04,.57)),((-w/2+.02,0,.34),(.04,d,.57)),((w/2-.02,0,.34),(.04,d,.57))])
    box((0,0,h+.027),(w+.02,d+.02,.05),'Case',.012)
    for x in (-.32,0,.32):box((x,0,h+.057),(.032,d-.09,.012),'Case',.004)
    for y in (-d/2,d/2):box((0,y,h+.033),(w,.026,.056),'Steel',.006)
    emit('SM_Warehouse_MetalCase_Lid',pivot=(0,-d/2,h))
    prototypes['MetalCase']=dict(body='SM_Warehouse_MetalCase_Body',door='SM_Warehouse_MetalCase_Lid',hinge=[0,d*50,h*100],
        opening_motion='Lid',opened_roll=108,caption='重型金属运输箱',storage_pages=2,dimensions_m=[w+.12,d+.10,h+.07])

def tool_cabinet():
    w,d,h=.88,.52,1.53
    for x in (-.33,.33):
        for y in (-.18,.18):box((x,y,.065),(.08,.08,.13),'Steel',.005);box((x,y,.016),(.09,.09,.028),'Rubber',.006)
    box((0,0,.14),(w,d,.038),'Paint',.004)
    for x in (-w/2+.012,w/2-.012):box((x,0,.82),(.024,d,1.37),'Paint',.007)
    box((0,-d/2+.013,.82),(w,.026,1.37),'Paint',.006)
    box((0,0,h-.015),(w+.025,d+.025,.045),'Paint',.008)
    for z in (.48,.84,1.09):box((0,0,z),(w-.05,d-.035,.022),'Steel',.004)
    for x in (-.34,.34):box((x,-d/2+.031,.60),(.037,.014,.87),'Steel',.003)
    for x in (-.32,-.16,0,.16,.32):
        box((x,-.16,.88),(.047,.10,.06),'Rubber',.006)
        cylinder((x,-.16,.95),.009,.13,'Steel')
    for x in (-.40,.40):
        for z in (.36,.87):cylinder((x,d/2+.01,z),.011,.08,axis=(0,0,1))
    # Fixed drawer runners support the independently searchable top tray.
    for x in (-.39,.39):box((x,0,1.27),(.022,d-.06,.022),'Steel',.004)
    for x in (-.40,.40):
        for z in (1.12,1.44):box((x,0,z),(.024,d,.025),'Paint',.003)
    emit('SM_Warehouse_ToolCabinet_Body',hulls=[((0,0,.14),(w,d,.05)),((0,-d/2+.02,.82),(w,.04,1.37)),
        ((-w/2+.02,0,.82),(.04,d,1.37)),((w/2-.02,0,.82),(.04,d,1.37)),((0,0,1.51),(w,d,.04))])
    box((0,d/2+.012,.61),(w-.05,.029,.89),'Paint',.012)
    box((0,d/2+.031,.61),(w-.16,.008,.76),'Paint',.01)
    for x in (-.30,.30):
        for z in (.25,.95):fasteners(x,d/2+.04,z)
    tube([(.24,d/2+.035,.53),(.24,d/2+.084,.53),(.24,d/2+.084,.69),(.24,d/2+.035,.69)],.008)
    cylinder((.27,d/2+.04,.76),.017,.013,axis=(0,1,0))
    label((-.08,d/2+.04,.81),.28,.14,3)
    emit('SM_Warehouse_ToolCabinet_Door',pivot=(-w/2+.015,d/2+.015,.16))
    prototypes['ToolCabinet']=dict(body='SM_Warehouse_ToolCabinet_Body',door='SM_Warehouse_ToolCabinet_Door',
        hinge=[(-w/2+.015)*100,-(d/2+.015)*100,16],opening_motion='Swing',opened_yaw=-105,caption='维修工具柜',
        storage_pages=2,dimensions_m=[w+.025,d+.09,h])
    # Upper drawer is a second container; its separate fixed frame remains in the cabinet.
    for x in (-.402,.402):box((x,0,1.28),(.018,d-.06,.24),'Steel',.003)
    box((0,-d/2+.022,1.28),(w-.04,.025,.24),'Paint',.003)
    emit('SM_Warehouse_ToolDrawer_Frame',hulls=[((0,0,1.28),(w-.04,d-.05,.25))])
    box((0,.009,1.158),(w-.095,d-.04,.021),'Steel',.003)
    for x in (-.379,.379):box((x,.009,1.27),(.022,d-.04,.23),'Steel',.004)
    box((0,-d/2+.03,1.27),(w-.095,.021,.23),'Steel',.003)
    box((0,d/2+.02,1.28),(w-.055,.035,.29),'Paint',.01)
    tube([(-.16,d/2+.042,1.28),(-.16,d/2+.084,1.28),(.16,d/2+.084,1.28),(.16,d/2+.042,1.28)],.008)
    for x in (-.16,0,.16):box((x,.014,1.181),(.01,d-.06,.028),'Rubber',.002)
    for x in (-.26,-.10,.10,.26):cylinder((x,-.07,1.196),.026,.012,'Steel',sides=12)
    label((0,d/2+.039,1.36),.20,.10,4)
    emit('SM_Warehouse_ToolDrawer_Tray')
    prototypes['ToolDrawer']=dict(body='SM_Warehouse_ToolDrawer_Frame',door='SM_Warehouse_ToolDrawer_Tray',
        hinge=[0,0,0],opening_motion='Drawer',drawer_travel=[0,-34,0],caption='工具柜上层抽屉',storage_pages=1)

wood_crate();tote();metal_case();tool_cabinet()
layout={'WoodCrate':(-2,0,0),'Tote':(0,0,0),'MetalCase':(1.8,0,0),'ToolCabinet':(3.8,0,0),'ToolDrawer':(3.8,0,0)}
for key,p in prototypes.items():
    offset=Vector(layout[key]);body=bpy.data.objects[p['body']];body.hide_set(False);body.location=offset
    moving=bpy.data.objects[p['door']];moving.hide_set(False);hinge=Vector((p['hinge'][0]/100,-p['hinge'][1]/100,p['hinge'][2]/100));moving.location=offset+hinge
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WarehouseContainers_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,material_sources=MAP,
    original_geometry=True,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('WAREHOUSE_CONTAINERS_AUTHORED',len(records),flush=True)
