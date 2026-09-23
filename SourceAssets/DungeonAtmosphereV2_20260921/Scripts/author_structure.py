"""Blender authoring only: asymmetric corridor, side bays, a real breach and alcove.

No scene render or tests. All geometry is original; no factory-pack mesh is used.
Coordinates are metres in Blender, exported to FBX with its scene unit metadata.
"""
import bpy
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
R=random.Random(92121)
MAT_NAMES=['Concrete','IvoryTile','PaintedSteel','BareSteel','AncientStone','WetFloor','WarmGlass','CoolGlass']
COLORS=[(.24,.25,.235),(.48,.45,.35),(.095,.11,.065),(.055,.061,.060),(.25,.225,.17),(.085,.10,.094),(1,.52,.16),(.62,.79,1)]
MATS=[]
for name,color in zip(MAT_NAMES,COLORS):
    m=bpy.data.materials.new('V2_'+name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.72 if name not in ['IvoryTile','WetFloor'] else .32
    p.inputs['Metallic'].default_value=.8 if name=='BareSteel' else 0
    if name.endswith('Glass'):
        p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=3
    texture_dir=OUT/'Textures'
    for channel,input_name in [('BaseColor','Base Color'),('Roughness','Roughness'),('Metallic','Metallic'),('Normal','Normal')]:
        path=texture_dir/(name+'_'+channel+'.png')
        if path.exists():
            tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
            tex.image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
            source=tex.outputs['Color']
            if channel=='Normal':
                normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(source,normal.inputs['Color']);source=normal.outputs['Normal']
            m.node_tree.links.new(source,p.inputs[input_name])
    MATS.append(m)

groups={}
def group(name):
    return groups.setdefault(name,{'v':[],'f':[],'m':[]})

def poly(name,verts,faces,mat=0):
    g=group(name);n=len(g['v']);g['v'].extend(verts)
    g['f'].extend([tuple(n+i for i in face) for face in faces]);g['m'].extend([mat]*len(faces))

def box(name,center,size,mat=0,rz=0):
    x,y,z=center;a,b,c=[v*.5 for v in size];co,si=math.cos(rz),math.sin(rz)
    vs=[(x+px*co-py*si,y+px*si+py*co,z+pz) for px,py,pz in
        [(-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]]
    poly(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def tube(name,points,radius,mat=3,sides=10):
    # Parallel frame built from local tangent, no detached cylinder intersections.
    vs=[];ps=[Vector(p) for p in points]
    for i,p in enumerate(ps):
        tangent=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        a=tangent.cross(helper).normalized();b=tangent.cross(a).normalized()
        vs.extend([tuple(p+radius*(math.cos(j*math.tau/sides)*a+math.sin(j*math.tau/sides)*b)) for j in range(sides)])
    faces=[]
    for i in range(len(ps)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))])
    poly(name,vs,faces,mat)

def xz_prism(name,points,y,depth,mat=0):
    # Normalize the XZ polygon winding. +XZ orientation faces -Y, so the near
    # face keeps this order; reversing it makes every tile an inside-out shell.
    area=sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))
    if area<0:points=list(reversed(points))
    n=len(points);vs=[(x,y+offset,z) for offset in (-depth/2,depth/2) for x,z in points]
    # Cross sections in this file are convex or horizontally monotone polygons.
    faces=[tuple(range(n)),tuple(n+i for i in reversed(range(n)))]
    faces.extend([(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)])
    poly(name,vs,faces,mat)

def wall(name,axis,a,b,fixed,height=3.9,tile=True,inside=1):
    # 1.4 m concrete pours beneath a continuous load-bearing cap.
    cursor=a
    while cursor<b-.001:
        length=min(R.uniform(.9,1.55),b-cursor)
        pos=((cursor+length/2,fixed,height/2) if axis=='x' else (fixed,cursor+length/2,height/2))
        size=((length,.24,height) if axis=='x' else (.24,length,height))
        box(name,pos,size,0)
        cursor+=length
    if not tile:return
    for row in range(9):
        z=.24+row*.158
        x=a+.155
        while x<b-.10:
            missing=(math.sin(x*1.78+z*5)+math.cos(x*.93-z*3)>.95 and R.random()<.48)
            if not missing:
                length=min(.30,b-x+.145)
                # Thin ceramic relief with genuinely chipped corners and omissions.
                chip=R.uniform(.007,.04) if R.random()<.18 else .003
                pts=[(x-length/2,z-.074),(x+length/2-chip,z-.074),(x+length/2,z-.074+chip),
                     (x+length/2,z+.074),(x-length/2,z+.074)]
                if axis=='x':xz_prism(name+'_Tiles',pts,fixed+inside*.137,.024,1)
                else:
                    g=group(name+'_Tiles');before=len(g['v']);before_faces=len(g['f']);xz_prism(name+'_Tiles',pts,fixed+inside*.137,.024,1)
                    for i in range(before,len(g['v'])):
                        vx,vy,vz=g['v'][i];g['v'][i]=(vy,vx,vz)
                    # Swapping X/Y mirrors the prism; restore its outward winding.
                    for i in range(before_faces,len(g['f'])):g['f'][i]=tuple(reversed(g['f'][i]))
            x+=.31
    if axis=='x':box(name,((a+b)/2,fixed+inside*.13,.08),(b-a,.06,.16),3)
    else:box(name,(fixed+inside*.13,(a+b)/2,.08),(.06,b-a,.16),3)

