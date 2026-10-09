"""Build the uniform in the preserved native bind frame, not inverse fitted sleeve rings.

Complete body, deforming outer surface, thickness and decorations are distinct.
No preview rendering or gameplay acceptance is performed by this production recipe.
"""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/rebuild_arms_v05.py').read_text(encoding='utf-8')
prefix=src.split("for o in list(scene.objects):\n    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)")[0]
prefix=prefix.replace("ROOT=BASE/'V05'","ROOT=BASE/'V09'").replace("BASE/'V04/Authoring/FacelessSecurity_V04.blend'","BASE/'V08/Authoring/FacelessSecurity_V08.blend'")
exec(compile(prefix,'native_uniform_helpers','exec'))
HEAD={b.name:rig.matrix_world@b.head_local for b in rig.data.bones}
old_body_rows=read_weights(body)
report={'source':'V08','construction_frame':'unchanged native Nurse reference pose in metres',
        'game_tested':False,'rendered':False,'removed':[],'new_parts':[]}
native_targets={s:[HEAD[n+'_'+s] for n in ['upperarm','lowerarm','hand']] for s in ['l','r']}
spine_names=['pelvis']+['spine_%02d'%i for i in range(1,6)]+['neck_01','neck_02','head']

def core_weights(p):
    for a,b in zip(spine_names[:-1],spine_names[1:]):
        if p.z<=HEAD[b].z:
            return mix({a:1.},{b:1.},ease(HEAD[a].z,HEAD[b].z,p.z))
    return {'head':1.}

def limb_weights(p,side):
    s,e,w=native_targets[side];ua=(e-s).normalized();la=(w-e).normalized()
    elbow=ease(-.075,.075,(p-e).dot((w-s).normalized()))
    ws=mix({'upperarm_'+side:1.},{'lowerarm_'+side:1.},elbow)
    clav=.40*(1-ease(-.015,.115,(p-s).dot(ua)))
    ws=mix(ws,{'clavicle_'+side:1.},clav)
    return mix(ws,{'hand_'+side:1.},ease(-.035,.018,(p-w).dot(la)))

# Establish the complete-body native shoulder field first. UV duplicate
# vertices participate in the same diffusion field; arms and ribs are
# connected through actual skin edges, never through spatial waist neighbours.
p=np.array([v.co for v in body.data.vertices]);edges=np.array([e.vertices[:] for e in body.data.edges]);aa,bb=edges.T
field=np.zeros((len(p),3));fixed=np.ones(len(p),dtype=bool)
for i,v in enumerate(body.data.vertices):
    co=v.co;side='l' if co.x>=0 else 'r';s,e,w=native_targets[side];q=(co-s).dot((e-s).normalized())
    amount=ease(.115,.305,abs(co.x))
    if co.z<1.18:amount=1. if abs(co.x)>.34 else 0.
    field[i]=[1-amount,amount if side=='l' else 0,amount if side=='r' else 0]
    if 1.18<co.z<1.565 and .105<abs(co.x)<.345:
        fixed[i]=(abs(co.x)<.135) or (q>.150 and abs(co.x)>.280) or (co.z<1.27 and abs(co.x)<.215)
        if q>.150 and abs(co.x)>.280:field[i]=[0,1 if side=='l' else 0,1 if side=='r' else 0]
        elif fixed[i]:field[i]=[1,0,0]
anchors=field.copy();count=np.bincount(np.r_[aa,bb],minlength=len(p))
_,weld=np.unique(np.round(p,6),axis=0,return_inverse=True);wc=np.bincount(weld)
for iteration in range(280):
    averaged=np.column_stack([np.bincount(aa,weights=field[bb,c],minlength=len(p))+np.bincount(bb,weights=field[aa,c],minlength=len(p)) for c in range(3)])
    field=.25*field+.75*averaged/np.maximum(count[:,None],1)
    if iteration%4==0:
        field=np.column_stack([np.bincount(weld,weights=field[:,c])/wc for c in range(3)])[weld]
    field[fixed]=anchors[fixed]
