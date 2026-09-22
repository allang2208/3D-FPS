"""Fabricate the user's four workshop revisions in Blender; no rendering or tests."""
import bpy, json, math, random
from mathutils import Vector
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopDetail20260921')
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
R=random.Random(92143)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
recipes=json.loads((OUT/'material-manifest.json').read_text());materials={};groups={}
for key,recipe in recipes.items():
    m=bpy.data.materials.new('WSDetail_'+key);m.use_nodes=True
    p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p is None:
        p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Metallic'].default_value=recipe['metallic']
    p.inputs['Roughness'].default_value=recipe.get('roughness',.6)
    for ch,path in recipe['maps'].items():
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(path,check_existing=True)
        if ch!='BaseColor':n.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(n.outputs['Color'],normal.inputs['Color'])
            m.node_tree.links.new(normal.outputs['Normal'],p.inputs['Normal'])
        else:m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color' if ch=='BaseColor' else 'Roughness'])
    materials[key]=m

def add(group,verts,faces,mat,smooth=False,uvs=None):
    g=groups.setdefault(group,{'v':[],'f':[],'mat':[],'smooth':[],'uv':[]});offset=len(g['v'])
    g['v'].extend((10-x,-y,z) for x,y,z in verts)
    for i,face in enumerate(faces):
        g['f'].append(tuple(offset+j for j in face));g['mat'].append(mat)
        g['smooth'].append(smooth if isinstance(smooth,bool) else smooth[i]);g['uv'].append(uvs[i] if uvs else None)

def box(g,c,size,mat,angle=0):
    x,y,z=c;a,b,d=[v/2 for v in size];co,si=math.cos(angle),math.sin(angle)
    vs=[(x+i*co-j*si,y+i*si+j*co,z+k) for i,j,k in [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
    add(g,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def tube(g,points,r,mat,sides=24,cap=True):
    ps=[Vector(p) for p in points];vs=[]
    for i,p in enumerate(ps):
        t=(ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)]).normalized()
        axis=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
        a=t.cross(axis).normalized();b=t.cross(a).normalized()
        vs.extend(tuple(p+r*(math.cos(j*math.tau/sides)*a+math.sin(j*math.tau/sides)*b)) for j in range(sides))
    fs=[];sm=[]
    for i in range(len(ps)-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j));sm.append(True)
    if cap:fs.extend([tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))]);sm.extend([False,False])
    add(g,vs,fs,mat,sm)

def ring(g,c,axis,r,minor,mat,n=36):
    axis=Vector(axis).normalized();a=axis.cross(Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0))).normalized();b=axis.cross(a)
    points=[tuple(Vector(c)+r*(math.cos(i*math.tau/n)*a+math.sin(i*math.tau/n)*b)) for i in range(n+1)]
    tube(g,points,minor,mat,12,False)

def bolt(g,p,axis=(0,-1,0),r=.006):
    p=Vector(p);axis=Vector(axis).normalized()
    tube(g,[tuple(p),tuple(p+axis*.003)],r*1.4,'Steel',20)
    tube(g,[tuple(p+axis*.003),tuple(p+axis*.008)],r,'Steel',6)

def panel(g,c,right,up,w,h,mat,uv=(0,0,1,1)):
    c=Vector(c);right=Vector(right)*w/2;up=Vector(up)*h/2
    a,b,d,e=uv
    add(g,[tuple(c-right-up),tuple(c+right-up),tuple(c+right+up),tuple(c-right+up)],[(0,1,2,3)],mat,
        uvs=[[(a,b),(d,b),(d,e),(a,e)]])

def label(c,right,w,h,index):
    col=index%4;row=index//4
    uv=(col/4,(3-row)/4,(col+1)/4,(4-row)/4)
    panel('Markings',c,right,(0,0,1),w,h,'Labels',uv)

# Left cabinet: front-facing sheet-metal carcass and actual drawer gaps.
cx,cy=.60,.98;front=cy-.30
box('CabinetBody',(cx,cy,.20),(.80,.62,.045),'PaintRed')
box('CabinetBody',(cx,cy+.302,.535),(.79,.014,.65),'PaintRed')
for x in (cx-.39,cx+.39):
    box('CabinetBody',(x,cy,.535),(.016,.60,.65),'PaintRed')
    box('CabinetBody',(x,front-.007,.535),(.027,.023,.65),'PaintRed')
