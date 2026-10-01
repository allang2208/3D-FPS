"""Author enclosed switchback ramps in Blender. No rendering or test scene."""
import json, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
for folder in ('Authored','Config','Receipts','Backup'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1.0
MATS={
    'Concrete':'/Game/Dungeons/AtmosphereV2/Materials/M_Concrete',
    'Steel':'/Game/Dungeons/AtmosphereV2/Materials/M_PaintedSteel',
    'Yellow':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint',
    'Glass':'/Game/Dungeons/AtmosphereV2/Materials/M_CoolGlass',
}
materials={k:bpy.data.materials.new(k) for k in MATS}
records=[];modules=[]

def ue(v):return (v[0]/100,-v[1]/100,v[2]/100)

def prism(group,x0,x1,y0,y1,z0,z1,height,material):
    # A sheared closed box: horizontal datum at y0/y1, vertical thickness.
    vertices=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1),
              (x0,y0,z0+height),(x1,y0,z0+height),(x1,y1,z1+height),(x0,y1,z1+height)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new(group);mesh.from_pydata([ue(v) for v in vertices],[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(group,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(materials[material])
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        n=p.normal;axis=max(range(3),key=lambda a:abs(n[a]));axes=[a for a in range(3) if a!=axis]
        for li in p.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/2.,co[axes[1]]/2.)
    groups[group].append(obj)

def beam(group,a,b,radius,material):
    aa,bb=Vector(ue(a)),Vector(ue(b));d=bb-aa
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=radius/100,depth=d.length,location=(aa+bb)/2)
    obj=bpy.context.object;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=d.to_track_quat('Z','Y')
    obj.data.materials.append(materials[material]);groups[group].append(obj)

for rise in (540,1080,1620):
    ident=f'RouteRamp{rise}';run=rise*.75;back=-80-run;half=rise/2
    groups={'Structure':[],'Details':[]};cells=[]
    # Both 3 m clear flights have 33.7 degree grades and level end landings.
    for xc,za,zb in ((0,0,half),(348,rise,half)):
        prism('Structure',xc-174,xc+174,0,-80,za-22,za-22,22,'Concrete')
        prism('Structure',xc-174,xc+174,-80,back,za-22,zb-22,22,'Concrete')
        prism('Structure',xc-174,xc+174,0,-80,za+280,za+280,18,'Concrete')
        prism('Structure',xc-174,xc+174,-80,back,za+280,zb+280,18,'Concrete')
        for side in (-1,1):
            x=xc+side*162
            prism('Structure',x-12,x+12,0,-80,za,za,280,'Concrete')
            prism('Structure',x-12,x+12,-80,back,za,zb,280,'Concrete')
            # Raised edge strips and two solid handrails follow the real grade.
            strip=xc+side*139
            prism('Details',strip-3,strip+3,-80,back,za+.4,zb+.4,.6,'Yellow')
            beam('Details',(strip,-80,za+105),(strip,back,zb+105),2.5,'Steel')
            for i in range(5):
                t=i/4;y=-80-run*t;z=za+(zb-za)*t
                beam('Details',(side*148+xc,y,z+90),(strip,y,z+105),1.6,'Steel')
        # Axis-aligned occupancy slices preserve the usable space above/below.
        cells.append(dict(min=[xc-174,-80,za-22],max=[xc+174,0,za+298]))
        n=math.ceil(run/120)
        for i in range(n):
            t0,t1=i/n,(i+1)/n;z0,z1=za+(zb-za)*t0,za+(zb-za)*t1
            cells.append(dict(min=[xc-174,-80-run*t1,min(z0,z1)-22],max=[xc+174,-80-run*t0,max(z0,z1)+298]))
        for y,z in ((-45,za),(back+run*.45,za+(zb-za)*.55)):
            prism('Details',xc-58,xc+58,y-9,y+9,z+265,z+265,8,'Steel')
            prism('Details',xc-50,xc+50,y-7,y+7,z+263,z+263,2,'Glass')
    # A 3.2 m deep turn landing; no central wall across the route.
    prism('Structure',-174,522,back,back-320,half-22,half-22,22,'Concrete')
    prism('Structure',-174,522,back,back-320,half+280,half+280,18,'Concrete')
    for x0,x1 in ((-174,-150),(498,522)):
        prism('Structure',x0,x1,back,back-320,half,half,280,'Concrete')
    prism('Structure',-174,522,back-320,back-344,half-22,half-22,320,'Concrete')
    cells.append(dict(min=[-174,back-344,half-22],max=[522,back,half+298]))
    for xc,z in ((0,0),(348,rise)):
        for x in (xc-148,xc+148):prism('Details',x-2,x+2,0,-10,z,z,280,'Steel')
        prism('Details',xc-150,xc+150,0,-10,z+274,z+274,6,'Steel')
        for y in (-20,-60):prism('Details',xc-142,xc+142,y,y-4,z+.4,z+.4,.6,'Yellow')
    parts=[]
    for kind,objects in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        obj.name=f'SM_{ident}_{kind}';name=obj.name
        if kind=='Details':
            mod=obj.modifiers.new('ManufacturedEdges','BEVEL');mod.width=.004;mod.segments=2;mod.limit_method='ANGLE'
            bpy.ops.object.modifier_apply(modifier=mod.name)
        tri=obj.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
        fbx=ROOT/'Authored'/f'{name}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        asset='/Game/Dungeons/SplitLevels20261001/Meshes/'+name
        records.append(dict(name=name,fbx=str(fbx),asset=asset,materials=MATS,collision=kind=='Structure'))
        parts.append(dict(mesh=asset,position=[0,0,0],scale=[1,1,1],yaw=0,collision=kind=='Structure',fluid=False,materials=[]))
        obj.hide_set(True)
    path=[[0,0,0],[0,-80,0],[0,back,half],[0,back-160,half],[348,back-160,half],[348,back,half],[348,-80,rise],[348,0,rise]]
    lights=[]
    for xc,y,z in ((0,-60,0),(174,back-160,half),(348,-60,rise)):
        lights.append(dict(type='point',position=[xc,y,z+235],color=[.62,.75,.78],intensity=90,radius=750,optimized_radius_cm=750,
                           source_radius=12,cast_shadows=False,max_draw_distance_cm=2500,fade_range_cm=450))
    modules.append(dict(id=ident,family_id='SplitLevelRamp',role='vertical_connector',
        min=[-174,back-344,-22],max=[522,0,rise+298],ports=[dict(position=[0,0,0],normal=[0,1,0],width=300,height=280),
        dict(position=[348,0,rise],normal=[0,1,0],width=300,height=280)],cells=cells,parts=parts,lights=lights,anchors=[],
        walk_polyline=path,split_level_ramp=True,vertical_rise_cm=rise,connector_turns=2,spawn=dict(enabled=False),
        wall_art=False))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/SplitLevelRamps.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=records),indent=2),encoding='utf-8')
(ROOT/'Config/ramps.json').write_text(json.dumps(modules,indent=2),encoding='utf-8')
print('SPLIT_LEVEL_RAMPS_AUTHORED',len(records),flush=True)