body_rows=[]
for v,amounts,old in zip(body.data.vertices,field,old_body_rows):
    co=v.co;side='l' if co.x>=0 else 'r';s,e,w=native_targets[side];la=(w-e).normalized()
    if co.z<1.17 or co.z>1.565 or abs(co.x)>.49:
        body_rows.append(old);continue
    row={}
    for amount,ws in zip(amounts,[core_weights(co),limb_weights(co,'l'),limb_weights(co,'r')]):
        for n,value in ws.items():row[n]=row.get(n,0)+float(amount)*value
    row=norm(row)
    keep=ease(-.125,-.060,(co-w).dot(la)) if abs(co.x)>.31 else 0.
    body_rows.append(mix(row,old,keep))
put_weights(body,body_rows);body_surface=surface(body)

preserve=('Security_Boot','Security_DutyBelt','Security_Buckle','Security_Trouser','Security_RearPocket')
for o in list(scene.objects):
    if o.type=='MESH' and o not in [body,display] and not o.name.startswith(preserve):
        report['removed'].append(o.name);bpy.data.objects.remove(o,do_unlink=True)

def native_attach(o,rows):
    # Coordinates already ARE native reference positions: no inverse fit.
    put_weights(o,rows);o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=o.modifiers.new('NativeBodySkin','ARMATURE');mod.object=rig

def clean_normals(o):
    if o.data.has_custom_normals:
        o.data.normals_split_custom_set([(0.,0.,0.)]*len(o.data.loops))
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.data.update()
    for f in o.data.polygons:f.use_smooth=True

def make(name,vertices,faces,family='Uniform',uvs=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(bpy.data.materials['Security_'+family])
    clean_normals(o);layer=me.uv_layers.new(name='UVMap')
    for face in me.polygons:
        for li in face.loop_indices:
            vi=me.loops[li].vertex_index;co=me.vertices[vi].co
            layer.data[li].uv=uvs[vi] if uvs else (co.x/.2,co.z/.2)
    return o

def weight_from_body(point):
    ws=sample(point,body_surface,body_rows);out={}
    for n,w in ws.items():
        if n.startswith(('thumb','index','middle','ring','pinky')):n='hand_'+n[-1]
        out[n]=out.get(n,0)+w
    return norm(out)

# Closed construction volumes are fused in native rest space. The resulting
# outside surface has no separately capped upper arm, overlapping sleeve
# mouth, shoulder web, or inverse-LBS fold. Openings are cut AFTER fusion.
pieces=[];N=96;zs=np.linspace(1.020,1.570,76);vertices=[]
for z in zs:
    rx=float(np.interp(z,[1.020,1.12,1.27,1.37,1.43,1.48,1.53,1.57],[.222,.214,.230,.238,.219,.143,.083,.076]))
    ry=float(np.interp(z,[1.020,1.20,1.37,1.44,1.53,1.57],[.150,.165,.168,.153,.090,.080]))
    center=Vector((0,.017,float(z)));radii=[]
    for i in range(N):
        theta=2*math.pi*i/N;d=Vector((math.sin(theta),-math.cos(theta),0))
        expected=1/math.sqrt((d.x/rx)**2+(d.y/ry)**2)
        hit=body_surface[0].ray_cast(center,d,.35)
        measured=(hit[0]-center).length+.014 if hit[0] is not None else expected
        radii.append(max(expected*.91,min(expected*1.06,measured)))
    radii=np.array(radii)
    for _ in range(5):radii=(np.roll(radii,1)+2*radii+np.roll(radii,-1))/4
    for i,r in enumerate(radii):
        theta=2*math.pi*i/N;vertices.append((math.sin(theta)*r,.017-math.cos(theta)*r,float(z)))
faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(zs)-1) for i in range(N)]
faces.extend([tuple(reversed(range(N))),tuple((len(zs)-1)*N+i for i in range(N))])
pieces.append(make('UniformNativeVolume',vertices,faces))
for side,sign in [('l',1),('r',-1)]:
    s,e,w=native_targets[side];ua=(e-s).normalized();la=(w-e).normalized();l1=(e-s).length;l2=(w-e).length
    vertices=[];N=64;qs=np.linspace(-.10,l1+l2+.035,90)
    for q in qs:
        center=s+ua*q if q<=l1 else e+la*(q-l1);axis=ua.lerp(la,ease(l1-.075,l1+.075,q)).normalized()
        front=Vector((0,-1,0));front=(front-axis*front.dot(axis)).normalized();around=front.cross(axis).normalized()
        r=float(np.interp(q,[-.10,-.035,.04,.145,l1,l1+l2],[.030,.072,.101,.088,.073,.0545]))
        for i in range(N):
            t=2*math.pi*i/N;vertices.append(tuple(center+(front*math.cos(t)+around*math.sin(t))*r))
    faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(qs)-1) for i in range(N)]
    faces.extend([tuple(reversed(range(N))),tuple((len(qs)-1)*N+i for i in range(N))])
    pieces.append(make('SleeveNativeVolume_'+side,vertices,faces))
