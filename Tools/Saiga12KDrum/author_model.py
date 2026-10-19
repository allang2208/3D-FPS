"""Precision exterior model in Saiga root centimetres; drum faces muzzle +Y.

The original insertion neck is retained. Only the circular drum body and its
transition are new. Export uses the project's corrected UE clockwise contract.
"""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDrum20261018'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
C=np.array([.08,12.3,-12.6]);R=9.25;HALF=3.35
materials={}
specs={'Steel':((.034,.035,.037),1.,.38),'Face':((.042,.044,.046),1.,.34),'Gold':((.24,.155,.065),1.,.31),'Polymer':((.019,.019,.018),0.,.49),'Rubber':((.009,.010,.011),0.,.64),'Interior':((.004,.005,.006),0.,.76)}
for name,(color,metal,rough) in specs.items():
    m=bpy.data.materials.new('Saiga12K_Drum_'+name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;materials[name]=m
parts=[]
def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def finish(name,verts,faces,mat,bevel=0.,smooth=True):
    me=bpy.data.meshes.new(name);me.from_pydata([(float(x),-float(y),float(z)) for x,y,z in verts],[],faces);me.update()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(materials[mat]);select(ob)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=smooth
    if bevel:
        mod=ob.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(25)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    wn=ob.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=40;bpy.ops.object.modifier_apply(modifier=wn.name)
    parts.append(ob);return ob
def lathe(name,profile,mat,center=C,segments=192):
    # Closed revolved (axial Y, radial XZ) polygon, including cap/back surfaces.
    verts=[(center[0]+r*math.cos(2*math.pi*j/segments),center[1]+y,center[2]+r*math.sin(2*math.pi*j/segments)) for y,r in profile for j in range(segments)]
    faces=[]
    for i in range(len(profile)):
        ni=(i+1)%len(profile)
        for j in range(segments):k=(j+1)%segments;faces.append((i*segments+j,i*segments+k,ni*segments+k,ni*segments+j))
    return finish(name,verts,faces,mat)
def disk(name,r,y,depth,mat,center=C,segments=160,bevel=.035):
    verts=[(center[0]+r*math.cos(2*math.pi*j/segments),center[1]+yy,center[2]+r*math.sin(2*math.pi*j/segments)) for yy in (y-depth/2,y+depth/2) for j in range(segments)]
    faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))]+[(j,(j+1)%segments,(j+1)%segments+segments,j+segments) for j in range(segments)]
    return finish(name,verts,faces,mat,bevel)
def sector(name,r0,r1,a0,a1,y0,y1,mat,bevel=.035,steps=36):
    verts=[]
    for y in (y0,y1):
        for r in (r0,r1):
            for j in range(steps+1):
                a=a0+(a1-a0)*j/steps;verts.append((C[0]+r*math.cos(a),C[1]+y,C[2]+r*math.sin(a)))
    n=steps+1;faces=[]
    for j in range(steps):faces.extend([(j,j+1,n+j+1,n+j),(2*n+j,3*n+j,3*n+j+1,2*n+j+1),(j,2*n+j,2*n+j+1,j+1),(n+j,n+j+1,3*n+j+1,3*n+j)])
    faces.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)])
    return finish(name,verts,faces,mat,bevel)
def prism(name,xy,y0,y1,mat,bevel=.04):
    # Exterior relief extruded along Y from a closed XZ outline.
    verts=[(x,y,z) for y in (y0,y1) for x,z in xy];n=len(xy)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return finish(name,verts,faces,mat,bevel)
def box(name,center,size,mat,bevel=.07):
    x,y,z=center;sx,sy,sz=np.array(size)/2
    return prism(name,[(x-sx,z-sz),(x+sx,z-sz),(x+sx,z+sz),(x-sx,z+sz)],y-sy,y+sy,mat,bevel)

