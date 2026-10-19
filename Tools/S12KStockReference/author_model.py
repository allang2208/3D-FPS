"""Reference-led cosmetic stock for the existing virtual S12K.

Only visible game surfaces are authored, in the gun's existing art frame.
The reference's grip is represented by the game's separate fitted rear grip.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME'); O=P/'SourceAssets/S12KStockReference20261018'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=.01
# Match the already installed private WeaponSurface instances, without grain.
specs={'Polymer':((.019,.019,.018),0.,.49),'Steel':((.034,.035,.037),1.,.38),
       'Rubber':((.009,.010,.011),0.,.66),'Inset':((.012,.014,.016),0.,.54)}
mats={}; parts=[]
for name,(color,metal,rough) in specs.items():
    m=bpy.data.materials.new('Saiga12K_Stock_'+name);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*color,1)
    s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough;mats[name]=m

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def smooth(ob,bevel=0):
    select(ob)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for f in ob.data.polygons:f.use_smooth=True
    if bevel:
        m=ob.modifiers.new('Soft manufactured edges','BEVEL');m.width=bevel;m.segments=4
        m.limit_method='ANGLE';m.angle_limit=math.radians(28);bpy.ops.object.modifier_apply(modifier=m.name)
    m=ob.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50
    bpy.ops.object.modifier_apply(modifier=m.name)
    return ob
def mesh(name,verts,faces,mat,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata([(float(x),-float(y),float(z)) for x,y,z in verts],[],faces);me.update()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(mats[mat]);parts.append(ob)
    return smooth(ob,bevel)
def slab(name,yz,x0,x1,mat,bevel=.06):
    n=len(yz);v=[(x,y,z) for x in (x0,x1) for y,z in yz]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,v,f,mat,bevel)
def box(name,c,size,mat,bevel=.06):
    x,y,z=c;sx,sy,sz=np.array(size)/2
    return slab(name,[(y-sy,z-sz),(y+sy,z-sz),(y+sy,z+sz),(y-sy,z+sz)],x-sx,x+sx,mat,bevel)
def rounded(y0,y1,z0,z1,r,n=8):
    out=[]
    for cy,cz,a in ((y1-r,z1-r,0),(y0+r,z1-r,90),(y0+r,z0+r,180),(y1-r,z0+r,270)):
        for j in range(n+1):
            q=math.radians(a+90*j/n);out.append((cy+r*math.cos(q),cz+r*math.sin(q)))
    return out
def bore(target,cutter):
    select(target);m=target.modifiers.new('Closed slot walls','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
    bpy.ops.object.modifier_apply(modifier=m.name);parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
def cylinder(name,c,r,length,axis,mat,n=48,bevel=.025):
    c=np.array(c,float);a=np.zeros(3);a[axis]=1;b=np.zeros(3);b[(axis+1)%3]=1;d=np.cross(a,b)
    v=[c+a*t+(b*math.cos(2*math.pi*i/n)+d*math.sin(2*math.pi*i/n))*r for t in (-length/2,length/2) for i in range(n)]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,v,f,mat,bevel)
def bar(name,a,b,width,thick,mat,bevel=.06):
    a=np.array(a);b=np.array(b);delta=b-a;side=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)*width/2
    return slab(name,[a+side,b+side,b-side,a-side],.08-thick/2,.08+thick/2,mat,bevel)
def frame(name,outer,inner,x0,x1,mat,bevel):
    n=len(outer);v=[(x,y,z) for x in (x0,x1) for loop in (outer,inner) for y,z in loop];f=[]
    for i in range(n):
        j=(i+1)%n
        f += [(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),
              (i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)]
    return mesh(name,v,f,mat,bevel)

# Preserve the actual front neck surfaces and close the cut with a short loft.
g=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text())
ff=[f for f,s in zip(g['triangles'],g['parts']) if s=='Stock'];ids=sorted({i for f in ff for i in f});lookup={i:n for n,i in enumerate(ids)}
neck=mesh('Original fitted front neck',np.array(g['positions'])[ids],[[lookup[i] for i in f] for f in ff],'Polymer')
bm=bmesh.new();bm.from_mesh(neck.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,11.8,0),plane_no=(0,1,0),clear_outer=True,dist=.00001)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-11.8)<.0001 for v in e.verts)];adj={}
for e in edges:
    for a,b in ((e.verts[0],e.verts[1]),(e.verts[1],e.verts[0])):adj.setdefault(a,[]).append(b)
start=next(iter(adj));ring=[start];prev=None;cur=start
while True:
    nxt=next(x for x in adj[cur] if x!=prev)
    if nxt==start:break
    ring.append(nxt);prev,cur=cur,nxt
    if len(ring)>len(adj):raise RuntimeError('Neck boundary could not be followed')
xmid=(min(v.co.x for v in ring)+max(v.co.x for v in ring))/2
zmid=(min(v.co.z for v in ring)+max(v.co.z for v in ring))/2
hw=(max(v.co.x for v in ring)-min(v.co.x for v in ring))/2;hh=(max(v.co.z for v in ring)-min(v.co.z for v in ring))/2
base=[((v.co.x-xmid)/hw,(v.co.z-zmid)/hh) for v in ring];last=ring
for y,w,z,h in ((12.2,1.04,2.1,1.82),(13.,1.05,2.45,1.56),(13.8,1.05,2.7,1.34)):
    new=[bm.verts.new((xmid+a*w,y,z+b*h)) for a,b in base]
    for i in range(len(last)):
        j=(i+1)%len(last);bm.faces.new((last[i],last[j],new[j],new[i]))
    last=new
bm.faces.new(last);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free();smooth(neck)

# Horizontal upper silhouette and upright collar from the supplied reference.
collar=slab('Upright front collar',rounded(-14.7,-12.9,1.0,5.3,.30),-1.18,1.34,'Polymer',.10)
cylinder('Horizontal dark upper tube',(.08,-21.8,3.64),.85,15.6,1,'Steel',64,.055)
for y,r,l in ((-15.0,.98,.24),(-16.05,.89,.15),(-19.5,.94,.30)):
    cylinder('Visible tube collar '+str(y),(.08,y,3.64),r,l,1,'Polymer',64,.04)
box('Continuous lower joining spine',(.08,-17.0,1.05),(1.45,8.1,.70),'Polymer',.12)

# The long horizontal windows are real closed-sided apertures, not dark decals.
cheek=slab('Slotted cheek housing',rounded(-30.0,-20.0,.82,4.60,.28),-1.43,1.59,'Polymer',0)
for row,z in enumerate((1.58,2.35,3.12)):
    for col,(y0,y1) in enumerate(((-29.14,-25.20),(-24.53,-20.88))):
        cut=slab('Window cutter',rounded(y0,y1,z-.205,z+.205,.19),-2.1,2.3,'Inset',0)
        bore(cheek,cut)
smooth(cheek,.065)
slab('Soft upper cheek ridge',rounded(-29.74,-20.17,4.39,4.74,.16),-1.40,1.56,'Rubber',.055)

# Open triangular skeleton with solid inner walls and a slim secondary strut.
frame('Triangular lower skeleton',[(-20.28,1.12),(-30.0,1.12),(-30.0,-5.02)],
      [(-22.65,.39),(-29.22,.39),(-29.22,-3.78)],-.58,.74,'Polymer',.095)
bar('Inset diagonal brace',(-29.62,-4.16),(-26.26,.62),.39,.80,'Steel',.065)
box('Rear frame spine',(.08,-29.75,-.04),(1.46,.71,9.45),'Polymer',.14)
slab('Thin pad backing',rounded(-30.43,-29.95,-5.02,4.76,.24),-1.00,1.16,'Steel',.07)
slab('Contoured rubber buttpad',rounded(-30.99,-30.24,-5.13,4.86,.28),-1.14,1.30,'Rubber',.105)
for i in range(18):
    z=-4.63+i*.525
    box('Rubber transverse tread '+str(i),(.08,-30.98,z),(2.18,.12,.125),'Rubber',.035)

# Sparse physical detailing; keep the reference's black/graphite appearance.
for side in (-1,1):
    x=.08+side*1.28
    for j,z in enumerate((2.03,4.27)):
        cylinder('Front fastener rim '+str(side)+str(j),(x,-13.80,z),.285,.11,0,'Steel')
        cylinder('Recessed fastener '+str(side)+str(j),(x+side*.058,-13.80,z),.145,.019,0,'Inset',6,.008)
    for y,z in ((-20.39,4.04),(-29.59,4.04),(-29.67,-3.89)):
        xx=.08+side*(1.54 if z>0 else .78)
        cylinder('Housing fastener '+str(side)+str(y),(xx,y,z),.14,.075,0,'Steel',32,.018)
        cylinder('Fastener socket '+str(side)+str(y),(xx+side*.043,y,z),.062,.014,0,'Inset',6,.006)
    # Narrow recessed borders describe the molding without speckled roughness.
    xx=.08+side*1.513
    for z in (1.08,3.62):
        box('Housing molded seam '+str(side)+str(z),(xx,-25.02,z),(.022,8.25,.045),'Inset',.01)
    barob=bar('Diagonal frame inner relief '+str(side),(-22.42,.01),(-29.30,-4.41),.075,.025,'Inset',.015)
    barob.location.x=side*.665
    cylinder('Small spine molding boss '+str(side),(.08+side*.78,-19.31,1.01),.27,.13,0,'Polymer',40,.04)
    cylinder('Spine boss recess '+str(side),(.08+side*.85,-19.31,1.01),.10,.016,0,'Inset',32,.015)

# Final source retains every editable piece. Runtime is one mesh, four slots.
for ob in parts:
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    smooth(ob)
archive=bpy.data.collections.new('Editable reference stock components');scene.collection.children.link(archive)
for ob in parts:
    cp=ob.copy();cp.data=ob.data.copy();archive.objects.link(cp);cp.hide_render=True;cp.hide_set(True)
select(parts[0])
for ob in parts:ob.select_set(True)
bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_Saiga12K_SpecialStock';me=ob.data
tri=ob.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0001);bmesh.ops.triangulate(bm,faces=list(bm.faces))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();smooth(ob)
while me.uv_layers:me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name='UV0');select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.003,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT');me.uv_layers.new(name='UV1')
for a,b in zip(me.uv_layers['UV0'].data,me.uv_layers['UV1'].data):b.uv=a.uv
data={'positions':[[float(v.co.x),-float(v.co.y),float(v.co.z)] for v in me.vertices],
      'triangles':[],'normals':[],'uv0':[],'uv1':[],'parts':[],
      'slot_names':[m.name.removeprefix('Saiga12K_Stock_') for m in me.materials],
      'ue_clockwise':True,'socket':'WPN_root','scale':.01}
uvarea=area=0.
for f in me.polygons:
    ids=list(f.loop_indices);data['triangles'].append([me.loops[i].vertex_index for i in ids]);data['parts'].append(f.material_index)
    data['normals'].append([[float(me.corner_normals[i].vector.x),-float(me.corner_normals[i].vector.y),float(me.corner_normals[i].vector.z)] for i in ids])
    for ch in (0,1):data['uv'+str(ch)].append([[float(me.uv_layers[ch].data[i].uv.x),1-float(me.uv_layers[ch].data[i].uv.y)] for i in ids])
    a,b,c=np.array(data['uv0'][-1]);uvarea+=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2;area+=f.area
data['uv_per_cm']=float(math.sqrt(uvarea/area))
(O/'Authoring/stock.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8');me.uv_layers.active_index=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_SpecialStock_Editable.blend'),compress=True)
select(ob);bpy.ops.export_scene.fbx(filepath=str(O/'Authoring/SM_Saiga12K_SpecialStock.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
recipe={'display_name':'S12K撞火枪托','id':'saiga12k_bump_stock','tier':'Special',
        'reference':'Reference/user-stock.png','socket':'WPN_root','runtime_scale':.01,
        'geometry':'Horizontal tube, six solid-sided cheek apertures, triangular open brace, narrow buttpad; game exterior only',
        'preserves_reargrip_slot':True,'preserves_native_neck':True,'hidden_side':'Inferred symmetric exterior',
        'triangles':len(me.polygons),'vertices':len(me.vertices),'materials':data['slot_names'],
        'game_stats':{'fire_interval_mult':.8,'hip_spread_mult':.75,'recoil_mult':1.1},'runtime_tested':False}
(O/'Authoring/recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf8')
print('S12K_REFERENCE_STOCK_AUTHORED',len(me.polygons),len(me.vertices),flush=True)