bpy.ops.object.select_all(action='DESELECT')
for o in pieces:o.select_set(True)
bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();shirt=bpy.context.object;shirt.name='Security_Uniform_Native_V09'
shirt.data.remesh_voxel_size=.0045;shirt.data.remesh_voxel_adaptivity=0.
bpy.ops.object.voxel_remesh()
smooth=shirt.modifiers.new('ContinuousShoulderFillet','SMOOTH');smooth.factor=.65;smooth.iterations=24;apply(shirt,smooth)

bm=bmesh.new();bm.from_mesh(shirt.data)
def cut(point,normal,inner=False,side=None,neck=False):
    if neck:
        vv=[v for v in bm.verts if abs(v.co.x)<.112 and abs(v.co.y-.017)<.119 and v.co.z>1.49];vs=set(vv)
        geom=vv+[e for e in bm.edges if all(v in vs for v in e.verts)]+[f for f in bm.faces if all(v in vs for v in f.verts)]
    elif side is None:geom=list(bm.verts)+list(bm.edges)+list(bm.faces)
    else:
        vv=[v for v in bm.verts if side*v.co.x>.44];vs=set(vv)
        geom=vv+[e for e in bm.edges if all(v in vs for v in e.verts)]+[f for f in bm.faces if all(v in vs for v in f.verts)]
    bmesh.ops.bisect_plane(bm,geom=geom,plane_co=point,plane_no=normal,dist=1e-7,clear_inner=inner,clear_outer=not inner)
cut(Vector((0,0,1.039)),Vector((0,0,1)),True)
cut(Vector((0,0,1.535)),Vector((0,0,1)),neck=True)
for side,sign in [('l',1),('r',-1)]:
    s,e,w=native_targets[side];la=(w-e).normalized();cut(w-la*.012,la,side=sign)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update()
