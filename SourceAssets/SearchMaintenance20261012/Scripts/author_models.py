"""Five detailed maintenance collectibles, modeled in centimetres; no preview renders."""
import sys, json, math, random
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import mesh_helpers as H
SPEC=H.SPEC
box=H.box;ring=H.ring;cyl=H.cylinder;panel=H.panel;cut=H.cut

def spring(name,p,radius=.5,length=3.5,turns=6,wire=.07):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
    curve.bevel_depth=wire;curve.bevel_resolution=2;curve.resolution_u=1
    spline=curve.splines.new('POLY');steps=turns*24;spline.points.add(steps)
    for i,point in enumerate(spline.points):
        t=i/steps;a=t*turns*math.tau
        point.co=(p[0]+(t-.5)*length,p[1]+radius*math.cos(a),p[2]+radius*math.sin(a),1)
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    H.select(obj);bpy.ops.object.convert(target='MESH');H.register(obj,name,'steel')
    for face in obj.data.polygons:face.use_smooth=True
    return obj

def round_cut(obj,p,radius,depth):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=p)
    cutter=bpy.context.object;H.select(obj)
    mod=obj.modifiers.new('Manufactured circular pocket','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    while obj.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    H.project_uv(obj,obj['surface_region'])

def alloy():
    box('Chamfered forging alloy billet',(0,0,2),(27.7,6.8,3.8),'steel',.15,5)
    # Packaging is a thin, four-sided sleeve; both billet ends remain visible.
    box('Protective paper top',(0,0,3.946),(12.3,6.90,.085),'kraft',.035,3)
    box('Protective paper bottom',(0,0,.052),(12.3,6.90,.085),'kraft',.035,3)
    for y in (-3.45,3.45):box('Protective paper fold',(0,y,2),(12.3,.085,3.89),'kraft',.026,3)
    box('Wrapper overlap seam',(0,-3.503,2.55),(12.3,.026,.18),'paper',.01,2)
    box('Batch label stock',(0,0,4.004),(10.8,4.83,.028),'paper',.025,3)
    panel('Printed billet batch',(0,0,4.020),10.65,4.66,'primary')
    panel('Wrapper side serial',(0,-3.501,1.45),8.8,1.65,'barcode','FRONT')
    for x in (-13.857,13.857):
        # Faint saw-feed relief on the exposed ends, with no false dents.
        for j in range(12):
            z=.42+j*.275
            box('End face machining pass',(x,0,z),(.012,6.27,.012),'aluminum',.003,2)
    for x in (-9.9,9.9):
        box('Surface inspection witness',(x,0,3.906),(3.4,4.9,.010),'aluminum',.04,3)

def assembly():
    tray=box('Folded component carton',(0,0,2.45),(20,13,4.9),'kraft',.12,4)
    cut(tray,(0,0,3.30),(19.25,12.25,5.75))
    box('Paper insert base',(0,0,.56),(19.05,12.05,.22),'paper',.06,3)
    for x in (-3.25,3.22):box('Cardboard cell partition',(x,0,2.38),(.18,12.08,3.65),'kraft',.035,3)
    box('Cross cell partition',(0,0,2.38),(19.1,.18,3.65),'kraft',.035,3)
    # A factory paper sleeve covers one column, leaving the real contents readable.
    box('Outer sleeve top',(-6.53,0,4.99),(5.72,13.13,.14),'blue',.04,3)
    box('Outer sleeve underside',(-6.53,0,.005),(5.72,13.13,.10),'blue',.035,3)
    for y in (-6.55,6.55):box('Outer sleeve side fold',(-6.53,y,2.49),(5.72,.11,4.98),'blue',.025,3)
    for x in (-9.38,-3.68):box('Sleeve folded hem',(x,0,5.04),(.07,12.9,.045),'paper',.01,2)
    panel('Assembly box identity',(-6.53,2.55,5.068),5.20,2.28,'primary')
    panel('Assembly inventory list',(-6.53,-.46,5.068),5.20,2.28,'secondary')
    panel('Assembly batch serial',(-6.53,-4.12,5.068),5.20,.975,'barcode')
    # Distinct stocked compartments: screws, springs, locating pins and washers.
    for y in (1.95,3.95):
        spring('Packaged compression spring',(-.05,y,1.45),.47,4.25,6,.075)
    for y in (-4.55,-3.10,-1.65):
        cyl('Locating pin shaft',(-.10,y,1.15),.25,4.9,'steel','X',28,.035)
        cyl('Locating pin shoulder',(-2.55,y,1.15),.39,.27,'steel','X',28,.025)
        ring('Pin retaining groove',(-1.8,y,1.15),.265,.21,.065,'rubber','X',28)
    for y in (1.65,3.0,4.35):
        cyl('Bolt shank',(6.35,y,1.28),.23,4.25,'steel','X',24,.02)
        cyl('Hex bolt head',(4.19,y,1.28),.47,.39,'steel','X',6,.035)
        for x in (6.75,7.15,7.55,7.95):ring('Fastener rolled thread',(x,y,1.28),.27,.22,.07,'steel','X',24)
    for x in (4.93,7.75):
        for z in (.84,1.08,1.32):ring('Stacked flat washer',(x,-3.08,z),.94,.47,.15,'steel',sides=36)
        cyl('Hex nut',(x,-1.50,1.02),.65,.49,'brass',sides=6,radius=.03)
    for x in (-9.7,9.7):
        for y in (-6.24,6.24):box('Carton corner fold',(x,y,2.48),(.20,.20,4.56),'paper',.025,3)

def pouch_surface(x,y,upper=True):
    ex=min(1,max(0,(5.55-abs(x))/.65))
    phase=min(1,max(0,(abs(y)-.26)/3.17))
    hump=max(0,math.sin(phase*math.pi))**.52
    longitudinal=max(0,math.sin(min(1,max(0,(x+5.6)/11.2))*math.pi))**.22
    amount=ex*hump*longitudinal
    ripple=.021*math.sin(x*8.7+y*12.2)*math.sin(y*18.3)*(1-amount*.7)*amount
    return .24+(.91*amount+ripple if upper else -.67*amount-ripple)

def pouch_label(name,centre,w,h,region):
    nx,ny=18,10;verts=[];faces=[]
    for j in range(ny+1):
        for i in range(nx+1):
            x=centre[0]+(i/nx-.5)*w;y=centre[1]+(j/ny-.5)*h
            verts.append((x,y,pouch_surface(x,y)+.009))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);H.register(obj,name,region)
    u0,v0,u1,v1=H.uv_rect(region)
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            point=mesh.vertices[mesh.loops[li].vertex_index].co
            mesh.uv_layers.active.data[li].uv=(u0+(point.x-centre[0]+w*.5)/w*(u1-u0),v0+(point.y-centre[1]+h*.5)/h*(v1-v0))