def slab(name,rect,z,mat=0,ceiling=False):
    x0,y0,x1,y1=rect
    x=x0
    while x<x1-.001:
        dx=min(R.uniform(1.1,1.8),x1-x);y=y0
        while y<y1-.001:
            dy=min(R.uniform(1.2,2),y1-y)
            box(name,(x+dx/2,y+dy/2,z-.08),(dx-.004,dy-.004,.16),mat)
            y+=dy
        x+=dx
    # Continuous bed seals hairline slab seams while leaving the top joints visible.
    box(name,((x0+x1)/2,(y0+y1)/2,z-.20),(x1-x0,y1-y0,.16),mat)
    if ceiling:
        # Room height is the ceiling UNDERSIDE. Preserve the original slab RNG
        # consumption so this correction cannot reshuffle later walls/tiles.
        g=group(name);g['v']=[(vx,vy,vz+.28) for vx,vy,vz in g['v']]

# A corridor backbone with side excavations, not a chain of similarly sized rooms.
regions=[('MainCorridor',(0,0,22,4),3.9,0),('Dogleg',(22,0,26,10),4.25,0),
         ('EndLanding',(22,10,29,14),4.65,0),('Workshop',(4,-4.2,10,0),3.3,0),
         ('MachineBay',(8,4,13,8),4.25,0),('ServiceRecess',(14,-2.2,16.6,0),3.15,0),
         ('RuinNiche',(15,4,21.5,11.5),4.6,4)]
for name,rect,height,material in regions:
    slab(name+'_Floor',rect,0,material)
    slab(name+'_Ceiling',rect,height,0,ceiling=True)

# South edge openings: 5.2 m workshop and a smaller 1.8 m service recess.
for a,b in [(0,4.4),(9.6,14.4),(16.2,26)]:wall('Corridor_South','x',a,b,0,inside=1)
for a,b,h in [(4.4,9.6,3.05),(14.4,16.2,2.7)]:box('BayHeaders',((a+b)/2,0,(h+3.9)/2),(b-a,.40,3.9-h),0)
wall('EntryEnd','y',0,4,0,inside=1)
# North side: gated bay + deep irregular breach before the turn.
for a,b in [(0,8.3),(12.7,15),(21.5,22)]:wall('Corridor_North','x',a,b,4,inside=-1)
box('BayHeaders',(10.5,4,3.6),(4.4,.36,.6),0)
wall('Workshop','x',4,10,-4.2,3.3,inside=1)
wall('Workshop','y',-4.2,0,4,3.3,inside=1)
wall('Workshop','y',-4.2,0,10,3.3,inside=-1)
wall('MachineBay','x',8,13,8,4.25,inside=-1)
wall('MachineBay','y',4,8,8,4.25,inside=1)
wall('MachineBay','y',4,8,13,4.25,inside=-1)
wall('ServiceRecess','x',14,16.6,-2.2,3.15,inside=1)
wall('ServiceRecess','y',-2.2,0,14,3.15,inside=1)
wall('ServiceRecess','y',-2.2,0,16.6,3.15,inside=-1)
wall('Dogleg','y',0,10,26,4.25,inside=-1)
wall('Dogleg','y',4,14,22,4.25,inside=1)
wall('EndLanding','x',22,29,14,4.65,inside=-1)
wall('EndLanding','y',10,14,29,4.65,inside=-1)
wall('EndLanding','x',26,29,10,4.65,inside=1)
for axis,a,b,k,s in [('x',15,21.5,11.5,-1),('y',4,11.5,15,1),('y',4,11.5,21.5,-1)]:
    wall('RuinNiche',axis,a,b,k,4.6,False,s)

