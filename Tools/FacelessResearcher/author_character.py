"""Native-rest body binding and separate continuous laboratory garments."""
from pathlib import Path
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
exec(compile((TOOLS/'body_fit_helpers.py').read_text(encoding='utf-8'),'researcher_body_fit','exec'))

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def put(o,rows):
    o.vertex_groups.clear()
    for n in sorted({n for ws in rows for n in ws}):o.vertex_groups.new(name=n)
    for v,ws in zip(o.data.vertices,rows):
        for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
def read(o):
    names={g.index:g.name for g in o.vertex_groups}
    return [{names[g.group]:g.weight for g in v.groups} for v in o.data.vertices]
def clean(o):
    if o.data.has_custom_normals:o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
    for f in o.data.polygons:f.use_smooth=True
def surf(o):
    o.data.calc_loop_triangles();v=[p.co.copy() for p in o.data.vertices];t=[tuple(x.vertices) for x in o.data.loop_triangles]
    return BVHTree.FromPolygons(v,t,all_triangles=True),v,t
def sample_surface(p,surface,rows):return sample(p,*surface,rows)

# Diffuse the torso/left-arm/right-arm partition along actual skin edges.
# Fingers retain the side-specific donor mapping. No waist nearest-neighbour
# transfer is permitted for sleeves or their attachments.
p=np.array(points);edges=np.array([e.vertices[:] for e in body.data.edges]);a,b=edges.T
field=np.array([[sum(w for n,w in ws.items() if not n.startswith(('upperarm','lowerarm','hand','clavicle','thumb','index','middle','ring','pinky'))),
    sum(w for n,w in ws.items() if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand','clavicle','thumb','index','middle','ring','pinky'))),
    sum(w for n,w in ws.items() if n.endswith('_r') and n.startswith(('upperarm','lowerarm','hand','clavicle','thumb','index','middle','ring','pinky')))] for ws in body_weights])
mask=(p[:,2]>1.30)&(p[:,2]<1.61)&(abs(p[:,0])>.105)&(abs(p[:,0])<.29)
anchors=field.copy();count=np.bincount(np.r_[a,b],minlength=len(p))
_,weld=np.unique(np.round(p,6),axis=0,return_inverse=True);wc=np.bincount(weld)
for k in range(140):
    sums=np.column_stack([np.bincount(a,weights=field[b,c],minlength=len(p))+np.bincount(b,weights=field[a,c],minlength=len(p)) for c in range(3)])
    field=.30*field+.70*sums/np.maximum(count[:,None],1)
    if k%4==0:field=np.column_stack([np.bincount(weld,weights=field[:,c])/wc for c in range(3)])[weld]
    field[~mask]=anchors[~mask]
for i in np.flatnonzero(mask):
    co=points[i];row={}
    for amount,side in zip(field[i,1:],['l','r']):
        s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
        elbow=smooth(-.07,.07,(co-e).dot((w-s).normalized()))
        limb=mixweights({'upperarm_'+side:1.},{'lowerarm_'+side:1.},elbow)
        limb=mixweights(limb,{'clavicle_'+side:1.},.40*(1-smooth(-.015,.12,(co-s).dot((e-s).normalized()))))
        for n,value in limb.items():row[n]=row.get(n,0)+float(amount)*value
    for n,value in torso_weights(co).items():row[n]=row.get(n,0)+float(field[i,0])*value
    body_weights[i]=norm(row)

# Only the new unrigged source is bound; native donor bones and animation
# tracks retain their original reference transforms and hierarchy.
oldnormals=[n.vector.copy() for n in body.data.corner_normals];fit_matrices=[matrix(ws) for ws in body_weights]
mapped=[(fit_matrices[lp.vertex_index].to_3x3().transposed()@normal).normalized() for lp,normal in zip(body.data.loops,oldnormals)]
for v,m in zip(body.data.vertices,fit_matrices):v.co=m.inverted_safe()@v.co
put(body,body_weights);body.data.update();body.data.normals_split_custom_set(mapped)
body.name='Researcher_CompleteBody';body.data.materials[0].name='Researcher_Skin'
body.parent=rig;body.matrix_parent_inverse=rig.matrix_world.inverted();m=body.modifiers.new('NativeNurseSkin','ARMATURE');m.object=rig
for o in list(bpy.context.scene.objects):
    if o not in [body,rig]:bpy.data.objects.remove(o,do_unlink=True)
skin=surf(body);body_rows=read(body);HEAD={b.name:rig.matrix_world@b.head_local for b in rig.data.bones}
def skin_weights(p):return sample_surface(p,skin,body_rows)
def attach(o,rows=None):
    put(o,rows if rows is not None else [skin_weights(v.co) for v in o.data.vertices]);o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    m=o.modifiers.new('NativeNurseSkin','ARMATURE');m.object=rig

# Physically scaled, independently authored cloth / trim / leather / metal.
material_source=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/garment_recipe.py').read_text(encoding='utf-8')
material_source=material_source[material_source.index('def imagefile('):material_source.index('shirtmat=material(')].replace("'Security_'","'Researcher_'")
exec(compile(material_source,'researcher_pbr_materials','exec'))
coatmat=material('Coat',(.64,.675,.66),.82)
pantsmat=material('Trousers',(.042,.053,.065),.82)
trim=material('Trim',(.058,.080,.091),.80)
leather=material('Leather',(.024,.029,.035),.49,'leather')
metal=material('Hardware',(.39,.43,.45),.38,'metal',.80)
parts=[]
def uv(o,mode='torso'):
    layer=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
    for face in o.data.polygons:
        coords=[]
        for li in face.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co;side='l' if co.x>=0 else 'r'
            if mode=='torso' and abs(co.x)>.26 and co.z>1.05:
                start=HEAD['upperarm_'+side];axis=(HEAD['hand_'+side]-start).normalized();q=(co-start).dot(axis);d=co-start-axis*q
                coords.append((math.atan2(d.z,d.y)*.064/.2,q/.2))
            elif mode=='trousers' and co.z<.87:
                start=HEAD['thigh_'+side];axis=(HEAD['foot_'+side]-start).normalized();q=(co-start).dot(axis);d=co-start-axis*q
                coords.append((math.atan2(d.x,-d.y)*.08/.2,q/.2))
            elif mode in ['torso','trousers']:coords.append((math.atan2(co.x,-(co.y-.017))*.18/.2,co.z/.2))
            else:coords.append((co.x/.2,co.z/.2))
        if max(x for x,y in coords)-min(x for x,y in coords)>2.5:coords=[(x+(2*math.pi*.18/.2 if x<0 else 0),y) for x,y in coords]
        for li,c in zip(face.loop_indices,coords):layer.data[li].uv=c
def make(name,verts,faces,mat,mode='planar'):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
    me.materials.append(mat);clean(o);uv(o,mode);parts.append(o);return o
def thick(o,rows,width=.0022):
    put(o,rows);m=o.modifiers.new('MatchingPairedInnerWall','SOLIDIFY');m.thickness=width;m.offset=-1;apply(o,m);clean(o);attach(o,read(o))
def boundary_loop(o,predicate):
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();adj={}
    for e in bm.edges:
        if e.is_boundary and all(predicate(v.co) for v in e.verts):
            a,b=[v.index for v in e.verts];adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    if not adj or any(len(x)!=2 for x in adj.values()):raise RuntimeError('Cannot join garment opening '+o.name+' '+str({degree:sum(len(x)==degree for x in adj.values()) for degree in set(map(len,adj.values()))}))
    start=min(adj);loop=[start];prev=None;current=start
    while True:
        nxt=next(v for v in adj[current] if v!=prev)
        if nxt==start:break
        loop.append(nxt);prev,current=current,nxt
    bm.free();return loop

# The entire upper coat starts from ONE connected native-rest surface,
# including both shoulders and sleeves; all openings are cut analytically.
def plane(bm,point,normal,inner=False,side=None):
    if side is None:geom=list(bm.verts)+list(bm.edges)+list(bm.faces)
    else:
        verts=[v for v in bm.verts if side*v.co.x>.42];vs=set(verts)
        geom=verts+[e for e in bm.edges if all(v in vs for v in e.verts)]+[f for f in bm.faces if all(v in vs for v in f.verts)]
    bmesh.ops.bisect_plane(bm,geom=geom,plane_co=point,plane_no=normal,dist=1e-7,clear_inner=inner,clear_outer=not inner)
volumes=[];N=96;zs=np.linspace(1.01,1.59,76);vv=[]
for z in zs:
    rx=float(np.interp(z,[1.01,1.14,1.25,1.36,1.44,1.49,1.54,1.59],[.20,.175,.156,.183,.178,.135,.078,.065]))
    ry=float(np.interp(z,[1.01,1.20,1.35,1.45,1.54,1.59],[.137,.13,.165,.141,.071,.065]))
    c=Vector((0,.017,float(z)));rr=[]
    for i in range(N):
        t=2*math.pi*i/N;d=Vector((math.sin(t),-math.cos(t),0));expected=1/math.sqrt((d.x/rx)**2+(d.y/ry)**2)
        hit=skin[0].ray_cast(c,d,.34)[0];measured=(hit-c).length+.018 if hit is not None else expected
        rr.append(max(expected*.90,min(expected*1.10,measured)))
    rr=np.array(rr)
    for _ in range(5):rr=(np.roll(rr,1)+2*rr+np.roll(rr,-1))/4
    for i,r in enumerate(rr):t=2*math.pi*i/N;vv.append((math.sin(t)*r,.017-math.cos(t)*r,float(z)))
ff=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(zs)-1) for i in range(N)]
ff.extend([tuple(reversed(range(N))),tuple((len(zs)-1)*N+i for i in range(N))]);volumes.append(make('Researcher_CoatVolume',vv,ff,coatmat))
for side in ['l','r']:
    s,e,w=[HEAD[n+'_'+side] for n in ['upperarm','lowerarm','hand']];ua=(e-s).normalized();la=(w-e).normalized();l1=(e-s).length;l2=(w-e).length
    N=64;qs=np.linspace(-.09,l1+l2+.025,85);vv=[]
    for q in qs:
        c=s+ua*q if q<=l1 else e+la*(q-l1);axis=ua.lerp(la,smooth(l1-.07,l1+.07,q)).normalized()
        frontv=Vector((0,-1,0));frontv=(frontv-axis*frontv.dot(axis)).normalized();around=frontv.cross(axis).normalized()
        r=float(np.interp(q,[-.09,-.025,.04,.13,l1,l1+l2],[.024,.065,.078,.064,.054,.043]))
        for i in range(N):
            t=2*math.pi*i/N;d=frontv*math.cos(t)+around*math.sin(t)
            hit=skin[0].ray_cast(c,d,.14)[0];measured=(hit-c).length+.014 if hit is not None and q>0 else r
            vv.append(tuple(c+d*max(r*.91,min(r*1.08,measured))))
    ff=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(qs)-1) for i in range(N)]
    ff.extend([tuple(reversed(range(N))),tuple((len(qs)-1)*N+i for i in range(N))]);volumes.append(make('Researcher_SleeveVolume_'+side,vv,ff,coatmat))