source_outer=shirt.copy();source_outer.data=shirt.data.copy();source_outer.name='Security_Uniform_Native_DenseSource_V09'
high_collection=bpy.data.collections.new('V09_DenseSource_ExcludedFromDelivery');bpy.context.scene.collection.children.link(high_collection);high_collection.objects.link(source_outer)
source_outer.hide_render=True;source_outer.hide_set(True)
source_outer.use_fake_user=True;source_outer.data.use_fake_user=True
# Keep the dense construction as an unlinked authoring datablock. Exporters
# intentionally enumerate only scene meshes for the actual game assembly.
high_collection.objects.unlink(source_outer);bpy.data.collections.remove(high_collection)
outer_triangles=sum(len(f.vertices)-2 for f in shirt.data.polygons)
reduce=shirt.modifiers.new('UniformGameSurfaceDensity','DECIMATE');reduce.ratio=min(1.,36000/max(1,outer_triangles));reduce.use_collapse_triangulate=True;apply(shirt,reduce)
clean_normals(shirt)
if not shirt.data.uv_layers:shirt.data.uv_layers.new(name='UVMap')
uv=shirt.data.uv_layers.active
for f in shirt.data.polygons:
    center=f.center;side='l' if center.x>=0 else 'r';s,e,w=native_targets[side];axis=(w-s).normalized()
    arm=abs(center.x)>.27
    coords=[]
    for li in f.loop_indices:
        co=shirt.data.vertices[shirt.data.loops[li].vertex_index].co
        if arm:
            q=(co-s).dot(axis);front=Vector((0,-1,0));front=(front-axis*front.dot(axis)).normalized();around=front.cross(axis).normalized();d=co-s-axis*q
            coords.append((math.atan2(d.dot(around),d.dot(front))/(2*math.pi),q/.2))
        else:coords.append((math.atan2(co.x,-(co.y-.017))/(2*math.pi),co.z/.2))
    if max(x[0] for x in coords)-min(x[0] for x in coords)>.5:coords=[(x+(1 if x<0 else 0),y) for x,y in coords]
    for li,(x,y) in zip(f.loop_indices,coords):uv.data[li].uv=(x*(2*math.pi*(.076 if arm else .21))/.2,y)
shirt_rows=[weight_from_body(v.co) for v in shirt.data.vertices]
# Relax transferred weights only over the connected garment, keeping the
# forearm and centre torso anchors. This removes nearest-face discontinuities.
bone_names=sorted({n for ws in shirt_rows for n in ws});bn={n:i for i,n in enumerate(bone_names)}
wfield=np.zeros((len(shirt_rows),len(bone_names)))
for i,ws in enumerate(shirt_rows):
    for n,value in ws.items():wfield[i,bn[n]]=value
ee=np.array([e.vertices[:] for e in shirt.data.edges]);a,b=ee.T;cnt=np.bincount(np.r_[a,b],minlength=len(wfield))
mask=np.array([1.22<v.co.z<1.54 and .10<abs(v.co.x)<.39 for v in shirt.data.vertices]);anch=wfield.copy()
for _ in range(45):
    sums=np.column_stack([np.bincount(a,weights=wfield[b,c],minlength=len(wfield))+np.bincount(b,weights=wfield[a,c],minlength=len(wfield)) for c in range(len(bone_names))])
    wfield=.25*wfield+.75*sums/np.maximum(cnt[:,None],1);wfield[~mask]=anch[~mask]
shirt_rows=[norm({n:float(w) for n,w in zip(bone_names,row) if w>1e-5}) for row in wfield]
put_weights(shirt,shirt_rows);outer_surface=surface(shirt)

def garment_weights(p):return sample(p,outer_surface,shirt_rows)
def shell_finish(o,thickness=.0018):
    rows=[garment_weights(v.co) for v in o.data.vertices];put_weights(o,rows)
    if thickness:
        m=o.modifiers.new('RealPairedInnerWall','SOLIDIFY');m.thickness=thickness;m.offset=-1;apply(o,m)
    clean_normals(o);native_attach(o,read_weights(o));report['new_parts'].append(o.name)

def front_point(x,z,offset=.003,back=False):
    y=.55 if back else -.55;direction=Vector((0,-1 if back else 1,0));hit=outer_surface[0].ray_cast(Vector((x,y,z)),direction,1.)
    if hit[0] is None:raise RuntimeError('No native torso at '+str((x,z,back)))
    return hit[0]+Vector((0,offset if back else -offset,0))

def patch(name,corners,family='Uniform',offset=.003,nu=14,nv=12):
    a,b,c,d=[Vector(v) for v in corners];verts=[]
    for j in range(nv+1):
        t=j/nv
        for i in range(nu+1):
            s=i/nu;xz=a.lerp(b,s).lerp(d.lerp(c,s),t);verts.append(tuple(front_point(xz.x,xz.y,offset)))
    faces=[(j*(nu+1)+i,j*(nu+1)+i+1,(j+1)*(nu+1)+i+1,(j+1)*(nu+1)+i) for j in range(nv) for i in range(nu)]
    o=make(name,verts,faces,family)
    if sum(f.normal.y for f in o.data.polygons)>0:
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    shell_finish(o);return o