def resin():
    nx,ny=64,44;verts=[];faces=[]
    for side in (False,True):
        for j in range(ny+1):
            for i in range(nx+1):
                x=-6+12*i/nx;y=-4+8*j/ny
                verts.append((x,y,pouch_surface(x,y,side)+(0 if side else -.065)))
    n=(nx+1)*(ny+1)
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+2;d=a+nx+1
            faces.extend(((d,c,b,a),(a+n,b+n,c+n,d+n)))
    boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)];faces.append((a,b,b+n,a+n))
    mesh=bpy.data.meshes.new('Dual chamber sealed foil');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('Dual chamber sealed foil',mesh);bpy.context.collection.objects.link(obj);H.register(obj,obj.name,'foil')
    for face in mesh.polygons:face.use_smooth=True
    cut(obj,(-5.82,0,.25),(.48,.28,2.5));cut(obj,(5.82,0,.25),(.48,.28,2.5))
    for y in (-3.86,3.86,0):
        box('Heat sealed seam',(0,y,.245),(11.4,.13,.025),'foil',.012,3)
    for x in (-5.80,5.80):
        for j in range(6):box('Crimped end seal',(x+(j-2.5)*.047,0,.249),(.021,7.76,.018),'aluminum',.006,2)
    pouch_label('Resin chamber printed label',(-.25,1.82),6.12,2.67,'primary')
    pouch_label('Hardener chamber directions',(-.25,-1.82),6.12,2.67,'secondary')
    pouch_label('Resin lot coding',(4.22,1.83),1.06,1.65,'small_label')
    pouch_label('Hardener lot coding',(4.22,-1.83),1.06,1.65,'small_label')