bpy.ops.object.select_all(action='DESELECT')
for o in volumes:o.select_set(True);parts.remove(o)
bpy.context.view_layer.objects.active=volumes[0];bpy.ops.object.join();coat=bpy.context.object;coat.name='Researcher_LabCoat_Continuous'
coat.data.remesh_voxel_size=.0040;coat.data.remesh_voxel_adaptivity=0.;bpy.ops.object.voxel_remesh()
sm=coat.modifiers.new('SoftSewnShoulders','SMOOTH');sm.factor=.55;sm.iterations=18;apply(coat,sm)
tri_count=sum(len(f.vertices)-2 for f in coat.data.polygons)
dec=coat.modifiers.new('CoatOuterSurfaceDensity','DECIMATE');dec.ratio=min(1.,32000/max(1,tri_count));dec.use_collapse_triangulate=True;apply(coat,dec)
bm=bmesh.new();bm.from_mesh(coat.data)
plane(bm,Vector((0,0,1.055)),Vector((0,0,1)),True)
plane(bm,Vector((0,0,1.545)),Vector((0,0,1)))
for side,sign in [('l',1),('r',-1)]:
    w=HEAD['hand_'+side];axis=(w-HEAD['lowerarm_'+side]).normalized();plane(bm,w-axis*.023,axis,side=sign)
