"""Precision support frames, traversal pipes and clipped garden soil geometry."""
import math,json,random
from ecology_garden_layout import bed_margin,bed_height

H=None;VAULT_HULLS=[]

def setup(host):
    global H,original_pipe
    H=host;original_pipe=H['detail'].smooth_pipe;H['detail'].smooth_pipe=pipe

def reset():VAULT_HULLS.clear()

def pipe(points,radius):
    group=H['G'].get('CoarsePipes');nv=len(group['v']) if group else 0;nf=len(group['f']) if group else 0
    nh=len(H['v4'].PIPE_HULLS)
    original_pipe(points,radius)
    if radius<.04 or max(p[2] for p in points)>1.5:return
    source=H['G']['CoarsePipes'];target=H['group']('VaultPipes');offset=len(target['v'])
    target['v'].extend(source['v'][nv:]);target['f'].extend(tuple(i-nv+offset for i in f) for f in source['f'][nf:])
    for key in ('m','uv','smooth'):target[key].extend(source[key][nf:]);del source[key][nf:]
    del source['v'][nv:];del source['f'][nf:]
    VAULT_HULLS.extend(H['v4'].PIPE_HULLS[nh:]);del H['v4'].PIPE_HULLS[nh:]

def bed_supports():
    box,beam,detail=H['box'],H['beam'],H['detail']
    # Basin slab top is -1.24 m. Footplates sit on it, uprights contact the
    # existing bed end beams, and all bracing remains underneath the planting.
    for cx in (-7,7):
        for cy in (-3.8,3.8):
            for dx in (-2.92,2.92):
                for dy in (-.58,.58):
                    x,y=cx+dx,cy+dy
                    box('BedSupports',(x,y,-1.225),(.30,.25,.03),'BareSteel')
                    box('BedSupports',(x,y,-.63),(.085,.085,1.16),'PaintedSteel')
                    box('BedSupports',(x,y,-.068),(.20,.17,.055),'BareSteel')
                    for bx in (-.10,.10):
                        for by in (-.075,.075):detail.fastener((x+bx,y+by,-1.204),(0,0,1),.009,'BedSupportHardware')
                beam('BedSupports',(cx+dx,cy-.58,-1.14),(cx+dx,cy+.58,-.15),.038,.038,'BareSteel')
            for dy in (-.58,.58):
                box('BedSupports',(cx,cy+dy,-1.035),(5.93,.055,.055),'BareSteel')
                beam('BedSupports',(cx-2.92,cy+dy,-1.05),(cx-.65,cy+dy,-.16),.036,.036,'BareSteel')
                beam('BedSupports',(cx+2.92,cy+dy,-1.05),(cx+.65,cy+dy,-.16),.036,.036,'BareSteel')

def garden(r):
    poly,beam=H['poly'],H['beam']
    vs=[];faces=[];uv=[];edge_segments=[]
    step=.32;x0=-22.2;y0=-13.2;nx=140;ny=80
    def vertex(x,y):return (x,y,bed_margin(x,y))
    def clip(tri):
        out=[]
        for a,b in zip(tri,tri[1:]+tri[:1]):
            if a[2]>=0:out.append(a)
            if (a[2]>=0)!=(b[2]>=0):
                t=a[2]/(a[2]-b[2]);out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,0.))
        return out
    for ix in range(nx):
        for iy in range(ny):
            x=x0+ix*step;y=y0+iy*step
            square=[vertex(x,y),vertex(x+step,y),vertex(x+step,y+step),vertex(x,y+step)]
            for tri in ([square[0],square[1],square[2]],[square[0],square[2],square[3]]):
                points=clip(tri)
                if len(points)<3:continue
                first=len(vs)
                for px,py,_ in points:vs.append((px,py,bed_height(px,py,H['v4'].height_sample(px/.85,py/.85))))
                faces.append(tuple(range(first,len(vs))));uv.append([(px/.85,py/.85) for px,py,_ in points])
                for a,b in zip(points,points[1:]+points[:1]):
                    if a[2]==0 and b[2]==0 and math.hypot(a[0]-b[0],a[1]-b[1])>.005:edge_segments.append((a,b))
    poly('SoilBed',vs,faces,'SoilBed',uv,True)
    for a,b in edge_segments:
        beam('GardenEdging',(a[0],a[1],.029),(b[0],b[1],.029),.035,.058,'BareSteel')
    # Irrigation emitter stakes stay in the beds and do not obstruct the route.
    for i,p in enumerate(r['plants']):
        x,y=p['position'][:2];p['position'][2]=bed_height(x,y,H['v4'].height_sample(x/.85,y/.85))
        if i%15==0:
            z=p['position'][2];H['detail'].tube('GardenIrrigation',[(x+.13,y,z),(x+.13,y,z+.11)],.006,'Rubber',12)
    for tree in [r['hero_tree']]+r.get('trees',[]):
        x,y=tree['position'][:2]
        tree['position'][2]=bed_height(x,y,H['v4'].height_sample(x/.85,y/.85))