# Original currently-loaded magazine throat, cut below its insertion zone.
source=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text())
faces=[f for f,part in zip(source['triangles'],source['parts']) if part=='Magazine']
ids=sorted({i for f in faces for i in f});lookup={v:i for i,v in enumerate(ids)}
neck=finish('Factory insertion neck',np.asarray(source['positions'])[ids],[[lookup[i] for i in f] for f in faces],'Polymer')
bm=bmesh.new();bm.from_mesh(neck.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,-1.05),plane_no=(0,0,1),clear_inner=True,clear_outer=False,dist=.00001)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+1.05)<.0001 for v in e.verts)]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free()
# Continuous solid shell: no hollow seam, duplicate thin cap, or hidden holes.
lathe('Rolled cylindrical steel shell',[(-3.33,8.88),(-3.28,9.03),(-3.12,9.18),(-2.92,R),(2.92,R),(3.12,9.18),(3.28,9.03),(3.33,8.88),(3.33,.3),(-3.33,.3)],'Steel')
# Close the central bore through the underlying shell; it is not a real mechanism.
disk('Closed central support',.34,0,6.67,'Steel',segments=48,bevel=.02)
for sign,label in ((1,'Front'),(-1,'Rear')):
    disk(label+' closed face',8.83,sign*3.35,.18,'Steel',bevel=.065)
    lathe(label+' outer rolled border',[(sign*3.36,8.62),(sign*3.41,8.65),(sign*3.46,8.75),(sign*3.43,8.89),(sign*3.34,8.94),(sign*3.30,8.72)],'Steel')
    for i in range(4):
        a0=math.radians(7+i*90);a1=math.radians(83+i*90)
        y0,y1=sorted((sign*3.39,sign*3.50))
        sector(label+' recessed panel '+str(i),2.96,8.40,a0,a1,y0,y1,'Face',.045)
        y0,y1=sorted((sign*3.50,sign*3.53))
        sector(label+' gold inset '+str(i),7.50,7.65,a0+.07,a1-.07,y0,y1,'Gold',.014)
    disk(label+' inset medallion',2.69,sign*3.51,.18,'Face',bevel=.065)
    lathe(label+' medallion steel bezel',[(sign*3.49,2.72),(sign*3.62,2.75),(sign*3.64,2.83),(sign*3.54,2.91),(sign*3.46,2.86)],'Steel')
    lathe(label+' medallion gold hairline',[(sign*3.63,2.74),(sign*3.65,2.76),(sign*3.65,2.80),(sign*3.63,2.81)],'Gold')
    # Small embossed geometric mark, sealed against the medallion.
    glyph=[(-.15,1.32),(-.94,-.18),(-.23,-.11),(-.48,-1.38),(.93,.36),(.20,.28)]
    poly=[(C[0]+x,C[2]+z) for x,z in glyph];a,b=sorted((C[1]+sign*3.60,C[1]+sign*3.63));prism(label+' lightning relief',poly,a,b,'Gold',.012)
    for i in range(4):
        a=math.radians(i*90);center=C+np.array([7.85*math.cos(a),0,7.85*math.sin(a)])
        disk(label+' screw recess '+str(i),.32,sign*3.50,.05,'Interior',center,48,.018)
        disk(label+' screw head '+str(i),.23,sign*3.54,.05,'Steel',center,48,.025)
        disk(label+' hex drive '+str(i),.09,sign*3.575,.009,'Interior',center,6,.005)
    # Fine perimeter index notches are short, shallow relief rather than noise.
    for i in range(32):
        a=2*math.pi*i/32;aa=a-.006;bb=a+.006;lo,hi=sorted((sign*3.45,sign*3.47))
        sector(label+' engraved index '+str(i),8.47,8.56,aa,bb,lo,hi,'Interior',0.,2)

# Rounded circumferential armor pads leave the neck crown unobstructed.
for i in range(12):
    mid=math.radians(i*30)
    if i==3:continue
    sector('Molded perimeter pad '+str(i),9.18,9.68,mid-math.radians(9),mid+math.radians(9),-3.10,3.10,'Rubber',.115,14)
for y in (-2.03,2.03):
    lathe('Inset axial trim '+str(y),[(y-.045,9.245),(y-.045,9.275),(y+.045,9.275),(y+.045,9.245)],'Gold')
    lathe('Rubber seal '+str(y),[(y-.14,9.22),(y-.14,9.255),(y-.10,9.255),(y-.10,9.22)],'Interior')