box('CabinetBody',(cx,cy,.872),(.84,.65,.038),'PaintRed')
box('CabinetBody',(cx,cy,.895),(.789,.601,.014),'DarkRubber')
for x in (cx-.411,cx+.411):box('CabinetBody',(x,cy,.913),(.017,.64,.055),'PaintRed')
box('CabinetBody',(cx,cy+.312,.913),(.84,.018,.055),'PaintRed')
box('CabinetBody',(cx,front+.055,.527),(.755,.12,.62),'DarkRubber')
z=.219
for i,h in enumerate((.122,.115,.097,.091,.081,.077)):
    mid=z+h/2;pull=.073 if i==4 else 0;yy=front-.015-pull
    if pull:
        box('CabinetHardware',(cx,yy+.15,z+.01),(.721,.34,.012),'Steel')
        for x in (cx-.352,cx+.352):box('CabinetHardware',(x,yy+.15,mid),(.014,.33,h-.012),'PaintRed')
        for x in (cx-.22,cx-.13,cx-.04,cx+.06,cx+.16):
            tube('CabinetHardware',[(x,yy+.08,z+.018),(x,yy+.08,z+.049)],.018,'Steel',24)
            tube('CabinetHardware',[(x,yy+.08,z+.049),(x,yy+.08,z+.053)],.009,'DarkRubber',6)
    box('CabinetBody',(cx,yy,mid),(.744,.026,h-.010),'PaintRed')
    box('CabinetHardware',(cx,yy-.022,mid+.019),(.588,.018,.023),'DarkRubber')
    tube('CabinetHardware',[(cx-.275,yy-.039,mid+.026),(cx+.275,yy-.039,mid+.026)],.008,'Steel',24)
    for x in (cx-.307,cx+.307):bolt('CabinetHardware',(x,yy-.015,mid+.022),r=.004)
    if i in (1,3,5):label((cx+.215,yy-.014,mid-.011),(1,0,0),.118,.045,{1:1,3:2,5:3}[i])
    # Paint breaks follow pulled edges, not a uniform noise scatter over the cabinet.
    for k in range(3 if i>2 else 1):
        x=cx+R.uniform(-.31,.16);ww=R.uniform(.008,.026)
        panel('Wear',(x,yy-.0132,z+.004),(1,0,0),(0,0,1),ww,.0024,'BareEdge')
    z+=h+.004
for x in (cx-.27,cx+.27):
    for y in (cy-.213,cy+.213):
        # Tyres contact z=0; fork plates and axle caps remain separate shapes.
        tube('CabinetHardware',[(x-.028,y,.064),(x+.028,y,.064)],.064,'DarkRubber',36)
        for dx in (-.030,.030):
            tube('CabinetHardware',[(x+dx,y,.064),(x+dx*1.14,y,.064)],.029,'Steel',24)
            box('CabinetHardware',(x+dx*1.3,y,.110),(.010,.038,.108),'Steel')
            bolt('CabinetHardware',(x+dx*1.4,y,.064),(1 if dx>0 else -1,0,0),.007)
        tube('CabinetHardware',[(x,y,.144),(x,y,.19)],.027,'Steel',28)
        box('CabinetHardware',(x,y,.178),(.11,.083,.018),'Steel')
        if y<cy:box('CabinetHardware',(x,y-.068,.121),(.043,.065,.009),'Steel')
for x in (cx-.38,cx+.38):
    for zz in (.246,.824):bolt('CabinetHardware',(x,front-.024,zz),r=.005)
tube('CabinetHardware',[(cx+.31,front-.031,.838),(cx+.31,front-.046,.838)],.012,'Steel',32)
panel('Wear',(cx+.31,front-.0463,.838),(1,0,0),(0,0,1),.002,.010,'DarkRubber')
label((cx-.25,front-.024,.832),(1,0,0),.17,.055,0)
# Visible side: recessed louvers, folded seams, push grip and service label.
for zz in (.35,.385,.42,.455,.49):
    box('CabinetHardware',(cx+.399,cy+.035,zz),(.004,.32,.014),'DarkRubber')
    box('CabinetHardware',(cx+.404,cy+.035,zz+.009),(.011,.32,.008),'PaintRed')