for v in bm.verts:
    if v.is_boundary and abs(v.co.x)<.30:v.co.z=1.050 if v.co.z<1.20 else 1.550
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
bm.to_mesh(coat.data);bm.free();clean(coat)
parts.append(coat)

# Sew an A-line thigh-length hem to the existing waist loop. Both lower
# vents are true openings, so either thigh can stride without cross-leg skin.
hem=boundary_loop(coat,lambda p:abs(p.z-1.050)<.0001)
vv=[v.co.copy() for v in coat.data.vertices];ff=[tuple(f.vertices) for f in coat.data.polygons]
old_hem=[vv[i].copy() for i in hem];angles=[math.atan2(p.x,-(p.y-.017)) for p in old_hem];previous=hem
for j in range(1,25):
    t=j/24;z=1.050-.29*t;new=[]
    for p,a in zip(old_hem,angles):
        target=Vector((.242*math.sin(a),.017-.170*math.cos(a),z));q=p.lerp(target,t);q.z=z
        q+=Vector((math.sin(a),-math.cos(a),0))*(.0017*math.sin(a*10+2*t)*t*t)
        new.append(len(vv));vv.append(q)
    for k in range(len(hem)):
        a=angles[k];front=abs(a)<(.025+.17*t);back=abs(abs(a)-math.pi)<(.020+.11*t) and t>.32
        if front or back:continue
        ff.append((previous[k],previous[(k+1)%len(hem)],new[(k+1)%len(hem)],new[k]))
    previous=new