def wood():
    rng=random.Random(111)
    for layer in range(6):
        for y in (-1.45,1.45):
            obj=box('Laminated timber strip',(rng.uniform(-.09,.09),y,.28+layer*.475),
                    (54.7+rng.uniform(-.12,.12),2.79,.421),'wood',.055,4)
            obj['wood_end_grain']=True
    for x in (-14.3,14.3):
        box('Paper band top',(x,0,2.963),(4.0,5.98,.086),'kraft',.035,3)
        box('Paper band underside',(x,0,.035),(4.0,5.98,.066),'kraft',.025,3)
        for y in (-2.97,2.97):box('Paper band side',(x,y,1.50),(4.0,.075,2.93),'kraft',.025,3)
        box('Band glued overlap',(x,-3.016,1.69),(4.0,.025,.26),'paper',.012,3)
        panel('Lamination stock band',(x,0,3.010),3.62,1.585,'primary' if x<0 else 'secondary')
        panel('Lamination batch side',(x,-3.019,1.20),3.54,.664,'barcode','FRONT')

def precision():
    tray=box('Precision parts protective tray',(0,0,1.9),(18,12,3.8),'aluminum',.19,5)
    cut(tray,(0,0,2.60),(17.35,11.35,4.44))
    foam=box('Machined foam insert',(0,0,1.92),(17.0,11,2.87),'foam',.10,4)
    round_cut(foam,(-5,2.43,2.76),1.69,2.9)
    round_cut(foam,(-5,-2.75,2.65),1.57,2.8)
    cut(foam,(3.19,2.38,2.74),(7.28,2.83,2.85))
    cut(foam,(4.24,-2.62,2.70),(5.75,4.43,2.85))
    cut(foam,(-.86,-2.77,2.68),(2.35,4.43,2.85))
    ring('Brass precision bush',(-5,2.43,2.78),1.34,.76,2.0,'brass',sides=64)
    ring('Bush locating flange',(-5,2.43,3.60),1.53,.76,.23,'brass',sides=64)
    ring('Bearing outer race',(-5,-2.75,2.68),1.39,1.14,.94,'steel',sides=64)
    ring('Bearing inner race',(-5,-2.75,2.68),.86,.56,.94,'steel',sides=56)
    for j in range(12):
        a=j*math.tau/12
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.18,location=(-5+math.cos(a),-2.75+math.sin(a),2.87))
        H.register(bpy.context.object,'Bearing steel ball','steel')
        for face in bpy.context.object.data.polygons:face.use_smooth=True
    cyl('Stepped shaft main',(3.18,2.38,2.83),.62,5.45,'steel','X',48,.04)
    cyl('Shaft shoulder',(1.73,2.38,2.83),.87,.35,'steel','X',48,.035)
    for x in (.13,6.23):cyl('Shaft end journal',(x,2.38,2.83),.40,.75,'steel','X',40,.03)
    ring('Gear hub',(4.24,-2.62,2.84),1.47,.56,.47,'steel',sides=64)
    ring('Gear central shoulder',(4.24,-2.62,3.08),.89,.56,.27,'steel',sides=48)
    for j in range(24):
        a=j*math.tau/24
        obj=box('Machined gear tooth',(4.24+1.54*math.cos(a),-2.62+1.54*math.sin(a),2.84),(.33,.24,.44),'steel',.025,3)
        obj.rotation_euler.z=a
    for y in (-3.71,-1.84):
        ring('Retaining collar',(-.87,y,2.59),.71,.40,.62,'brass',sides=40)
        ring('Collar machined groove',(-.87,y,2.88),.716,.66,.06,'steel',sides=40)
    for x in (-8.68,8.68):
        for y in (-5.64,5.64):box('Corner protective pad',(x,y,1.95),(.40,.40,3.52),'rubber',.11,4)
    box('Precision front identity backing',(0,-6.005,1.79),(10.05,.029,2.43),'paper',.03,3)
    panel('Precision serialized label',(0,-6.026,1.79),9.85,2.30,'primary','FRONT')
    panel('Precision underside barcode',(0,0,-.008),9,1.69,'barcode','BOTTOM')