tube('CabinetHardware',[(cx+.395,cy-.18,.77),(cx+.475,cy-.18,.77),(cx+.475,cy+.17,.77),(cx+.395,cy+.17,.77)],.012,'Steel',24)
tube('CabinetHardware',[(cx+.475,cy-.12,.77),(cx+.475,cy+.11,.77)],.016,'DarkRubber',28)
label((cx+.399,cy-.02,.64),(0,1,0),.23,.097,11)
# Shallow tray and a few usable tools on the nonslip work surface.
box('CabinetHardware',(cx-.16,cy+.07,.919),(.26,.22,.019),'Steel')
for y in (cy-.04,cy+.18):box('CabinetHardware',(cx-.16,y,.934),(.26,.008,.034),'Steel')
for x in (cx-.29,cx-.03):box('CabinetHardware',(x,cy+.07,.934),(.008,.22,.034),'Steel')
for i in range(6):ring('CabinetHardware',(cx-.24+(i%3)*.07,cy+.015+(i//3)*.08,.932),(0,0,1),.013,.003,'Steel',24)
box('CabinetHardware',(cx+.135,cy-.055,.909),(.032,.21,.009),'Steel',-.12)
for yy in (cy-.155,cy+.035):box('CabinetHardware',(cx+.115,yy,.917),(.063,.014,.027),'Steel',-.12)

# Right rack: perforated angle posts, folded trays, bracing and fixed feet.
xf,xb=5.30,5.86;ya,yb=.48,2.25
for x in (xf,xb):
    for y in (ya,yb):
        box('RackFrame',(x,y,.017),(.115,.115,.024),'RackPaint')
        for dx in (-.033,.033):bolt('RackFrame',(x+dx,y,.030),(0,0,1),.006)
        # The front flange is built around real repeating rectangular apertures.
        for dy in (-.020,.020):box('RackFrame',(x,y+dy,1.04),(.005,.014,2.04),'RackPaint')
        for j in range(34):box('RackFrame',(x,y,.046+j*.059),(.005,.026,.041),'RackPaint')
        box('RackFrame',(x+.021,y+.025,1.04),(.046,.005,2.04),'RackPaint')
for z in (.245,.745,1.245,1.745):
    box('RackFrame',((xf+xb)/2,(ya+yb)/2,z),(.588,1.82,.018),'RackPaint')
    for x in (xf-.012,xb+.012):box('RackFrame',(x,(ya+yb)/2,z-.018),(.014,1.82,.043),'RackPaint')
    for y in (ya-.015,yb+.015):box('RackFrame',((xf+xb)/2,y,z-.018),(.588,.014,.043),'RackPaint')
    for y in (.86,1.52,1.98):box('RackFrame',((xf+xb)/2,y,z-.035),(.55,.026,.038),'RackPaint')
    for x in (xf,xb):
        for y in (ya,yb):
            bolt('RackFrame',(x-.006,y,z-.014),(-1,0,0),.006)
    for j in range(7):
        yy=R.uniform(.57,2.16);panel('Wear',(xf-.0192,yy,z-.011),(0,-1,0),(0,0,1),R.uniform(.009,.032),.003,'BareEdge')
for a,b in [((xb+.025,ya,.36),(xb+.025,yb,1.83)),((xb+.025,yb,.36),(xb+.025,ya,1.83))]:
    tube('RackFrame',[a,b],.010,'RackPaint',12)
for y in (ya,yb):tube('RackFrame',[(xf,y,.42),(xb,y,1.71)],.008,'Steel',12)
label((xf-.021,1.37,1.70),(0,-1,0),.28,.095,10)

def bin_box(x,y,z,w=.39,depth=.40,height=.21,mat='BluePlastic',idx=4):
    g='RackStock';front=x-depth/2;back=x+depth/2
    box(g,(x,y,z+.010),(depth,w,.02),mat)
    box(g,(back,y,z+height/2),(.015,w,height),mat)
    box(g,(front,y,z+.052),(.015,w,.104),mat)
    for yy in (y-w/2,y+w/2):
        # Thin side walls rise toward the rear: recognizably open industrial bins.
        v=[(front,yy-.007,z),(back,yy-.007,z),(back,yy-.007,z+height),(front,yy-.007,z+.105),
           (front,yy+.007,z),(back,yy+.007,z),(back,yy+.007,z+height),(front,yy+.007,z+.105)]
        add(g,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
        tube(g,[(front,yy,z+.105),(back,yy,z+height)],.006,mat,12)
    box(g,(front-.010,y,z+.058),(.005,.22,.070),'DarkRubber')
    label((front-.013,y,z+.058),(0,-1,0),.208,.062,idx)
    return front

for yy,idx in [(.73,4),(1.19,5),(1.70,6)]:
    bin_box(5.58,yy,.258,idx=idx)
    for k in range(5):
        x=R.uniform(5.44,5.71);y=yy+R.uniform(-.12,.12)
        ring('RackStock',(x,y,.302+R.uniform(0,.024)),(0,0,1),.02+idx*.001,.005,'Steel',24)
for yy,idx in [(.83,7),(1.33,13)]:
    bin_box(5.58,yy,.758,w=.40,height=.19,mat='RackPaint',idx=idx)
    for k in range(4):
        y=yy-.12+k*.08
        tube('RackStock',[(5.49,y,.79),(5.68,y+.025,.805)],.014,'Steel',20)
        ring('RackStock',(5.49,y,.80),(1,0,0),.019,.004,'DarkRubber',24)

def carton(x,y,z,w,d,h,idx,open_top=False):
    g='RackStock';mat='Cardboard'
    box(g,(x,y,z+.008),(d,w,.016),mat)
    for xx in (x-d/2,x+d/2):box(g,(xx,y,z+h/2),(.011,w,h),mat)
    for yy in (y-w/2,y+w/2):box(g,(x,yy,z+h/2),(d,.011,h),mat)
    if open_top:
        box(g,(x+d/2+.055,y,z+h+.012),(.13,w,.009),mat)
        box(g,(x-d/2-.037,y,z+h-.008),(.088,w,.009),mat)
    else:
        for yy in (y-w/4,y+w/4):box(g,(x,yy,z+h),(d,w/2-.005,.010),mat)
        box(g,(x,y,z+h+.006),(d+.007,.052,.002),'BareEdge')
    label((x-d/2-.0058,y,z+h*.58),(0,-1,0),min(w*.72,.24),min(h*.55,.11),idx)

carton(5.57,1.90,.758,.43,.42,.27,8)
carton(5.59,.78,1.258,.48,.43,.25,9,True)
carton(5.60,1.68,1.758,.47,.46,.30,8)
carton(5.58,2.01,1.258,.31,.39,.19,15)
# Coil on an open shelf plus two upright filter elements with pleated silhouettes.
for i in range(4):ring('RackStock',(5.56,1.72,1.286+i*.019),(0,0,1),.135,.008,'DarkRubber',48)
tube('RackStock',[(5.43,1.72,1.30),(5.38,1.84,1.27),(5.36,1.93,1.28)],.008,'DarkRubber',18)
for yy in (1.11,1.34):
    for zz in (1.774,1.976):tube('RackStock',[(5.59,yy,zz),(5.59,yy,zz+.013)],.070,'Steel',32)
    tube('RackStock',[(5.59,yy,1.788),(5.59,yy,1.98)],.058,'Cardboard',32)
    for j in range(28):
        a=j*math.tau/28;x=5.59+math.cos(a)*.059;y=yy+math.sin(a)*.059
        tube('RackStock',[(x,y,1.791),(x,y,1.975)],.0038,'Cardboard',8)
    ring('RackStock',(5.59,yy,1.993),(0,0,1),.048,.008,'DarkRubber',32)

# Whiteboard replacing the old ambiguous electrical slab, mounted against the rear wall.
cx,yy,cz=3.60,3.955,1.79;ww,hh=1.84,1.14
box('WhiteboardFrame',(cx,yy,cz),(ww,.045,hh),'DarkRubber')
for x in (cx-ww/2,cx+ww/2):box('WhiteboardFrame',(x,yy-.025,cz),(.028,.035,hh+.015),'Steel')
for z in (cz-hh/2,cz+hh/2):box('WhiteboardFrame',(cx,yy-.025,z),(ww,.035,.027),'Steel')
for x in (cx-ww/2,cx+ww/2):
    for z in (cz-hh/2,cz+hh/2):
        box('WhiteboardFrame',(x,yy-.030,z),(.044,.041,.044),'DarkRubber')
        bolt('WhiteboardFrame',(x,yy-.052,z),r=.004)
panel('WhiteboardFace',(cx,yy-.024,cz),(1,0,0),(0,0,1),ww-.034,hh-.034,'Whiteboard')
# Folded pen tray, end caps, markers and a felt eraser.
trayz=cz-hh/2-.044
box('WhiteboardFrame',(cx,yy-.076,trayz),(1.08,.15,.010),'Steel')
box('WhiteboardFrame',(cx,yy-.148,trayz+.018),(1.08,.010,.044),'Steel')
for x in (cx-.54,cx+.54):box('WhiteboardFrame',(x,yy-.080,trayz+.018),(.012,.15,.044),'DarkRubber')
for i,mat in enumerate(('BluePlastic','PaintRed','DarkRubber')):
    x=cx-.37+i*.18
    tube('WhiteboardFrame',[(x,yy-.078,trayz+.016),(x+.13,yy-.078,trayz+.016)],.008,'Steel',24)
    tube('WhiteboardFrame',[(x+.13,yy-.078,trayz+.016),(x+.16,yy-.078,trayz+.016)],.0085,mat,24)
box('WhiteboardFrame',(cx+.36,yy-.082,trayz+.026),(.112,.055,.034),'BluePlastic')
box('WhiteboardFrame',(cx+.36,yy-.082,trayz+.009),(.114,.057,.011),'DarkRubber')
for x,z in [(cx+.82,cz+.44),(cx-.82,cz+.45)]:
    tube('WhiteboardFrame',[(x,yy-.025,z),(x,yy-.040,z)],.014,'BluePlastic',28)

# Retain the ceiling service route while removing dangling branches over the workbench.
for h,r in [(2.78,.065),(3.03,.046)]:
    tube('ServiceLines',[(.19,3.81,h),(5.74,3.81,h),(5.79,3.79,h),(5.81,3.72,h),(5.81,0,h)],r,'RackPaint',32)
    ring('ServiceLines',(.23,3.81,h),(1,0,0),r+.003,.007,'Steel',32)
for x in (4.47,5.04):
    low=2.42 if x==4.47 else 2.1
    tube('ServiceLines',[(x,3.99,low),(x,3.99,3.12),(x,3.89,3.16),(.45,3.89,3.16),(.19,3.68,3.16),(.19,2.62,3.16),(.19,2.62,1.35)],.017,'Steel',24)

replace={'CabinetBody':'DGN_Room_WS_ToolCart','CabinetHardware':'DGN_Room_WS_CartDetail',
         'RackFrame':'DGN_Room_WS_PartsRack','RackStock':'DGN_Room_WS_RackContents','ServiceLines':'DGN_Room_WS_Utilities'}
objects=[];manifest={'objects':[],'remove_actors':['DGN_AV2_Workshop_Bypass','DGN_AV2_Workshop_Electrical'],
                   'source_blend':str(OUT/'DungeonWorkshopDetail.blend'),'coordinate_space':'Blender metres, world baked; Unreal mirrors Y',
                   'tests_run':False,'screenshots_taken':False}
for name,g in groups.items():
    mesh=bpy.data.meshes.new('SM_WSDetail_'+name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj)
    used=list(dict.fromkeys(g['mat']))
    for key in used:mesh.materials.append(materials[key])
    uv=mesh.uv_layers.new(name='UVMap')
    for face,key,sm,faceuv in zip(mesh.polygons,g['mat'],g['smooth'],g['uv']):
        face.material_index=used.index(key);face.use_smooth=sm
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=faceuv[j] if faceuv else (p[dims[0]]/.5,p[dims[1]]/.5)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if name not in ('Markings','Wear','WhiteboardFace','ServiceLines'):
        bevel=obj.modifiers.new('Rolled and broken edges','BEVEL');bevel.width=.0015;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.65
        bevel.harden_normals=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
        weighted=obj.modifiers.new('Weighted flat-panel normals','WEIGHTED_NORMAL');weighted.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=weighted.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    obj.select_set(False);objects.append(obj)
    file=OUT/(obj.name+'.fbx')
    entry={'name':obj.name,'actor':replace.get(name,'DGN_WSDetail_'+name),'replace':name in replace,
           'collision':name in ('CabinetBody','RackFrame','ServiceLines','WhiteboardFrame'),
           'fbx':str(file),'materials':used}
    manifest['objects'].append(entry)
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,global_scale=1,use_mesh_modifiers=True,
        mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
for image in bpy.data.images:
    if image.source=='FILE' and Path(bpy.path.abspath(image.filepath)).exists():image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkshopDetail.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WORKSHOP_AUTHORED',len(objects),'NO_RENDER')