me=bpy.data.meshes.new('Researcher_ContinuousCoatOuter');me.from_pydata(vv,[],ff);me.materials.append(coatmat);me.update();coat.data=me
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(me);bm.free()
clean(coat);uv(coat)
coat_rows=[]
for v in coat.data.vertices:
    p=v.co
    if p.z<1.06:
        side='l' if p.x>=0 else 'r';leg=smooth(1.07,.79,p.z)*.74
        # One side's tail follows its own thigh only; a narrow center-back
        # transition is shared by both sides until the rear vent begins.
        balance=smooth(-.045,.045,p.x)
        thighs={'thigh_l':balance,'thigh_r':1-balance}
        coat_rows.append(mixweights({'pelvis':1.},thighs,leg))
    else:coat_rows.append(skin_weights(p))
coat_surface=surf(coat)

# Fitted stand collar shares the coat's actual neckline, with continuous
# neck weights; no separately floating ring is used to conceal a gap.
neck=boundary_loop(coat,lambda p:abs(p.z-1.550)<.0001)
vv=[v.co.copy() for v in coat.data.vertices];ff=[tuple(f.vertices) for f in coat.data.polygons];previous=neck
base=[vv[i].copy() for i in neck]
for j in range(1,7):
    t=j/6;new=[]
    for i,p in zip(neck,base):
        q=p.copy();q.z+=.024*t
        h,n,_,_=skin[0].find_nearest(q);target=h+n*.0055;q=q.lerp(target,t*.8)
        new.append(len(vv));vv.append(q);coat_rows.append(mixweights(coat_rows[i],skin_weights(q),t))
    for k in range(len(neck)):ff.append((previous[k],previous[(k+1)%len(neck)],new[(k+1)%len(neck)],new[k]))
    previous=new
me=bpy.data.meshes.new('Researcher_CoatWithSewnCollar');me.from_pydata(vv,[],ff);me.materials.append(coatmat);me.update();coat.data=me
clean(coat);uv(coat);coat_surface=surf(coat)
def coat_weights(p):return sample_surface(p,coat_surface,coat_rows)

