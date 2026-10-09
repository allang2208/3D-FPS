"""Make an explicitly sewn shirt with armholes above the lower upper arm.

The old scan-derived side web and its abrupt arm/torso boundaries are removed.
"""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=src.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V08'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V07/Authoring/FacelessSecurity_V07.blend'")
exec(compile(prefix,'armhole_helpers','exec'))
arm_source=src[src.index('def arm_weights('):src.index('\ndef make(',src.index('def arm_weights('))]
exec(compile(arm_source,'arm_weights','exec'))
exclude=('Security_Boot','Security_DutyBelt','Security_Buckle','Security_Cuff_','Security_Trouser','Security_RearPocket')
upper=[o for o in scene.objects if o.type=='MESH' and o not in [body,display] and not o.name.startswith(exclude)]
for o in upper:unbind(o)
old=bpy.data.objects['Security_Shirt_Continuous_V06'];upper.remove(old);bpy.data.objects.remove(old,do_unlink=True)
uniform=bpy.data.materials['Security_Uniform']
N=96;HALF_I=6
zs=np.unique(np.r_[np.linspace(1.110,1.390,25),np.linspace(1.390,1.600,25),np.linspace(1.600,1.645,7)])
LOW=int(np.argmin(abs(zs-1.390)));HIGH=int(np.argmin(abs(zs-1.600)))
ZM=.5*(zs[LOW]+zs[HIGH]);ZH=.5*(zs[HIGH]-zs[LOW]);JH=.5*(HIGH-LOW)
holes=[('l',1,N//4),('r',-1,3*N//4)]
verts=[];uvs=[];rows=[];faces=[]

def torso_point(theta,z):
    center=Vector((0,.020,z));d=Vector((math.sin(theta),-math.cos(theta),0))
    rx=float(np.interp(z,[1.110,1.22,1.36,1.45,1.53,1.58,1.645],[.214,.210,.228,.238,.244,.213,.120]))
    limit=1/math.sqrt((d.x/rx)**2+(d.y/.180)**2)
    hit=body_tree.ray_cast(center,d,.37)
    radius=min((hit[0]-center).length,limit) if hit[0] is not None else limit
    return center+d*(radius+.017)

def add(point,weights,uv):
    verts.append(tuple(point));rows.append(weights);uvs.append(uv);return len(verts)-1

for j,z in enumerate(zs):
    for i in range(N):
        theta=2*math.pi*i/N;znew=float(z);field=None
        for side,sign,center_i in holes:
            u=sign*(i-center_i)/HALF_I;v=(float(z)-ZM)/ZH;rho=max(abs(u),abs(v))
            if rho<=1.9:
                # Turn a rectangular grid boundary into an oval and carry
                # that displacement smoothly into the surrounding torso.
                radius=math.hypot(u,v)
                factor=rho/radius if radius>1e-8 else 1.
                influence=1-ease(1.,1.9,rho)
                scale=1+influence*(factor-1)
                theta=2*math.pi*(center_i+sign*u*scale*HALF_I)/N
                znew=ZM+v*scale*ZH
                field=(side,rho,v*scale)
        point=torso_point(theta,znew);ws=torso_weights(point)
        if field:
            side,rho,v=field
            amount=(1-ease(1.,1.75,rho))*(.22+.15*ease(-1.,1.,v))
            ws=mix(ws,{'clavicle_'+side:1.},amount)
        add(point,ws,(theta*.21/.2,znew/.2))

for j in range(len(zs)-1):
    for i in range(N):
        in_hole=any(center-HALF_I<=i<center+HALF_I and LOW<=j<HIGH for _,_,center in holes)
        if not in_hole:faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))