def wood_end_uv(obj):
    mesh=obj.data;u0,v0,u1,v1=H.uv_rect('wood_end');low,high=H.Vector((0,0,0)),H.Vector((0,0,0))
    ys=[v.co.y for v in mesh.vertices];zs=[v.co.z for v in mesh.vertices]
    for face in mesh.polygons:
        if abs(face.normal.x)<.80:continue
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            mesh.uv_layers.active.data[li].uv=(u0+(p.y-min(ys))/(max(ys)-min(ys))*(u1-u0),v0+(p.z-min(zs))/(max(zs)-min(zs))*(v1-v0))

BUILDERS={'Alloy':alloy,'Assembly':assembly,'Resin':resin,'Wood':wood,'Precision':precision}
receipt={'stage':'authoring','assets':{},'runtime_tested':False,'preview_rendered':False}
for key,builder in BUILDERS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    H.REGIONS=SPEC['assets'][key]['regions'];H.PARTS=[];H.MAT=H.make_material(key);builder()
    source=ROOT/'Authored'/(SPEC['assets'][key]['mesh']+'_Source.blend')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in H.PARTS:
        obj.select_set(True)
        if obj.get('wood_end_grain'):wood_end_uv(obj)
    bpy.context.view_layer.objects.active=H.PARTS[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    deps=bpy.context.evaluated_depsgraph_get();parts=[]
    for obj in H.PARTS:
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
        export=bpy.data.objects.new(obj.name+'_Export',mesh);bpy.context.collection.objects.link(export)
        export.matrix_world=obj.matrix_world.copy()
        if obj.modifiers:H.project_uv(export,obj['surface_region'])
        if obj.get('wood_end_grain'):wood_end_uv(export)
        parts.append(export)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();game=bpy.context.object
    game.name=SPEC['assets'][key]['mesh'];game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
    game.data.materials.clear();game.data.materials.append(H.MAT)
    for face in game.data.polygons:face.material_index=0
    triangulate=game.modifiers.new('Export triangulation','TRIANGULATE');triangulate.quad_method='FIXED';triangulate.ngon_method='BEAUTY'
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    points=[v.co for v in game.data.vertices]
    low=Vector([min(v[i] for v in points) for i in range(3)]);high=Vector([max(v[i] for v in points) for i in range(3)])
    shift=Vector((-(low.x+high.x)/2,-(low.y+high.y)/2,-low.z))
    game.data.transform(Matrix.Translation(shift));low+=shift;high+=shift
    extent=high-low;game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(low+high)*.5);collision=bpy.context.object
    collision.name='UCX_'+game.name+'_00';collision.scale=extent
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    H.select(game);collision.select_set(True)
    fbx=ROOT/'Export'/(game.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
    H.select(game);game.scale=(.01,.01,.01);scene.unit_settings.scale_length=1
    glb=ROOT/'Export'/(game.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
    receipt['assets'][key]={**SPEC['assets'][key], 'source':str(source),'fbx':str(fbx),'glb':str(glb),
        'triangles_lod0':triangles,'source_components':len(H.PARTS),'actual_dimensions_cm':list(extent),
        'pivot':'Game exports bottom centred, +Z up','collision':'one authored UCX box',
        'geometry_features':[o.name for o in H.PARTS]}
    (ROOT/'model_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('MAINTENANCE_MODEL_EXPORTED',key,triangles,list(extent),flush=True)
receipt['stage']='sources_and_exports_saved'
(ROOT/'model_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
