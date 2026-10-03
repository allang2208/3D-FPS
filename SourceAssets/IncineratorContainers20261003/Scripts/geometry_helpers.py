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
