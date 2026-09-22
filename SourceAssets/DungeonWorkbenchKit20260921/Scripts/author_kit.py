"""Rebase approved meshes to reusable local pivots; author the dependent power lead."""
from pathlib import Path
import bpy,json,math,hashlib,re
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';CFG=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'));SRC=json.loads((ROOT/'Config/sources.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
ROOT_B=Vector((10,-1.48,0));WORLD=Matrix(((-1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
H=CFG['table_height_cm'];H0=CFG['original_table_height_cm'];manifest=dict(id=CFG['id'],components=[],source_blend=str(OUT/'DungeonWorkbenchKit.blend'),tests_run=False,renders_run=False)
def ue(v):return [v.x*100,-v.y*100,v.z*100]
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def clean(name):return re.sub(r'\.\d{3}$','',name)

def strip_old_bottles(ob):
    # These two containers were formerly disconnected islands inside BenchRetained.
    # Copy untouched face corners verbatim, including custom normals, UVs and colours.
    src=ob.data
    inside={v.index for v in src.vertices if 1.055<=10-v.co.x<=1.29 and 3.915<=-v.co.y<=4.025 and .93995<v.co.z<1.24}
    faces=[f for f in src.polygons if not all(i in inside for i in f.vertices)]
    used=sorted({i for f in faces for i in f.vertices});indices={old:new for new,old in enumerate(used)}
    loops=[i for f in faces for i in f.loop_indices]
    normals=[src.corner_normals[i].vector.copy() for i in loops]
    me=bpy.data.meshes.new('Retained tools without former bottles')
    me.from_pydata([src.vertices[i].co[:] for i in used],[],[[indices[i] for i in f.vertices] for f in faces]);me.update()
    for m in src.materials:me.materials.append(m)
    for old,new in zip(faces,me.polygons):new.material_index=old.material_index;new.use_smooth=old.use_smooth
    for layer in src.uv_layers:
        dest=me.uv_layers.new(name=layer.name)
        for j,i in enumerate(loops):dest.data[j].uv=layer.data[i].uv
    for layer in src.color_attributes:
        dest=me.color_attributes.new(name=layer.name,type=layer.data_type,domain=layer.domain)
        for j,i in enumerate(loops if layer.domain=='CORNER' else used):dest.data[j].color=layer.data[i].color
    me.normals_split_custom_set(normals);ob.data=me

def close_table_joint(ob,component_id):
    if component_id not in ('Bench_BenchTop','Bench_BenchWear','Sculpt_BenchFrame','Fab_BenchRetained'):return
    me=ob.data;offsets={};derivatives={};normals=[n.vector.copy() for n in me.corner_normals]
    main_extend=(CFG['supports']['Main']['y'][1]-226)/100
    return_extend=(CFG['supports']['Return']['x'][1]+95)/100
    for v in me.vertices:
        x,y,z=10-v.co.x,-v.co.y,v.co.z;dx=dy=0;sx=sy=1
        if component_id=='Fab_BenchRetained':
            # Move only the rear fixing screws with the extended supporting tabletop.
            if x<.94 and y>3.5 and .938<=z<=.941:dy=main_extend
        elif x<.94:
            t=max(0,min(1,(y-1.7)/1.85));dy=main_extend*t
            if 1.7<y<3.55:sy+=main_extend/1.85
        else:
            t=max(0,min(1,(2.45-x)/1.40));dx=-return_extend*t
            if 1.05<x<2.45:sx+=return_extend/1.40
        v.co.x-=dx;v.co.y-=dy;offsets[v.index]=(dx,dy);derivatives[v.index]=(sx,sy)
    if component_id=='Bench_BenchTop':
        for f in me.polygons:
            for li in f.loop_indices:
                vi=me.loops[li].vertex_index;p=me.vertices[vi].co;dx,dy=offsets[vi]
                if f.material_index==0:me.uv_layers[0].data[li].uv.x+=(dy if 10-p.x<.94 else dx)/1.72
                if len(me.uv_layers)>1:me.uv_layers[1].data[li].uv=(10-p.x,-p.y)
    me.update()
    for li,n in enumerate(normals):
        sx,sy=derivatives[me.loops[li].vertex_index];n.x/=sx;n.y/=sy;n.normalize()
    me.normals_split_custom_set(normals)
def digest(ob):
    import array
    vals=array.array('f',[x for v in ob.data.vertices for x in v.co]);indices=array.array('I',[v for f in ob.data.polygons for v in f.vertices])
    sha=hashlib.sha256(vals.tobytes()+indices.tobytes())
    for layer in ob.data.uv_layers:sha.update(array.array('f',[x for p in layer.data for x in p.uv]).tobytes())
    sha.update(array.array('f',[x for n in ob.data.corner_normals for x in n.vector]).tobytes())
    sha.update(array.array('I',[f.material_index for f in ob.data.polygons]).tobytes())
    for layer in ob.data.color_attributes:sha.update(array.array('f',[x for p in layer.data for x in p.color]).tobytes())
    sha.update('|'.join(clean(m.name) for m in ob.data.materials).encode());return sha.hexdigest()
def emit(ob,e,pivot):
    active(ob);ob.data.transform(Matrix.Translation(-pivot));ob.data.update();ob.matrix_world=Matrix.Identity(4)
    if any(len(f.vertices)>3 for f in ob.data.polygons):
        tri=ob.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    ob.name='SM_WBK_'+e['id'];filepath=OUT/(ob.name+'.fbx');signature=digest(ob)
    stamps=OUT/'mesh-stamps.json';previous=json.loads(stamps.read_text()) if stamps.exists() else {}
    if previous.get(e['id'])!=signature or not filepath.exists():
        bpy.ops.export_scene.fbx(filepath=str(filepath),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    group=e['group'];group_origin=ROOT_B.copy()
    if group=='Table':group_origin.z=H0/100
    elif group=='Wall':group_origin.z=1.15
    elif group=='Lamp':group_origin=Vector((9.73,-2.13,H0/100))
    row=dict(e,name=ob.name,fbx=str(filepath),content_hash=signature,relative_location=ue(pivot-group_origin),materials=[clean(m.name) for m in ob.data.materials],triangles=sum(len(p.vertices)-2 for p in ob.data.polygons))
    row['material_paths']={slot:SRC['material_sources'].get(e['id']+'|'+slot) or (SRC['material_sources'].get(e['id']+'|FabGarage_Atlas') if slot.startswith('FabGarage_') else None) for slot in row['materials']}
    for slot in row['materials']:
        if slot.startswith('WBKBottle_'):row['material_paths'][slot]='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/BottleSources/MI_'+slot
    mins=[min(v.co[i] for v in ob.data.vertices) for i in range(3)];maxs=[max(v.co[i] for v in ob.data.vertices) for i in range(3)]
    row['local_bounds_cm']={'min':[mins[0]*100,-maxs[1]*100,mins[2]*100],'max':[maxs[0]*100,-mins[1]*100,maxs[2]*100]}
    if e.get('individual') and group=='Table':row['support']='Main' if pivot.x>9.05 else 'Return'
    manifest['components'].append(row);ob['component_id']=e['id'];ob['assembly_group']=group
    ob.location=pivot-ROOT_B
    if group in ('Table','Lamp'):ob.location.z+=(H-H0)/100
    if group=='Frame' and e['id']=='Sculpt_BenchFrame':ob.scale.z=(H-CFG['table_thickness_cm'])/(H0-CFG['table_thickness_cm'])
    print('WORKBENCH_LOCAL_COMPONENT',e['id'],flush=True)
for e in SRC['components']:
    if 'source_object' in e:
        with bpy.data.libraries.load(e['source_blend'],link=False) as (src,dst):dst.objects=[e['source_object']]
        ob=dst.objects[0]
        if not ob:raise RuntimeError('Missing source component '+e['id'])
        scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.data=ob.data.copy();ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
    else:
        with bpy.data.libraries.load(e['source_blend'],link=False) as (src,dst):dst.collections=[e['source_collection']]
        coll=dst.collections[0];scene.collection.children.link(coll);coll.hide_viewport=False;coll.hide_render=False;copies=[]
        for original in coll.objects:
            name=original.name
            socket=name.startswith(('Moulded socket plug','Plug gripping rib','Plug flexible boot','Moulded plug strain relief'))
            include=socket if e['part_filter']=='socket' else not socket and not name.startswith('Five millimetre power flex')
            if not include:continue
            dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(original.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
            me.transform(WORLD@original.matrix_world);cp=bpy.data.objects.new(name+'_local',me);scene.collection.objects.link(cp);copies.append(cp)
        active(copies[0])
        for cp in copies:cp.select_set(True)
        bpy.ops.object.join();ob=copies[0];coll.hide_viewport=True;coll.hide_render=True
    if e['id']=='Fab_BenchRetained':strip_old_bottles(ob)
    close_table_joint(ob,e['id'])
    group=e['group'];pivot=ROOT_B.copy()
    if group=='Table':pivot.z=H0/100
    elif group=='Wall':pivot.z=1.15
    elif group=='Lamp':pivot=Vector((9.73,-2.13,H0/100))
    if e.get('individual'):
        for axis in range(3):pivot[axis]=(min(v.co[axis] for v in ob.data.vertices)+max(v.co[axis] for v in ob.data.vertices))/2
        if group=='Table':pivot.z=min(v.co.z for v in ob.data.vertices)
    emit(ob,e,pivot)
# The only geometry dependent on desk height: a Bezier cable from wall plug to lamp inlet.
radius=CFG['power_cable']['diameter_mm']/20 # centimetres
clear=CFG['power_cable']['surface_clearance_mm']/10
z=H+radius+clear
socket=[a+b for a,b in zip(CFG['anchors']['WallOrigin'],CFG['anchor_offsets_cm']['SocketExit'])]
lamp=[a+b for a,b in zip(CFG['anchors']['LampBase'],CFG['anchor_offsets_cm']['LampEntry'])];lamp[2]+=H-H0
spans=[[socket,[-34,111,max(z,socket[2]-4)],[-22.5,114,z+1.65],[-21.5,105,z]],
       [[-21.5,105,z],[-20.6,102,z],[-20,86,z],[-21.2,80.5,z]],
       [[-21.2,80.5,z],[-21,73,z],[lamp[0]+.2,lamp[1]+3,max(z,lamp[2]+1.2)],lamp]]
points=[]
for span in spans:
    a,b,c,d=[Vector((p[0]/100,-p[1]/100,p[2]/100)) for p in span]
    for i in range(24):
        t=i/24;points.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
points.append(Vector((lamp[0]/100,-lamp[1]/100,lamp[2]/100)))
verts=[];faces=[];sides=24
for j,p in enumerate(points):
    t=(points[min(j+1,len(points)-1)]-points[max(j-1,0)]).normalized();axis=Vector((0,0,1)) if abs(t.z)<.93 else Vector((0,1,0));a=t.cross(axis).normalized();b=t.cross(a)
    for i in range(sides):ang=i*math.tau/sides;verts.append(p+(a*math.cos(ang)+b*math.sin(ang))*(radius/100))
for j in range(len(points)-1):
    for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+i for i in range(sides))])
me=bpy.data.meshes.new('Power lead');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new('Power lead',me);scene.collection.objects.link(ob)
rubber=next(m for m in bpy.data.materials if clean(m.name)=='WSBench_CableRubber');me.materials.append(rubber)
uv=me.uv_layers.new(name='UVMap')
for f in me.polygons:
    f.use_smooth=True
    for li in f.loop_indices:
        vi=me.loops[li].vertex_index;uv.data[li].uv=(vi%sides/sides,vi//sides/20)
me.transform(Matrix.Translation(ROOT_B));emit(ob,dict(id='PowerLead',group='Frame',collision=False,cast_shadow=True),ROOT_B)
manifest['power_route']={'spans_cm':spans,'diameter_mm':CFG['power_cable']['diameter_mm'],'table_height_cm':H,'surface_clearance_mm':CFG['power_cable']['surface_clearance_mm']}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'mesh-stamps.json').write_text(json.dumps({e['id']:e['content_hash'] for e in manifest['components']},indent=2),encoding='utf-8')
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=manifest['source_blend']);print('WORKBENCH_KIT_AUTHORED_NO_RENDER',len(manifest['components']))