# Broken portal has an actual unobstructed negative space, not a solid wall decal.
left=[(15,0),(16.0,0),(16.12,.45),(15.8,.8),(16.20,1.25),(15.91,1.7),(16.18,2.15),(16.06,2.8),(16.5,3.18),(15,3.9)]
right=[(20.3,0),(21.5,0),(21.5,3.9),(19.9,3.32),(20.0,2.96),(20.47,2.60),(20.19,2.13),(20.52,1.62),(20.24,.91),(20.46,.4)]
top=[(15,3.9),(21.5,3.9),(20.0,3.28),(19.63,3.56),(19.20,3.43),(18.8,3.68),(18.35,3.48),(17.98,3.63),(17.45,3.43),(17.07,3.54),(16.5,3.18)]
for pts in (left,right,top):xz_prism('Breach_Structural',pts,4,.55,0)
for x,z,side in [(16.08,.8,1),(16.05,1.35,1),(16.1,2.2,1),(20.33,.9,-1),(20.28,1.8,-1),(20.05,2.85,-1)]:
    tube('Breach_Rebar',[(x,3.71,z),(x+side*.22,3.68,z+.04),(x+side*.39,3.53,z-.16)],.012,3,8)
for x in (15.65,20.9):
    box('Breach_Shoring',(x,3.66,1.87),(.19,.20,3.74),2)
    for z in (.22,.72,1.6,2.55,3.45):
        box('Breach_Shoring',(x,3.52,z),(.31,.055,.22),3)
box('Breach_Shoring',(18.275,3.66,3.70),(5.45,.23,.20),2)

# Slightly irregular concrete piers, ceiling beams, cable trays and hanging wiring.
for x in (2.8,6.6,10.8,14.7,21.6):
    for y in (.10,3.90):box('ConcreteSupports',(x,y,1.95),(.32,.38,3.9),0)
    box('ConcreteSupports',(x,2,3.71),(.30,4,.37),0)
for x in range(0,22):
    for y,z,r in ((.28,2.92,.13),(.27,3.43,.09)):
        # Precise continuation pipes remain continuous; generated valves sit in bays.
        tube('ServicePipes',[(x,y,z),(x+1,y,z)],r,2,16)
        if x%3==0:
            tube('ServicePipes',[(x+.1,y,z),(x+.15,y,z)],r*1.3,3,16)
    for y in (1.1,3.35):
        box('CableTrays',(x+.5,y,3.48),(1,.035,.12),3)
        box('CableTrays',(x+.5,y+.35,3.48),(1,.035,.12),3)
        for i in range(5):box('CableTrays',(x+i*.2,y+.175,3.43),(.026,.37,.025),3)
for lane in range(5):
    pts=[(i*.5,1.18+lane*.043+math.sin(i*.36+lane)*.012,3.42-math.sin(i*.31+lane)*.028) for i in range(45)]
    tube('CableTrays',pts,.013,3,8)
for x,y in [(4.7,.30),(13.2,3.4),(20.5,1.0)]:
    tube('HangingCables',[(x,y,3.5),(x+.15,y+.12,3.35),(x+.36,y+.18,2.95),(x+.65,y+.11,2.85),(x+.91,y,3.47)],.018,3,8)

# Service bay grille: closed sightline to machinery, with a visibly offset gate.
for x in (8.32,10.6,12.68):box('MachineGrille',(x,3.91,1.50),(.07,.10,3.0),3)
for z in (.10,1.0,2.05,2.94):box('MachineGrille',(10.5,3.91,z),(4.4,.09,.05),3)
for i in range(35):box('MachineGrille',(8.36+i*.125,3.94,1.5),(.008,.012,2.82),3)
for j in range(21):box('MachineGrille',(10.5,3.95,.17+j*.131),(4.24,.011,.008),3)
box('MachineGrille',(10.72,3.82,1.3),(.055,.09,.25),2)

# Continuous inset drain, with small missing grate strips near the breach only.
for x in range(22):
    for y in (.72,3.52):
        box('Drains',(x+.5,y,-.018),(1,.20,.07),3)
        for i in range(12):
            if 17<x<20 and i%7==0:continue
            box('Drains',(x+i/12+.04,y,.004),(.022,.21,.018),3)
for x,y,r in [(3,.75,.55),(10.9,3.45,.43),(18.1,3.3,.72),(5.7,-1,.30)]:
    pts=[]
    for i in range(26):
        a=i*math.tau/26;rr=r*(1+.14*math.sin(i*1.73)+.08*math.cos(i*.7))
        pts.append((x+rr*1.8*math.cos(a),y+rr*.48*math.sin(a),.009))
    poly('WetPatches',pts,[tuple(range(26))],5)

# End turn rises by one metre via two short runs and a broad intermediate landing.
for i in range(5):box('EndStairs',(24,8.1+i*.36,.10+i*.20),(2.05,.36,.20),0)
box('EndStairs',(24,10.0,.91),(2.1,.70,.18),0)
for x in (22.96,25.04):
    tube('EndStairRails',[(x,7.95,1.0),(x,9.9,2.0),(x,10.3,2.0)],.027,2,10)
    for y,z in ((8,0),(8.9,.5),(9.8,1)):tube('EndStairRails',[(x,y,z),(x,y,z+1)],.024,2,10)