patch('Security_FrontPlacket',[(-.015,1.071),(.015,1.071),(.015,1.470),(-.015,1.470)],'Trim',.003,4,45)
for sign in [-1,1]:
    x=sign*.111
    patch('Security_ChestPocket_'+str(sign),[(x-.046,1.294),(x+.046,1.294),(x+.046,1.393),(x-.046,1.393)],offset=.005,nu=16,nv=18)
    patch('Security_PocketFlap_'+str(sign),[(x-.047,1.367),(x+.047,1.367),(x+.047,1.397),(x-.047,1.397)],'Trim',.008,16,6)
patch('Security_Tie',[(-.017,1.216),(.017,1.216),(.013,1.473),(-.013,1.473)],'Trim',.008,6,32)

def stud(name,x,z,radius=.004,offset=.012,family='Hardware'):
    co=front_point(x,z,offset);bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=radius,location=co)
    o=bpy.context.object;o.name=name;o.scale.y=.33;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.data.materials.append(bpy.data.materials['Security_'+family]);shell_finish(o,0)
for i,z in enumerate(np.linspace(1.10,1.425,6)):stud('Security_ShirtButton_%02d'%i,0,float(z))
for sign in [-1,1]:stud('Security_PocketButton_'+str(sign),sign*.111,1.382)
patch('Security_IDPlate',[(.076,1.416),(.134,1.416),(.134,1.432),(.076,1.432)],'Hardware',.007,12,4)
patch('Security_TieClip',[(-.023,1.315),(.023,1.315),(.023,1.321),(-.023,1.321)],'Hardware',.012,8,2)

# Collar follows the actual neck opening. The inside layer is made after
# shaping and weights, so it cannot collapse onto the outside projection.
N=96;vertices=[]
for j in range(9):
    t=j/8;z=1.504+.046*t
    for i in range(N):
        theta=2*math.pi*i/N;d=Vector((math.sin(theta),-math.cos(theta),0));center=Vector((0,.017,min(z,1.533)))
        hit=outer_surface[0].ray_cast(center,d,.2)
        r=(hit[0]-center).length if hit[0] is not None else 1/math.sqrt((d.x/.086)**2+(d.y/.094)**2)
        p=center+d*(r+.003);p.z=z;vertices.append(tuple(p))
faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(8) for i in range(N)]
collar=make('Security_CollarStand_Native',vertices,faces,'Trim');shell_finish(collar,.0022)
for sign in [-1,1]:
    patch('Security_CollarLeaf_'+str(sign),[(sign*.018,1.493),(sign*.080,1.518),(sign*.109,1.469),(sign*.047,1.427)],'Uniform',.009,14,16)
    vertices=[];nx=30;ny=8
    # Start outside the real neck opening rather than projecting a strap
    # across empty space inside it.
    start_x=None
    for candidate in np.linspace(.10,.19,46):
        hits=[outer_surface[0].ray_cast(Vector((sign*float(candidate),y,1.70)),Vector((0,0,-1)),.4)[0] for y in [-.002,.017,.036]]
        if all(h is not None and h.z>1.36 for h in hits):start_x=float(candidate)+.006;break
    if start_x is None:raise RuntimeError('No actual shoulder support for epaulette '+str(sign))
    for i in range(nx+1):
        x=sign*(start_x+(.245-start_x)*i/nx)
        for j in range(ny+1):
            y=.017+(j/ny-.5)*.035;hit=outer_surface[0].ray_cast(Vector((x,y,1.70)),Vector((0,0,-1)),.4)
            if hit[0] is None:raise RuntimeError('Missing shoulder under epaulette '+str((x,y)))
            vertices.append(tuple(hit[0]+Vector((0,0,.003))))
    faces=[(i*(ny+1)+j,(i+1)*(ny+1)+j,(i+1)*(ny+1)+j+1,i*(ny+1)+j+1) for i in range(nx) for j in range(ny)]
    ep=make('Security_Epaulette_'+str(sign),vertices,faces,'Trim')
    if sum(f.normal.z for f in ep.data.polygons)<0:
        bm=bmesh.new();bm.from_mesh(ep.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(ep.data);bm.free()
    shell_finish(ep,.0015)

for side in ['l','r']:
    s,e,w=native_targets[side];axis=(w-e).normalized();front=Vector((0,-1,0));front=(front-axis*front.dot(axis)).normalized();around=front.cross(axis).normalized()
    N=64;vertices=[]
    for q in np.linspace(-.070,-.002,12):
        center=w+axis*float(q);r=float(np.interp(q,[-.070,-.002],[.061,.056]))
        for i in range(N):
            t=2*math.pi*i/N;vertices.append(tuple(center+(front*math.cos(t)+around*math.sin(t))*r))
    faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(11) for i in range(N)]
    cuff=make('Security_Cuff_'+side,vertices,faces,'Trim');shell_finish(cuff,.0022)