def front(x,z,offset=.003,back=False):
    h=coat_surface[0].ray_cast(Vector((x,.55 if back else -.55,z)),Vector((0,-1 if back else 1,0)),1.2)
    if h[0] is None:raise RuntimeError('No coat under detail '+str((x,z)))
    return h[0]+Vector((0,offset if back else -offset,0))
def patch(name,corners,mat=coatmat,offset=.003,nx=12,ny=14):
    a,b,c,d=[Vector(p) for p in corners];v=[]
    for j in range(ny+1):
        for i in range(nx+1):
            p=a.lerp(b,i/nx).lerp(d.lerp(c,i/nx),j/ny);v.append(tuple(front(p.x,p.y,offset)))
    f=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
    o=make(name,v,f,mat);thick(o,[coat_weights(v.co) for v in o.data.vertices],.0015);return o
patch('Researcher_CentrePlacket',[(-.014,1.065),(.014,1.065),(.014,1.50),(-.014,1.50)],coatmat,.004,5,42)
for sign in [-1,1]:
    x=sign*.103
    patch('Researcher_HipPocket_'+str(sign),[(x-.044,.969),(x+.044,.969),(x+.044,1.08),(x-.044,1.08)],coatmat,.005,16,20)
    patch('Researcher_HipPocketEdge_'+str(sign),[(x-.045,1.066),(x+.045,1.066),(x+.045,1.08),(x-.045,1.08)],trim,.007,16,3)
patch('Researcher_ChestPocket',[(.056,1.335),(.137,1.335),(.137,1.405),(.056,1.405)],coatmat,.005,14,12)
patch('Researcher_IDHolder',[(.064,1.410),(.131,1.410),(.131,1.449),(.064,1.449)],trim,.007,12,8)
patch('Researcher_IDPlate',[(.068,1.415),(.127,1.415),(.127,1.444),(.068,1.444)],metal,.010,12,6)
for i,z in enumerate(np.linspace(1.085,1.475,6)):
    p=front(0,float(z),.009);bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.004,location=p)
    o=bpy.context.object;o.name='Researcher_CoatButton_%02d'%i;o.scale.y=.34;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    o.data.materials.append(metal);clean(o);uv(o,'planar');parts.append(o);attach(o,[coat_weights(p)]*len(o.data.vertices))
curve=bpy.data.curves.new('Researcher_IDText','FONT');curve.body='RESEARCH';curve.align_x='CENTER';curve.size=.007;curve.extrude=.00025;curve.resolution_u=2
o=bpy.data.objects.new('Researcher_IDText',curve);bpy.context.collection.objects.link(o);active(o);bpy.ops.object.convert(target='MESH');o=bpy.context.object
for v in o.data.vertices:p=v.co.copy();v.co=front(.097+p.x,1.426+p.y,.0115+p.z)
o.data.materials.append(trim);clean(o);uv(o,'planar');parts.append(o);attach(o,[coat_weights(v.co) for v in o.data.vertices])

# Independent trouser shell is copied from the newly bound body, not from
# any previously rejected security revision or cross-character garment.
pants=body.copy();pants.data=body.data.copy();bpy.context.collection.objects.link(pants);pants.name='Researcher_Trousers';pants.modifiers.clear()
pants.data.materials.clear();pants.data.materials.append(pantsmat)
bm=bmesh.new();bm.from_mesh(pants.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00004)
# Remove arm/hand surfaces by their skin family before horizontal cutting;
# wrists may be lower than the waistband in the reference pose.
deform=bm.verts.layers.deform.active
group_names={g.index:g.name for g in pants.vertex_groups}
if deform:
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if sum(weight for group,weight in v[deform].items()
        if group_names.get(group,'').startswith(('upperarm','lowerarm','hand','clavicle','thumb','index','middle','ring','pinky')))>.4],context='VERTS')
