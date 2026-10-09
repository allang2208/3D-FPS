"""Restore a connected shirt surface and paint continuous shoulder weights."""
from pathlib import Path
source=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=source.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V06'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V05/Authoring/FacelessSecurity_V05.blend'")
exec(compile(prefix,'security_v06_helpers','exec'))
report={'source':'V05 with V04 continuous shirt surface','removed':[],'rebuilt':[], 'game_tested':False,'rendered':False}
for o in list(scene.objects):
    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)
for o in list(scene.objects):
    if o.type=='MESH' and o.name.startswith(('Security_Shirt_Torso','Security_Sleeve_', 'Security_Belt','Security_DutyBelt','Security_Buckle','Security_CuffButton')):
        report['removed'].append(o.name);bpy.data.objects.remove(o,do_unlink=True)

# Use the original connected body-derived shirt, not two overlapping caps.
# Only its surface is reused; the V04 weights are discarded in full.
with bpy.data.libraries.load(str(BASE/'V04/Authoring/FacelessSecurity_V04.blend'),link=False) as (src,dst):
    dst.objects=['Security_Shirt_Continuous']
shirt=dst.objects[0];bpy.context.collection.objects.link(shirt);unbind(shirt)
shirt.name='Security_Shirt_Continuous_V06'
shirt.data.materials.clear();shirt.data.materials.append(bpy.data.materials['Security_Uniform'])
arm_source=source[source.index('def arm_weights('):source.index('\ndef make(',source.index('def arm_weights('))]
exec(compile(arm_source,'arm_weights','exec'))

# Solve arm/torso membership over mesh edges. Spatially close forearm and
# waist vertices must not exchange weights across their separate surfaces.
points=np.array([tuple(v.co) for v in shirt.data.vertices]);edges=np.array([tuple(e.vertices) for e in shirt.data.edges])
aa,bb=edges[:,0],edges[:,1];count=np.bincount(np.r_[aa,bb],minlength=len(points))[:,None]
field=np.zeros((len(points),3));fixed=np.zeros(len(points),dtype=bool)
for v in shirt.data.vertices:
    p=v.co;side='l' if p.x>=0 else 'r';s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
    q=(p-s).dot((e-s).normalized());ax=abs(p.x)
    is_arm=ax>.305 or (q>.12 and ax>.245) or (p.z<1.16 and ax>.27)
    is_torso=ax<.135 or (p.z<1.29 and ax<.215)
    t=ease(.19,.31,ax)
    field[v.index]=[1-t,t if side=='l' else 0,t if side=='r' else 0]
    if is_arm:field[v.index]=[0,1 if side=='l' else 0,1 if side=='r' else 0];fixed[v.index]=True
    elif is_torso:field[v.index]=[1,0,0];fixed[v.index]=True
anchors=field.copy()
for _ in range(320):
    total=np.zeros_like(field);np.add.at(total,aa,field[bb]);np.add.at(total,bb,field[aa])
    field=.2*field+.8*total/np.maximum(count,1);field[fixed]=anchors[fixed]
rows=[]
for v,amounts in zip(shirt.data.vertices,field):
    ws={}
    for amount,weights in zip(amounts,[torso_weights(v.co),arm_weights(v.co,'l'),arm_weights(v.co,'r')]):
        for name,value in weights.items():ws[name]=ws.get(name,0)+float(amount)*value
    rows.append(norm(ws))
put_weights(shirt,rows)
shirt_surface=surface(shirt);pants=bpy.data.objects['Security_Trousers_Continuous']
pants_surface=surface(pants);pants_rows=read_weights(pants)
parents={shirt.name:(shirt,shirt_surface,rows),pants.name:(pants,pants_surface,pants_rows)}
for side in ['l','r']:
    cuff=bpy.data.objects['Security_Cuff_'+side]
    parents[cuff.name]=(cuff,surface(cuff),read_weights(cuff))

def outside_normal(hit,point):
    # Attachment surfaces have a thin inner shell. Keep the outward side.
    n=hit[1].copy();delta=point-hit[0]
    if n.dot(delta)<0:n.negate()
    return n