seams={}
for side,sign,center in holes:
    seam=[]
    for j in range(LOW,HIGH+1):
        for i in range(center-HALF_I,center+HALF_I+1):
            if j not in [LOW,HIGH] and i not in [center-HALF_I,center+HALF_I]:continue
            u=sign*(i-center)/HALF_I;v=(j-.5*(LOW+HIGH))/JH
            angle=math.atan2(v,-u)%(2*math.pi);seam.append((angle,j*N+i))
    seam.sort();angles=[t for t,_ in seam];root_ids=[i for _,i in seam];K=len(root_ids)
    seams[side]={'shared_vertices':K,'bottom_z':float(zs[LOW]),'top_z':float(zs[HIGH])}
    s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
    upper_axis=(e-s).normalized();lower_axis=(w-e).normalized();l1=(e-s).length;l2=(w-e).length

    def sleeve_ring(q):
        center=s+upper_axis*q if q<=l1 else e+lower_axis*(q-l1)
        axis=upper_axis.lerp(lower_axis,ease(l1-.055,l1+.055,q)).normalized()
        front=Vector((0,-1,0));front=(front-axis*front.dot(axis)).normalized();around=sign*front.cross(axis).normalized()
        expected=float(np.interp(q,[.105,.15,l1,l1+l2],[.087,.083,.075,.054]))
        radii=[]
        for angle in angles:
            d=front*math.cos(angle)+around*math.sin(angle);hit=body_tree.ray_cast(center,d,.12)
            r=(hit[0]-center).length+.014 if hit[0] is not None else expected
            radii.append(max(expected*.90,min(expected*1.10,r)))
        radii=np.array(radii)
        for _ in range(3):radii=(np.roll(radii,1)+2*radii+np.roll(radii,-1))/4
        return [center+(front*math.cos(a)+around*math.sin(a))*float(r) for a,r in zip(angles,radii)]

    previous=root_ids;target=sleeve_ring(.105)
    # The sleeve cap is stitched to the SAME torso vertices. Twelve rings
    # distribute both curvature and root-to-upperarm attachment smoothly.
    for step in range(1,13):
        t=step/12;current=[]
        for angle,root_id,end in zip(angles,root_ids,target):
            start=Vector(verts[root_id]);cap=max(0.,math.sin(angle))
            point=start.lerp(end,t)+Vector((sign*.020,0,.012))*math.sin(math.pi*t)*cap
            ws=mix(rows[root_id],arm_weights(end,side),ease(0.,1.,t))
            current.append(add(point,ws,(angle*.082/.2,(.105*t)/.2)))
        for k in range(K):faces.append((previous[k],previous[(k+1)%K],current[(k+1)%K],current[k]))
        previous=current
    for q in np.linspace(.105,l1+l2-.018,43)[1:]:
        current=[]
        for angle,point in zip(angles,sleeve_ring(float(q))):
            current.append(add(point,arm_weights(point,side),(angle*.082/.2,float(q)/.2)))
        for k in range(K):faces.append((previous[k],previous[(k+1)%K],current[(k+1)%K],current[k]))
        previous=current

# Drop unused points inside the armholes, so no hidden faces or loose
# vertices survive the topology replacement.
used=sorted({i for face in faces for i in face});remap={old:new for new,old in enumerate(used)}
vertices=[verts[i] for i in used];weights=[rows[i] for i in used];texcoords=[uvs[i] for i in used]
me=bpy.data.meshes.new('Security_Shirt_Armholes_V08');me.from_pydata(vertices,[],[tuple(remap[i] for i in f) for f in faces]);me.update()
shirt=bpy.data.objects.new('Security_Shirt_Armholes_V08',me);bpy.context.collection.objects.link(shirt);me.materials.append(uniform)
bm=bmesh.new();bm.from_mesh(me)
shoulder_vertices=[v for v in bm.verts if 1.335<v.co.z<1.625 and abs(v.co.x)>.11]
for _ in range(4):bmesh.ops.smooth_vert(bm,verts=shoulder_vertices,factor=.22,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
uv=me.uv_layers.new(name='UVMap')
for face in me.polygons:
    face.use_smooth=True
    for li in face.loop_indices:uv.data[li].uv=texcoords[me.loops[li].vertex_index]
put_weights(shirt,weights)
solid=shirt.modifiers.new('SewnClothThickness','SOLIDIFY');solid.thickness=.0026;solid.offset=-1;apply(shirt,solid)
new_surface=surface(shirt);new_weights=read_weights(shirt);attachments=[]

for o in upper:
    rigid=any(token in o.name for token in ['Button','Stud','IDPlate','IDLetters','TieClip'])
    if rigid:
        center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
        hit=new_surface[0].find_nearest(center);normal=hit[1].copy()
        if normal.dot(center-hit[0])<0:normal.negate()
        extent=min((v.co-center).dot(normal) for v in o.data.vertices)
        shift=hit[0]+normal*(.0015-extent)-center
        for v in o.data.vertices:v.co+=shift
        ws=sample(hit[0],new_surface,new_weights);target_rows=[ws]*len(o.data.vertices)
    else:
        for v in o.data.vertices:
            hit=new_surface[0].find_nearest(v.co);normal=hit[1].copy()
            if normal.dot(v.co-hit[0])<0:normal.negate()
            v.co=hit[0]+normal*.003
        target_rows=[sample(v.co,new_surface,new_weights) for v in o.data.vertices]
    bind(o,target_rows);attachments.append(o.name)
bind(shirt,new_weights);body.hide_set(True);body.hide_render=True;rig.animation_data_create()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V08.blend'))
report={'source':'V07','replaced':'Security_Shirt_Continuous_V06','new_shirt':shirt.name,'armholes':seams,
    'sleeve_cap_rings':12,'sleeve_longitudinal_rings':43,'shirt_vertices':len(shirt.data.vertices),
    'shirt_triangles':sum(len(f.vertices)-2 for f in shirt.data.polygons),'reattached':attachments,
    'binding':'Shared torso/sleeve seam vertices; gradual clavicle-to-upperarm cap weights; inner/outer layers inherit the same weights before thickness',
    'preserved':'V07 cleaned trousers, belt, cuffs, body, boots, V06 motions and current ground offset','game_tested':False,'rendered':False}
(ROOT/'armhole_rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_ARMHOLES_V08_AUTHORED '+json.dumps(report),flush=True)
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V08')
exec(compile(export,'export_security_v08','exec'))