def monitor_front():
    box,beam,glazing=H['box'],H['beam'],H['glazing']
    # Window banks and door jambs are separately supported; the door opening
    # remains clear above the leaf, with a full lintel up to the office roof.
    for x0,x1 in ((-24,-18.415),(-17.185,-16)):
        box('MonitorSills',((x0+x1)/2,7,.46),(x1-x0,.28,.92),'Concrete')
    box('Walls',(-20,7,3.44),(8,.28,.32),'Concrete')
    for x in (-23.92,-18.49,-17.11,-16.08):box('Walls',(x,7,2.10),(.16,.28,2.36),'Concrete')
    box('Walls',(-17.8,7,2.885),(1.23,.28,.79),'Concrete')
    glazing((-23.82,6.84,0),(-18.57,6.84,0),.98,3.28,divisions=3)
    glazing((-17.03,6.84,0),(-16.18,6.84,0),.98,3.28,divisions=1)
    for x in (-18.39,-17.21):box('MonitorDoorFrame',(x,6.84,1.235),(.07,.20,2.47),'PaintedSteel')
    box('MonitorDoorFrame',(-17.8,6.84,2.455),(1.25,.20,.07),'PaintedSteel')
    for x in (-18.344,-17.256):box('MonitorDoorFrame',(x,6.882,1.21),(.016,.018,2.40),'Rubber')
    box('MonitorDoorFrame',(-17.8,6.882,2.408),(1.072,.018,.016),'Rubber')
    for x in (-18.39,-17.21):
        for z in (.15,1.22,2.29):H['detail'].fastener((x,6.729,z),(0,-1,0),.009,'MonitorDoorFrame')

def glass_assets():
    """Fit the existing hospital shard UV contract to the full-size panes."""
    bpy,bmesh=H['bpy'],H['bmesh'];out=H['OUT'];records=H['records'];base=H['MESHBASE']
    source=H['PROJECT']/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/manifest.json'
    material=next(i for i in json.loads(source.read_text('utf8'))['objects'] if i['name']=='SM_SW_WindowPaneV5')['materials']
    glass=bpy.data.materials.new('RS_Glass')
    # A single material slot uses exactly the accepted station pane material.
    material={'RS_Glass':next(iter(material.values()))}
    def cube(name,center,size,mat=None):
        bpy.ops.mesh.primitive_cube_add(size=1,location=center);obj=bpy.context.object;obj.name=name;obj.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if mat:obj.data.materials.append(mat)
        return obj
    def export(obj,kind,boxes=(),shards=0):
        name='SM_Eco_'+kind;obj.name=name
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        modifier=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=modifier.name)
        collision=[cube('UCX_'+name+'_'+str(i).zfill(2),c,s) for i,(c,s) in enumerate(boxes)]
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        for c in collision:c.select_set(True)
        bpy.context.view_layer.objects.active=obj;fbx=out/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        for c in collision:bpy.data.objects.remove(c,do_unlink=True)
        records.append(dict(name=name,kind=kind,room_id='Interaction',asset=base+'/Meshes/'+name,fbx=str(fbx),
            materials=material,triangles=len(obj.data.polygons),collision=bool(boxes),nanite=False,
            simple_collision_hulls=len(boxes),assembly_only=True,fracture_shards=shards))
    ward=(H['PROJECT']/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8')
    context=dict(bpy=bpy,math=math,random=random,cube=cube,export=export,glass=glass)
    exec(compile(ward[ward.index('def clipped('):ward.index("panes('Door'")],'shared_glass_shards','exec'),context)
    for kind,w,h,nx,nz in [('NurseryWindow',5.59,2.29,24,12),('MonitorWide',1.68,2.23,10,12),('MonitorNarrow',.78,2.23,6,12)]:
        context['panes'](kind,w,h,.0065,nx,nz,5104+nx)