# Raised terminus platform continues to a warm closed service door, without a drop.
box('EndStairs',(24,12.0,.47),(3.7,4,.94),0)
box('ServiceDoor',(24,13.86,2.15),(1.32,.10,2.28),2)
for x in (23.28,24.72):box('ServiceDoor',(x,13.84,2.13),(.12,.20,2.40),3)
box('ServiceDoor',(24,13.84,3.35),(1.55,.20,.13),3)

# Ancient arch is within a SIDE alcove. Individual stones break both silhouette
# and mortar rhythm; it is visible obliquely through the breach from the corridor.
for side in (-1,1):
    for row in range(6):
        box('AncientArch',(18.25+side*1.53+R.uniform(-.04,.04),9.62,row*.39+.2),(.60,.77,.38),4,rz=R.uniform(-.025,.025))
for i in range(13):
    a=(i+.5)*math.pi/13
    x,z=18.25+1.54*math.cos(a),2.34+1.54*math.sin(a)
    # Actual wedge voussoirs rather than a row of unrotated boxes.
    da=math.pi/13*.48
    points=[(18.25+r*math.cos(aa),2.34+r*math.sin(aa)) for r,aa in [(1.22,a-da),(1.87,a-da),(1.87,a+da),(1.22,a+da)]]
    xz_prism('AncientArch',points,9.62,.77,4)
for z,size in [(.12,(2,1.7,.24)),(.34,(1.70,1.40,.20)),(.68,(1.3,1.1,.48))]:box('AncientPlinth',(18.25,9.4,z),size,4)

# Purposeful service light fixtures. Light actors are authored separately in UE.
lights=[]
for name,x,y,z,warm in [('Entry',1.3,2,3.5,False),('Workshop',6.0,-1.8,2.85,True),
    ('Corridor',8.4,2.0,3.45,False),('MachineBay',10.7,6.6,3.55,False),
    ('Recess',15.2,-1.35,2.7,True),('Breach',17.1,3.1,3.45,True),
    ('Ruin',18.5,9.2,4.0,True),('Turn',23.8,5.2,3.78,False),('Exit',24,13.5,3.8,True)]:
    box('LightFixtures',(x,y,z),(.92,.22,.10),3)
    box('LightFixtures',(x,y,z-.064),(.78,.15,.028),6 if warm else 7)
    for i in range(5):box('LightFixtures',(x-.35+i*.175,y,z-.085),(.012,.18,.022),3)
    lights.append({'id':name,'location_cm':[x*100,y*100,(z-.20)*100],'warm':warm})

objects=[]
for name,g in groups.items():
    data=bpy.data.meshes.new('SM_V2_'+name);data.from_pydata(g['v'],[],g['f']);data.update()
    obj=bpy.data.objects.new('SM_V2_'+name,data);scene.collection.objects.link(obj)
    for m in MATS:data.materials.append(m)
    uv=data.uv_layers.new(name='UVMap')
    for face,mi in zip(data.polygons,g['m']):
        face.material_index=mi
        n=face.normal;axis=max(range(3),key=lambda i:abs(n[i]));dims=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            co=data.vertices[data.loops[li].vertex_index].co
            uv.data[li].uv=(co[dims[0]]/2,co[dims[1]]/2)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if name not in ('WetPatches','MachineGrille','CableTrays','HangingCables','Drains'):
        mod=obj.modifiers.new('Small manufactured edge bevel','BEVEL');mod.width=.004 if 'Tiles' in name else .010
        mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.65
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # Keep planar faces hard. Curved tube faces alone can carry smooth normals later.
    for f in obj.data.polygons:f.use_smooth=False
    if name in ('ServicePipes','HangingCables','EndStairRails','CableTrays','Breach_Rebar'):
        for f in obj.data.polygons:f.use_smooth=True
        obj.data.set_sharp_from_angle(angle=math.radians(50))
    triangulate=obj.modifiers.new('Export surface tangents','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    objects.append(obj);obj.select_set(False)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonAtmosphereV2_Structure.blend'))
manifest=[]
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    manifest.append({'name':obj.name,'fbx':str(path),'materials':MAT_NAMES,'placement':'authored coordinates, actor at origin'})
(OUT/'structure-manifest.json').write_text(json.dumps({'objects':manifest,'lights':lights,'regions':regions,
    'player_start_cm':[140,205,102],'event_anchor_cm':[1825,940,92], 'tests_run':False},indent=2),encoding='utf-8')
print('V2_STRUCTURE_AUTHORED',len(objects),'mesh assets; no render or tests')
