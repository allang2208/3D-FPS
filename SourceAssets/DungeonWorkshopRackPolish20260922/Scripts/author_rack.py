"""Author a continuous service cable and gravity-settled bin contents; no preview render."""
from pathlib import Path
import bpy,json,math,random
from mathutils import Vector,Matrix,Euler
TASK=Path(__file__).resolve().parents[1];OLD=TASK.parent/'DungeonWorkshopDetail20260921'
# Reuse only the original material setup and primitive helpers, never its scene pass.
text=(OLD/'Scripts/author_workshop.py').read_text(encoding='utf-8')
exec(compile(text.split('# Left cabinet:')[0],'rack_shared_primitives','exec'),globals())
ROOT=TASK;OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'Config/layout.json').read_text());R=random.Random(CFG['seed'])
MATPATH=json.loads((OLD/'Receipts/asset-import.json').read_text())['materials']
for key,col,rough in [('PackingTape',(.26,.175,.085),.72),('FuseCeramic',(.49,.49,.43),.62)]:
    m=bpy.data.materials.new('WSRack_'+key);m.use_nodes=True
    p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not p:p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');o=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs[0],o.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;materials[key]=m
    MATPATH[key]='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopRackPolish/Materials/MI_WSRack_'+key
with bpy.data.libraries.load(str(TASK.parent/'DungeonWorkshopBenchPolish20260921/Authored/DungeonWorkshopBenchPolish.blend'),link=False) as (src,dst):dst.materials=['WSBench_CableRubber']
materials['CableRubber']=dst.materials[0];MATPATH['CableRubber']='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/InUse/MI_WBK_WSBench_CableRubber'

def paper_uv(index,u,v):
    col=index%4;row=index//4;return ((col+u)/4,(3-row+v)/4)

def solid_box(g,c,size,mat,label_info=None,tape=False):
    """Subdivide one solid shell so print/tape replace faces instead of floating overlays."""
    x,y,z=c;hx,hy,hz=[v/2 for v in size];xs=[-hx,hx];ys=[-hy,hy];zs=[-hz,hz]
    if label_info:
        idx,lw,lh,lz=label_info;ys=sorted(set(ys+[-lw/2,lw/2]));zs=sorted(set(zs+[lz-lh/2,lz+lh/2]))
    if tape:ys=sorted(set(ys+[-min(.026,hy),min(.026,hy)]))
    vs=[];lookup={};fs=[];keys=[];uvs=[]
    def vertex(p):
        if p not in lookup:lookup[p]=len(vs);vs.append((x+p[0],y+p[1],z+p[2]))
        return lookup[p]
    def quad(points,normal):
        ps=[Vector(p) for p in points]
        if (ps[1]-ps[0]).cross(ps[2]-ps[0]).dot(Vector(normal))<0:points=list(reversed(points))
        mid=sum((Vector(p) for p in points),Vector())/4;key=mat;uv=None
        if label_info and normal==(-1,0,0) and abs(mid.y)<lw/2-1e-8 and abs(mid.z-lz)<lh/2-1e-8:
            key='Labels';uv=[paper_uv(idx,.5-p[1]/lw,.5+(p[2]-lz)/lh) for p in points]
        if tape and normal==(0,0,1) and abs(mid.y)<.026:key='PackingTape'
        fs.append(tuple(vertex(tuple(p)) for p in points));keys.append(key);uvs.append(uv)
    for xx,normal in [(-hx,(-1,0,0)),(hx,(1,0,0))]:
        for ya,yb in zip(ys,ys[1:]):
            for za,zb in zip(zs,zs[1:]):quad([(xx,ya,za),(xx,yb,za),(xx,yb,zb),(xx,ya,zb)],normal)
    for yy,normal in [(-hy,(0,-1,0)),(hy,(0,1,0))]:
        for za,zb in zip(zs,zs[1:]):quad([(-hx,yy,za),(hx,yy,za),(hx,yy,zb),(-hx,yy,zb)],normal)
    for zz,normal in [(-hz,(0,0,-1)),(hz,(0,0,1))]:
        for ya,yb in zip(ys,ys[1:]):quad([(-hx,ya,zz),(hx,ya,zz),(hx,yb,zz),(-hx,yb,zz)],normal)
    for face,key,uv in zip(fs,keys,uvs):add(g,vs,[face],key,False,[uv] if uv else None)

def rotate_group(name,center,angle):
    g=groups[name];c=Vector(center);m=Matrix.Rotation(angle,3,'Z')
    for i,v in enumerate(g['v']):
        p=m@(Vector((10-v[0],-v[1],v[2]))-c)+c;g['v'][i]=(10-p.x,-p.y,p.z)