# A flared collar connects the retained neck to the crown of the forward drum.
prism('Continuous flared transition',[(.08-1.48,-.90),(.08+1.48,-.90),(.08+2.48,-4.24),(.08-2.48,-4.24)],9.00,15.55,'Polymer',.16)
box('Neck collar front',(C[0],15.53,-1.58),(3.35,.36,.58),'Steel',.07)
box('Neck collar rear',(C[0],9.10,-1.58),(3.35,.36,.58),'Steel',.07)
for side in (-1,1):
    box('Neck shoulder '+str(side),(C[0]+side*1.64,12.3,-2.38),(.48,5.75,1.38),'Steel',.10)
    for i in range(3):box('Collar grip rib '+str(side)+' '+str(i),(C[0]+side*1.925,10.85+i*1.43,-2.45),(.065,.66,.56),'Polymer',.024)
box('Lower contact pad',(C[0],C[1],C[2]-9.37),(4.4,5.5,.40),'Rubber',.18)

# Maintain a non-rendered editable component collection as the modelling source.
archive=bpy.data.collections.new('Editable construction components');scene.collection.children.link(archive)
for ob in parts:
    cp=ob.copy();cp.data=ob.data.copy();archive.objects.link(cp);cp.hide_render=True;cp.hide_set(True)
select(parts[0])
for ob in parts:ob.select_set(True)
bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_Saiga12K_Drum20';me=ob.data
tri=ob.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
while me.uv_layers:me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name='UV0');select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.0025,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers.new(name='UV1')
for a,b in zip(me.uv_layers['UV0'].data,me.uv_layers['UV1'].data):b.uv=a.uv
# The exact native socket transform from the current rig, not a bounding box.
def matrix(v):return np.array(Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],v[3],v[4],v[5])),Vector(v[7:10])))
def world(local,parents):
    result={}
    def resolve(n):
        if n not in result:result[n]=resolve(parents[n])@local[n] if parents[n] else local[n]
        return result[n]
    for n in local:resolve(n)
    return result
native=json.loads((P/'SourceAssets/Saiga12KInspect20261018/Inputs/runtime-source.json').read_text());names=[b['name'] for b in native['bones']];parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in native['bones']}
pose=world({n:matrix(v) for n,v in native['idle'].items()},parents)
socket=np.linalg.inv(pose['WPN_SOCKET_Magazine'])@pose['WPN_root'];socket[:3,3]*=100
data={'positions':[],'root_positions':[],'triangles':[],'normals':[],'uv0':[],'uv1':[],'parts':[],'slot_names':[m.name.removeprefix('Saiga12K_Drum_') for m in me.materials],'ue_clockwise':True,'socket':'WPN_SOCKET_Magazine','scale':.01,'socket_from_root_cm':socket.tolist()}
for v in me.vertices:
    p=np.array([v.co.x,-v.co.y,v.co.z]);data['root_positions'].append(p.tolist());data['positions'].append((socket@np.r_[p,1])[:3].tolist())
uvarea=area=0.
for f in me.polygons:
    ids=list(f.loop_indices);data['triangles'].append([me.loops[i].vertex_index for i in ids]);data['parts'].append(f.material_index)
    data['normals'].append([(socket[:3,:3]@np.array([me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z])).tolist() for i in ids])
    for ch in (0,1):data['uv'+str(ch)].append([[float(me.uv_layers[ch].data[i].uv.x),1-float(me.uv_layers[ch].data[i].uv.y)] for i in ids])
    a,b,c=np.array(data['uv0'][-1]);uvarea+=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2;area+=f.area
data['uv_per_cm']=float(math.sqrt(uvarea/area))
if not np.isfinite(np.asarray(data['positions'])).all():raise RuntimeError('Invalid export coordinates')
(O/'Authoring/drum.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
recipe={'name':'12k 大弹鼓','capacity':20,'axis_root':[0,1,0],'front_face':'muzzle +Y','body_center_root_cm':C.tolist(),'body_radius_cm':R,'body_half_depth_cm':HALF,'shell_outer_radius_cm':9.68,'neck_source':'Saiga12K Closure20261018 Magazine; retained above root Z=-1.05 cm','source_triangles':len(me.polygons),'material_slots':data['slot_names'],'runtime_scale':.01,'socket':'WPN_SOCKET_Magazine','runtime_tested':False}
(O/'Authoring/recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
me.uv_layers.active_index=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_Drum20_Editable.blend'),compress=True)
print('SAIGA_DRUM_MODEL_AUTHORED',len(me.polygons),len(me.vertices),flush=True)