def lettering(name,text,z,width,back=False,xcenter=0):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.align_x='CENTER';curve.size=.035;curve.extrude=.00035;curve.resolution_u=3
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);active(o);bpy.ops.object.convert(target='MESH');o=bpy.context.object
    factor=width/(max(v.co.x for v in o.data.vertices)-min(v.co.x for v in o.data.vertices))
    for v in o.data.vertices:
        co=v.co.copy();x=xcenter+(-1 if back else 1)*co.x*factor;zz=z+co.y*factor
        v.co=front_point(x,zz,.004+co.z,back)
    o.data.materials.append(bpy.data.materials['Security_Insignia']);clean_normals(o);shell_finish(o,0)
lettering('Security_BackLettering','SECURITY',1.414,.205,True)
lettering('Security_IDLetters','SEC',1.419,.033,False,.105)

# Thickness comes last, in native space, with identical inner/outer weights.
solid=shirt.modifiers.new('PairedUniformThickness','SOLIDIFY');solid.thickness=.0026;solid.offset=-1;apply(shirt,solid)
clean_normals(shirt);native_attach(shirt,read_weights(shirt));report['new_parts'].append(shirt.name)

# Rebuild only the display mask from the intact body. Entire forearms, wrists,
# palms and every finger survive; the seam is well inside the sleeves.
bpy.data.objects.remove(display,do_unlink=True)
display=body.copy();display.data=body.data.copy();display.name='Security_OutfitBody';bpy.context.collection.objects.link(display)
bm=bmesh.new();bm.from_mesh(display.data);remove=[]
for f in bm.faces:
    co=f.calc_center_median();side='l' if co.x>=0 else 'r';s,e,w=native_targets[side];axis=(w-e).normalized()
    forearm=abs(co.x)>.30 and (co-e).dot(axis)>-.055 and co.z>.68
    if not (co.z>1.505 or co.z<.230 or forearm):remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(display.data);bm.free()
body.hide_set(True);body.hide_render=True;display.hide_set(False);display.hide_render=False
rig.animation_data_create();bpy.context.view_layer.update()
report.update(complete_body_vertices=len(body.data.vertices),display_skin_vertices=len(display.data.vertices),
    shoulder_method='single fused native-rest outer surface, body-derived continuous skinning, final-geometry normals, then paired thickness',
    preserved='native bone transforms; V06 clips and timing; cleaned V07 trousers, belt and boots; original complete fingers and foot geometry')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V09.blend'))
(ROOT/'native_uniform_recipe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_NATIVE_V09_AUTHORED '+json.dumps(report),flush=True)
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V09')
exec(compile(export,'export_security_v09','exec'))