plane(bm,Vector((0,0,1.120)),Vector((0,0,1)))
plane(bm,Vector((0,0,.105)),Vector((0,0,1)),True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
for v in bm.verts:v.co+=v.normal*.009
for _ in range(5):bmesh.ops.smooth_vert(bm,verts=[v for v in bm.verts if not v.is_boundary],factor=.20,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(pants.data);bm.free();clean(pants)
count=sum(len(f.vertices)-2 for f in pants.data.polygons)
dec=pants.modifiers.new('TrouserSurfaceDensity','DECIMATE');dec.ratio=min(1.,24000/max(1,count));dec.use_collapse_triangulate=True;apply(pants,dec)
clean(pants);uv(pants,'trousers');parts.append(pants);thick(pants,[skin_weights(v.co) for v in pants.data.vertices],.0018)

# Closed, low laboratory shoes. Build from a CLOSED foot volume before
# remeshing; the visible body omits covered feet but the full body keeps them.
for side,sign in [('l',1),('r',-1)]:
    shoe=body.copy();shoe.data=body.data.copy();bpy.context.collection.objects.link(shoe);shoe.name='Researcher_ClosedShoe_'+side;shoe.modifiers.clear();shoe.vertex_groups.clear()
    bm=bmesh.new();bm.from_mesh(shoe.data)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if sign*v.co.x<.045],context='VERTS')
    plane(bm,Vector((0,0,.145)),Vector((0,0,1)))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    for v in bm.verts:v.co+=v.normal*.007;v.co.z=max(.005,v.co.z)
    bm.to_mesh(shoe.data);bm.free();shoe.data.materials.clear();shoe.data.materials.append(leather)
    rem=shoe.modifiers.new('ContinuousClosedToe','REMESH');rem.mode='VOXEL';rem.voxel_size=.0038;rem.use_smooth_shade=True;apply(shoe,rem)
    sm=shoe.modifiers.new('LeatherLastSurface','SMOOTH');sm.factor=.55;sm.iterations=7;apply(shoe,sm)
    bm=bmesh.new();bm.from_mesh(shoe.data);plane(bm,Vector((0,0,.134)),Vector((0,0,1)));bm.to_mesh(shoe.data);bm.free()
    clean(shoe);uv(shoe,'planar');parts.append(shoe)
    shoe_rows=[norm({'foot_'+side:1-.6*smooth(.070,.14,v.co.z),'calf_'+side:.6*smooth(.070,.14,v.co.z)}) for v in shoe.data.vertices]
    thick(shoe,shoe_rows,.003)

# Finish main coat thickness only after its connected fit, seam weights and
# details are established. Store the paired count for motion-driven tailoring.
coat['outer_vertex_count']=len(coat.data.vertices)
thick(coat,coat_rows,.0022)

display=body.copy();display.data=body.data.copy();bpy.context.collection.objects.link(display);display.name='Researcher_OutfitBody'
bm=bmesh.new();bm.from_mesh(display.data);remove=[]
for f in bm.faces:
    p=f.calc_center_median();side='l' if p.x>=0 else 'r';w=HEAD['hand_'+side];axis=(w-HEAD['lowerarm_'+side]).normalized()
    exposed=(p.z>1.523 and abs(p.x)<.115) or (abs(p.x)>.30 and (p-w).dot(axis)>-.052)
    if not exposed:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(display.data);bm.free()
rig.name='root';rig['source_world_matrix']=[x for row in rig.matrix_world for x in row]
body.hide_set(True);body.hide_render=True;display.hide_set(False);display.hide_render=False
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
report={'stage':'authored','source':'Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb','source_height_m':1.88,
    'source_body_triangles':len(bodytris),'complete_body_preserved':True,'bone_count':len(rig.data.bones)+1,
    'fit_targets':TARGET,'clothing_parts':[{'name':o.name,'triangles':sum(len(f.vertices)-2 for f in o.data.polygons)} for o in parts],
    'native_rig':'unchanged Nurse reference transforms, shared body-derived garment field',
    'cloth_simulation':False,'rendered':False,'runtime_tested':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V01.blend'))
print('RESEARCHER_BODY_AND_CLOTHES_SAVED '+json.dumps({'parts':len(parts),'body_triangles':len(bodytris),'clothing_triangles':sum(x['triangles'] for x in report['clothing_parts'])}),flush=True)
