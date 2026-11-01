"""V3 structured game retopology: skived wraps, real stitch cords, fitted ribbon inlays and field seals."""
import sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import surface as surf
import numpy as np
# Retain native end lands and the established material/UV preservation machinery.
prelude=(P.parent/'StaticFieldGripV1/author.py').read_text(encoding='utf-8').split('# Main hand contact')[0]

prelude = prelude.split("native_band('01_NativeUpperMatingLand'")[0]
exec(compile(prelude,str(P/'native_interface_prelude.py'),'exec'))
bpy.data.objects.remove(factory, do_unlink=True)
with bpy.data.libraries.load(str(P.parent/'StaticFieldGripV2/StaticField_Design.blend'), link=False) as (src,dst):
    dst.objects = ['01_NativeUpperMatingLand','02_NativeLowerMatingLand']
for ob in dst.objects:
    bpy.context.collection.objects.link(ob)
    for i, mat in enumerate(ob.data.materials):
        ob.data.materials[i] = dark if mat and 'Recess' in mat.name else native
    parts.append(ob)
# Fine stitches are baked into the leather; no runtime thread material section.
rows[:] = [r for r in rows if r['slot'] != 'M_StaticField_WaxedThread']

bpy.context.preferences.filepaths.save_version=0

def tube(name, points, mat, width, depth=None, N=8):
    depth = depth or width
    closed = (Vector(points[0])-Vector(points[-1])).length < 1e-8
    points = points[:-1] if closed else points
    vs=[]; fs=[]; uv=[]; length=0.
    count=len(points)
    for i, point in enumerate(points):
        p=Vector(point)
        prev=(i-1)%count if closed else max(0,i-1)
        nex=(i+1)%count if closed else min(count-1,i+1)
        t=(Vector(points[nex])-Vector(points[prev])).normalized()
        n=Vector((p.x-CX,p.y-CY,0)).normalized()
        n=(n-t*n.dot(t)).normalized(); b=t.cross(n).normalized()
        if i: length+=(p-Vector(points[i-1])).length
        for j in range(N):
            a=TAU*j/N
            vs.append(tuple(p+n*(depth*math.cos(a))+b*(width*math.sin(a))))
            uv.append((j/N*.001/.065,length/.065))
    for i in range(count if closed else count-1):
        ni=(i+1)%count
        for j in range(N):
            nj=(j+1)%N
            fs.append((i*N+j,i*N+nj,ni*N+nj,ni*N+j))
    if not closed:
        fs.extend([tuple(reversed(range(N))),tuple((count-1)*N+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)

R=surf.R;z0,z1=surf.Z0,surf.Z1
def grid_surface(name,angles,zs,radii,material,body_uv=False):
    if np.ndim(zs)==2:Z=zs;A=np.broadcast_to(angles[None,:],Z.shape)
    else:A,Z=np.meshgrid(angles,zs)
    RR=np.broadcast_to(radii,A.shape);M=len(angles);K=len(Z)
    xyz=np.stack((CX+RR*np.cos(A),CY+RR*np.sin(A),Z),axis=-1).reshape(-1,3)
    uu=A/TAU if body_uv else A*.018/.065
    vv=(Z-z0)/(z1-z0) if body_uv else Z/.065
    uv=np.stack((uu,vv),axis=-1).reshape(-1,2)
    ii=np.arange((K-1)*(M-1)).reshape(K-1,M-1);base=(ii//(M-1))*M+ii%(M-1)
    ff=np.stack((base,base+1,base+M+1,base+M),axis=-1).reshape(-1,4).tolist()
    ff.extend([tuple(reversed(range(M-1))),tuple((K-1)*M+j for j in range(M-1))])
    return mesh(name,xyz.tolist(),ff,material,uv.tolist())
angles=np.linspace(0,TAU,129);zs=np.linspace(z0,z1,257);A,Z=np.meshgrid(angles,zs)
phase=(Z-z0-surf.PITCH*(A-.2)/TAU)/surf.PITCH
fraction=phase-np.floor(phase)
clustered=.18*fraction+.82*(.5-.5*np.cos(np.pi*fraction))
fade=np.clip(np.minimum(Z-z0,z1-Z)/.020,0,1)
Z=Z+surf.PITCH*(clustered-fraction)*fade
grid_surface('03_SkivedOverlappingLeather',angles,Z,surf.leather_radius(A,Z),leather,True)
del A,Z
# Two satin silver strips embedded in accurately cut beds. Both ends pass under
# the ferrule shoulders. Crossings have controlled, sub-millimetre under/over relief.
for sign in (-1,1):
    pts=[]
    for z in np.linspace(z0-.001,z1+.001,401):
        a=sign*TAU*(z-z0)/.106-.8
        r=float(surf.leather_radius(a,z))+.00018+sign*.000032
        pts.append(cyl(a,z,r))
    tube('04_SatinSilverInlay_'+str(sign),pts,silver,.00034,.000095,8)
# Two-ply thread retained in V2 baking source only.
# Dense, individually chamfered forged collar, with engraving beds cut into the core.
zs=np.unique(np.concatenate((np.linspace(.348,.401,33),[p[0] for p in surf.PROFILE])))
A,Z=np.meshgrid(angles,zs)
grid_surface('06_EngravedForgedUpperSleeve',angles,zs,surf.collar_radius(A,Z),steel)
del A,Z
lathe('07_SkivedLowerFerrule',[(-.081,.01530),(-.080,.01542),(-.0785,.01580),(-.078,.01603),(-.0774,.01618),(-.075,.01618),(-.0746,.01592),(-.074,.01588),(-.068,.01588),(-.0674,.01565),(-.0665,.01542),(-.065,.01527),(-.064,.01520)],steel,128)
# Restrained silver lips and dark machined channels separate the material layers.
for name,z,r,w in [('UpperRolledLip',.3578,.01816,.00068),('UpperCrown',.3943,.01781,.00055),('LowerRolledLip',-.0761,.01618,.00040)]:
    lathe('08_Edge_'+name,[(z-w,r-.00007),(z-w*.72,r+.000055),(z+w*.72,r+.000055),(z+w,r-.00007)],silver,128)
for z,r in [(.3606,.01776),(.3916,.01761),(-.0737,.01589)]:
    lathe('09_RecessedAnnulus_'+str(z),[(z-.00022,r),(z-.00012,r+.000012),(z+.00012,r+.000012),(z+.00022,r)],dark,128)
# A broad, flattened interlace with alternating crossings replaces the old wire waves.
for sign in (-1,1):
    pts=[];engrave=[]
    for a in np.linspace(0,TAU,401):
        z=.377+sign*.0057*math.sin(6*a)
        rad=.01817+sign*.000115*math.cos(6*a)
        pts.append(cyl(a,z,rad));engrave.append(cyl(a,z,rad+.000131))
    tube('10_NorseRibbon_'+str(sign),pts,silver,.00058,.000145,8)
    tube('11_EngravedRibbonSpine_'+str(sign),engrave,dark,.000075,.000018,4)
# Double-strand rope margins are seated in shallow turned grooves, not added as loose wires.
for zc in (.365,.3888,-.0705):
    rr=.018075 if zc>0 else .01590
    for sign in (-1,1):
        pts=[cyl(a,zc+sign*.00050*math.sin(20*a),rr+sign*.000035*math.cos(20*a)) for a in np.linspace(0,TAU,321)]
        tube('12_TwistedBorder_'+str(zc)+'_'+str(sign),pts,silver,.00021,.00011,6)
# Curved circular seals replace the flat rectangular badge. All backing surfaces
# have thickness, and terminate below the supporting sleeve surface.
def seal(face,a0):
    N=96;K=8;vs=[];uv=[];fs=[];radius=.00745;zc=.377
    for k in range(K+1):
        q=.000025+(radius-.000025)*k/K
        for j in range(N+1):
            t=TAU*j/N;u=q*math.cos(t);z=zc+q*math.sin(t);a=a0+u/.01805
            lip=.00018*math.exp(-((q-.00685)/.00038)**2)
            bevel=.00040*min(1,(radius-q)/.00055)
            r=.01817+bevel+lip
            vs.append(cyl(a,z,r));uv.append((u/.065,z/.065))
    for k in range(K):
        for j in range(N):
            b=k*(N+1)+j;fs.append((b,b+N+1,b+N+2,b+1))
    fs.append(tuple(range(N)))
    ob=mesh('13_CurvedSealBacking_'+face,vs,fs,steel,uv)
    mod=ob.modifiers.new('Solid backing below collar','SOLIDIFY');mod.thickness=.001;mod.offset=-1
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    for i,rr in enumerate([.0069,.0057]):
        pts=[cyl(a0+rr*math.cos(t)/.01805,zc+rr*math.sin(t),.01870 if i==0 else .01860) for t in np.linspace(0,TAU,161)]
        tube('14_ConcentricFieldRim_'+face+str(i),pts,silver,.000245,.000115,8)
    # One continuous threefold Nordic knot, framed by the field rings.
    pts=[];incised=[]
    for t in np.linspace(0,TAU,241):
        x=.00245*math.sin(t)+.0012*math.sin(2*t)
        z=zc+.00245*math.cos(t)-.0012*math.cos(2*t)
        r=.01863+.000085*math.sin(3*t)
        pts.append(cyl(a0+x/.01805,z,r));incised.append(cyl(a0+x/.01805,z,r+.000105))
    tube('15_ThreefoldThunderKnot_'+face,pts,silver,.00034,.00012,8)
    tube('16_KnotChasedLine_'+face,incised,dark,.000050,.000016,4)
    for a in np.arange(4)*TAU/4:
        pts=[cyl(a0+q*math.cos(a)/.01805,zc+q*math.sin(a),.01861) for q in np.linspace(.0042,.00540,4)]
        tube('17_EnamelFieldBridge_'+face+str(a),pts,glow,.00016,.000055,6)
    # Engraved indexed ticks are seated in the inner rim and carry no extra studs.
    for i in range(24):
        t=TAU*i/24
        pts=[cyl(a0+q*math.cos(t)/.01805,zc+q*math.sin(t),.01865) for q in np.linspace(.00614,.00650,3)]
        tube('18_FieldRimChasing_'+face+str(i),pts,dark,.000045,.000018,4)
seal('Front',-math.pi/2);seal('Back',math.pi/2)

for ob in parts:
    if ob.name.startswith(('01_', '02_')):
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-10)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
source=bpy.data.collections.new('StaticField_EditableParts');bpy.context.scene.collection.children.link(source)
for o in parts:
    for c in list(o.users_collection):c.objects.unlink(o)
    source.objects.link(o)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Design.blend'))
(P/'material_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('STATIC_FIELD_V3_RETOPOLOGIZED',len(parts),flush=True)