# Remove old offsets instead of carrying forward a misplaced decoration.
# Every remaining panel or piece of hardware is attached to the new shirt
# or trousers. Small metal parts get one common anchor transform.
attachments=[]
for o in list(scene.objects):
    if o.type!='MESH' or o in [body,display] or o.name.startswith('Security_Boot') or o.name in parents:continue
    if o.name.startswith(('Security_Trouser','Security_RearPocket')):parent=parents[pants.name]
    else:parent=parents[shirt.name]
    tree=parent[1][0]
    rigid=any(token in o.name for token in ['Button','Stud','IDPlate','IDLetters','TieClip'])
    if rigid:
        center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
        hit=tree.find_nearest(center);n=outside_normal(hit,center)
        # Place the back of the detail against the fabric, not its centre.
        extent=min((v.co-center).dot(n) for v in o.data.vertices)
        delta=hit[0]+n*(.0015-extent)-center
        for v in o.data.vertices:v.co+=delta
        weights=sample(hit[0],parent[1],parent[2]);weights_rows=[weights]*len(o.data.vertices)
    else:
        for v in o.data.vertices:
            hit=tree.find_nearest(v.co);v.co=hit[0]+outside_normal(hit,v.co)*.003
        weights_rows=[sample(v.co,parent[1],parent[2]) for v in o.data.vertices]
    put_weights(o,weights_rows);attachments.append(o.name)

def make(name,verts,faces,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=True
        for li in p.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co.x/.2,co.z/.2)
    return o

# One fitted belt band and one directly seated buckle. The side keepers,
# stale cuff buttons and small free-standing waist hardware are removed.
def beltpoint(theta,z,offset=.003):
    center=Vector((0,.020,z));direction=Vector((math.sin(theta),-math.cos(theta),0))
    hit=pants_surface[0].ray_cast(center,direction,.31)
    if hit[0] is None:raise RuntimeError('Trouser waist surface is missing')
    return hit[0]+direction*offset
N=128;v=[tuple(beltpoint(2*math.pi*i/N,float(z))) for z in np.linspace(1.109,1.151,6) for i in range(N)]
f=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(5) for i in range(N)]
belt=make('Security_DutyBelt_V06',v,f,bpy.data.materials['Security_Leather'])
put_weights(belt,[sample(v.co,pants_surface,pants_rows) for v in belt.data.vertices])
m=belt.modifiers.new('BeltThickness','SOLIDIFY');m.thickness=.003;m.offset=-1;apply(belt,m)
p=beltpoint(0,1.130,.006)
verts=[];faces=[]
for offset,size in [((0,0,.017),(.048,.004,.005)),((0,0,-.017),(.048,.004,.005)),((.0215,0,0),(.005,.004,.034)),((-.0215,0,0),(.005,.004,.034))]:
    c=p+Vector(offset);sx,sy,sz=[n*.5 for n in size];start=len(verts)
    verts.extend([tuple(c+Vector((x,y,z))) for x,y,z in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]])
    faces.extend([tuple(start+i for i in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
buckle=make('Security_Buckle_V06',verts,faces,bpy.data.materials['Security_Hardware'])
put_weights(buckle,[sample(p,pants_surface,pants_rows)]*len(buckle.data.vertices))
for o in list(scene.objects):
    if o.type=='MESH' and not o.name.startswith('Security_Boot'):bind(o,read_weights(o))
body.hide_set(True);body.hide_render=True;rig.animation_data_create()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V06.blend'))
report.update(rebuilt=[shirt.name,belt.name,buckle.name],reattached=attachments,
    shoulder_binding='Continuous body-derived surface; graph-connected torso/arm membership with fixed forearm/torso anchors; no independent sleeve cap',
    waist='No side keepers or dangling cuff buttons; one band fitted 3 mm above trouser surface, weights sampled from trousers')
(ROOT/'shoulder_rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V06')
exec(compile(export,'export_security_v06','exec'))