def make_bin(b):
    name='Bin_'+b['id'];x=5.58;y=b['y'];z=b['base_z'];w=b['width'];h=b['height'];front=x-.20;back=x+.20;mat=b['material']
    solid_box(name,(x,y,z+.01),(.4,w,.02),mat)
    solid_box(name,(back,y,z+h/2),(.015,w,h),mat)
    solid_box(name,(front,y,z+.052),(.015,w,.104),mat)
    for yy in (y-w/2,y+w/2):
        vs=[(front,yy-.007,z),(back,yy-.007,z),(back,yy-.007,z+h),(front,yy-.007,z+.105),
            (front,yy+.007,z),(back,yy+.007,z),(back,yy+.007,z+h),(front,yy+.007,z+.105)]
        add(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
        tube(name,[(front,yy,z+.105),(back,yy,z+h)],.006,mat,20)
    solid_box(name,(front-.010,y,z+.058),(.005,.22,.070),'DarkRubber',(b['label'],.208,.062,0))
    return name

placements=[];bin_groups=[];item_groups=[]
for b in CFG['bins']:
    name=make_bin(b);bin_groups.append(name)
    for k in range(b['items']):
        g='Item_'+b['id']+'_'+str(k+1);kind=b['id'];r=R.uniform(.019,.030)
        if kind=='Seals':ring(g,(0,0,0),(0,0,1),r,R.uniform(.0034,.0052),'DarkRubber',48)
        elif kind=='Bearings':
            ring(g,(0,0,0),(0,0,1),r,.005,'Steel',48)
            ring(g,(0,0,.0045),(0,0,1),r-.002,.0023,'Steel',48)
            ring(g,(0,0,0),(0,0,1),r-.007,.002,'DarkRubber',48)
        elif kind=='Fasteners':
            if k%3==0:ring(g,(0,0,0),(0,0,1),R.uniform(.012,.021),.0032,'Steel',40)
            else:
                length=R.uniform(.061,.104);tube(g,[(-length/2,0,0),(length/2,0,0)],.0052,'Steel',20)
                tube(g,[(-length/2,0,0),(-length/2+.010,0,0)],.010,'Steel',6)
                for j in range(6):ring(g,(length/2-.024+j*.004,0,0),(1,0,0),.0055,.0007,'Steel',20)
        elif kind=='Electrical':
            length=R.uniform(.066,.094);tube(g,[(-length/2,0,0),(length/2,0,0)],.009,'FuseCeramic',32)
            for s in (-1,1):
                a=s*(length/2-.010);bb=s*(length/2+.002);tube(g,[(a,0,0),(bb,0,0)],.010,'Steel',32)
                ring(g,(a,0,0),(1,0,0),.010,.001,'Steel',32)
            ring(g,(0,0,0),(1,0,0),.0091,.0013,'DarkRubber',32)
        else:
            length=R.uniform(.077,.138);radius=R.uniform(.012,.017)
            tube(g,[(-length/2,0,0),(length/2,0,0)],radius,'Steel',32,False)
            for s in (-1,1):
                ring(g,(s*length/2,0,0),(1,0,0),radius-.002,.0022,'Steel',40)
            if k%2:ring(g,(-length*.31,0,0),(1,0,0),radius+.001,.0022,'DarkRubber',40)
        # Choose orientation and a bounded drop position once; settle under gravity below.
        yaw=R.uniform(-math.pi,math.pi);pitch=R.uniform(-.30,.30);roll=R.uniform(-.24,.24)
        m=Euler((roll,pitch,yaw),'XYZ').to_matrix();local=[]
        for v in groups[g]['v']:local.append(m@Vector((10-v[0],-v[1],v[2])))
        minx,maxx=min(p.x for p in local),max(p.x for p in local);miny,maxy=min(p.y for p in local),max(p.y for p in local)
        x=R.uniform(5.405-minx,5.755-maxx);y=R.uniform(b['y']-b['width']/2+.025-miny,b['y']+b['width']/2-.025-maxy)
        z=b['base_z']+.075+k*.041-min(p.z for p in local)
        groups[g]['v']=[(10-x-p.x,-y-p.y,z+p.z) for p in local]
        rotate_group(g,(5.58,b['y'],b['base_z']),math.radians(b['yaw_deg']))
        item_groups.append(g);placements.append(dict(group=g,bin=b['id'],drop_position_m=[x,y,z],yaw_rad=yaw))
    rotate_group(name,(5.58,b['y'],b['base_z']),math.radians(b['yaw_deg']))

def carton(name,x,y,z,w,d,h,index,opened=False):
    solid_box(name,(x,y,z+.008),(d,w,.016),'Cardboard')
    solid_box(name,(x-d/2,y,z+h/2),(.011,w,h),'Cardboard',(index,min(w*.72,.24),min(h*.55,.11),h*.08))
    solid_box(name,(x+d/2,y,z+h/2),(.011,w,h),'Cardboard')
    for yy in (y-w/2,y+w/2):solid_box(name,(x,yy,z+h/2),(d,.011,h),'Cardboard')
    if opened:
        solid_box(name,(x+d/2+.055,y,z+h+.012),(.13,w,.009),'Cardboard')
        solid_box(name,(x-d/2-.037,y,z+h-.008),(.088,w,.009),'Cardboard')
    else:solid_box(name,(x,y,z+h),(d,w,.010),'Cardboard',tape=True)

carton('Carton_Lower',5.57,1.90,.758,.43,.42,.27,8)
carton('Carton_Open',5.59,.78,1.258,.48,.43,.25,9,True)
carton('Carton_Top',5.60,1.68,1.758,.47,.46,.30,8)
carton('Carton_Records',5.58,2.01,1.258,.31,.39,.19,15)
# Purposeful, offset folded gaskets in the open carton.
for i in range(3):
    g='Carton_Gasket_'+str(i);ring(g,(5.56+i*.024,.76+i*.013,1.283+i*.011),(0,0,1),.065+i*.007,.004,'DarkRubber',64)
    rotate_group(g,(5.57,.78,1.28),-.10+i*.14)

for k,yy in enumerate((1.11,1.34)):
    g='Filter_'+str(k);xx=5.59+(-.017 if k else .018)
    for zz in (1.764,1.966):tube(g,[(xx,yy,zz),(xx,yy,zz+.013)],.070,'Steel',64)
    tube(g,[(xx,yy,1.778),(xx,yy,1.97)],.058,'Cardboard',64)
    for j in range(36):
        a=j*math.tau/36;x=xx+math.cos(a)*.059;y=yy+math.sin(a)*.059;tube(g,[(x,y,1.781),(x,y,1.965)],.0038,'Cardboard',12)
    ring(g,(xx,yy,1.983),(0,0,1),.048,.008,'DarkRubber',64)

# One continuous flexible cable; varying oval loops, a shallow twist and two relaxed ends.
c=CFG['cable'];cx,cy=c['center_m'];rx,ry=c['radii_m'];radius=c['diameter_mm']/2000;floor=c['shelf_top_m'];turns=c['turns']
coil=[];steps=760
for i in range(steps+1):
    t=i/steps*turns;a=math.pi+math.tau*t;shrink=1-.045*t
    x=cx+rx*shrink*math.cos(a)+.004*math.sin(t*1.65)
    y=cy+ry*shrink*math.sin(a)+.005*math.sin(t*1.33)
    z=floor+radius+.0005+t*(radius*2+.0014)+.0011*(1-math.cos(a-math.pi))
    coil.append(Vector((x,y,z)))
def bezier(p0,p1,p2,p3,n=46):
    p0,p1,p2,p3=map(Vector,(p0,p1,p2,p3));return [(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3 for t in [i/n for i in range(n)]]
tangent=(coil[1]-coil[0]).normalized();end_t=(coil[-1]-coil[-2]).normalized();z=floor+radius+.0005
start=bezier((5.343,1.875,z),(5.344,1.81,z),coil[0]-tangent*.053,coil[0])
exit1=bezier(coil[-1],coil[-1]+end_t*.044,(5.57,1.463,coil[-1].z),(5.615,1.463,z+.010))
exit2=bezier((5.615,1.463,z+.010),(5.635,1.467,z),(5.651,1.445,z),(5.669,1.427,z));exit2.append(Vector((5.669,1.427,z)))
tube('Cable_Continuous',start+coil+exit1[1:]+exit2,radius,'CableRubber',24)
for p,q in [(start[0],start[1]),(exit2[-1],exit2[-2])]:
    direction=(p-q).normalized();tube('Cable_EndBoot',[p-direction*.010,p+direction*.014],radius*1.16,'CableRubber',32)
    tube('Cable_EndBoot',[p+direction*.014,p+direction*.020],radius*.72,'DarkRubber',24)

# Create editable pieces. Printed regions are ordinary opaque faces on the solid panels.
source=bpy.data.collections.new('SOURCE_RackPolish');scene.collection.children.link(source);objects={}
for name,g in groups.items():
    me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update();ob=bpy.data.objects.new(name,me);source.objects.link(ob)
    used=list(dict.fromkeys(g['mat']))
    for key in used:me.materials.append(materials[key])
    uv=me.uv_layers.new(name='UVMap')
    for face,key,sm,faceuv in zip(me.polygons,g['mat'],g['smooth'],g['uv']):
        face.material_index=used.index(key);face.use_smooth=sm;axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for j,li in enumerate(face.loop_indices):
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=faceuv[j] if faceuv else (p[dims[0]]/.5,p[dims[1]]/.5)
    if name.startswith(('Bin_','Carton_')) and 'Gasket' not in name:
        # Joined grid corners preserve a single exterior face; no duplicate label plane.
        import bmesh
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001);bm.to_mesh(me);bm.free()
        bevel=ob.modifiers.new('Folded edges','BEVEL');bevel.width=.0009;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.65
    objects[name]=ob

def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob

# This simulation is part of asset fabrication, baked into the final static geometry.
scene.render.fps=60;scene.frame_start=1;scene.frame_end=180
for name in bin_groups+item_groups:
    ob=objects[name];active(ob)
    center=sum((v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices);ob.data.transform(Matrix.Translation(-center));ob.location=center
    bpy.ops.rigidbody.object_add();rb=ob.rigid_body;rb.type='PASSIVE' if name in bin_groups else 'ACTIVE'
    rb.collision_shape='MESH' if name in bin_groups else 'CONVEX_HULL';rb.use_margin=True;rb.collision_margin=.00035;rb.friction=.70;rb.restitution=.01
    if name in item_groups:rb.mass=.06;rb.linear_damping=.65;rb.angular_damping=.75
world=scene.rigidbody_world;world.substeps_per_frame=4;world.solver_iterations=24;world.point_cache.frame_end=180
for frame in range(1,181):scene.frame_set(frame)
dg=bpy.context.evaluated_depsgraph_get();settled={name:objects[name].evaluated_get(dg).matrix_world.copy() for name in bin_groups+item_groups}
for name,matrix in settled.items():
    ob=objects[name];active(ob);bpy.ops.rigidbody.object_remove();ob.matrix_world=matrix
scene.frame_set(1)
for p in placements:p['baked_matrix_blender']=list(sum(([float(v) for v in row] for row in objects[p['group']].matrix_world),[]))

dg=bpy.context.evaluated_depsgraph_get();copies=[]
for name,ob in objects.items():
    me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg);me.transform(ob.matrix_world)
    cp=bpy.data.objects.new(name+'_export',me);scene.collection.objects.link(cp);copies.append(cp)
active(copies[0])
for cp in copies:cp.select_set(True)
bpy.ops.object.join();stock=copies[0];stock.name='SM_WSRack_Stock'

# Preserve cabinet and shelf-header artwork, remove only the old rack-box overlays.
with bpy.data.libraries.load(str(OLD/'Authored/DungeonWorkshopDetail.blend'),link=False) as (src,dst):dst.objects=['SM_WSDetail_Markings']
old=dst.objects[0];me=old.data;faces=[f for f in me.polygons if not all(10-me.vertices[i].co.x>5.33 for i in f.vertices)]
verts=sorted({i for f in faces for i in f.vertices});remap={v:i for i,v in enumerate(verts)};new=bpy.data.meshes.new('Retained markings')
new.from_pydata([me.vertices[i].co[:] for i in verts],[],[[remap[i] for i in f.vertices] for f in faces]);new.update()
for m in me.materials:new.materials.append(m)
for src,dst in zip(faces,new.polygons):dst.material_index=src.material_index;dst.use_smooth=src.use_smooth
loops=[li for f in faces for li in f.loop_indices]
for layer in me.uv_layers:
    uv=new.uv_layers.new(name=layer.name)
    for dst,li in zip(uv.data,loops):dst.uv=layer.data[li].uv
mark=bpy.data.objects.new('SM_WSRack_Markings',new);scene.collection.objects.link(mark)
manifest={'objects':[],'materials':{m.name:MATPATH[key] for key,m in materials.items()},'source_blend':str(OUT/'DungeonWorkshopRackPolish.blend'),'seed':CFG['seed'],'placements':placements,'tests_run':False,'renders_run':False}
# Loaded label material may carry Blender's numeric suffix, map the exact exported slot.
for m in mark.data.materials:manifest['materials'][m.name]=MATPATH['Labels']
for ob in (stock,mark):
    active(ob);tri=ob.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    file=OUT/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    manifest['objects'].append(dict(name=ob.name,fbx=str(file),replaces='SM_WSDetail_RackStock' if ob==stock else 'SM_WSDetail_Markings'))
source.hide_render=True;source.hide_viewport=True
for im in bpy.data.images:
    if im.source=='FILE' and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=manifest['source_blend']);(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('RACK_ASSET_FABRICATION_SAVED',len(item_groups),'SETTLED_ITEMS',len(manifest['objects']),'MESHES_NO_RENDER')
