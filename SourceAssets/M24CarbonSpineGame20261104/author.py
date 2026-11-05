"""Game art for the M24 carbon stock. Each receiver retains its actual mating face."""
from pathlib import Path
import json, math
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent; S=O.parent
art=S/'M24CarbonSpineConcept'/'ArtSource'
script=art/'concept.py'
env={'__file__':str(script)}
exec(compile(script.read_text().split('# Shot lighting:')[0],str(script),'exec'),env)
if env['WEAVE_PITCH_MULTIPLIER']!=1.:raise RuntimeError('The accepted original weave must be active')
scene=bpy.context.scene;P=env['params'];ease=env['fade']
# Two finer mould details: the underside return of the cheek saddle and the
# recessed indexing grooves on the pad carrier. Both follow the curved shell.
for sign in (-1,1):
    for xx in (1.52,1.63,1.74):
        zz=2.45;h,l,_=P(xx);w=env['sidewidth'](xx,(zz-l)/(h-l))
        env['rod']('Cheek base | fine witness',[(xx-4.14,sign*(w+.004),zz),(xx+.035-4.14,sign*(w+.004),zz+.035)],.006,env['slate'])
old_parts=[o for o in scene.objects if o.type in ('MESH','CURVE') and not o.name.startswith('09 | closed graphite neck cap')]
meta=json.loads((O/'Inputs/seats.json').read_text())
nominal=np.array(json.loads((S/'M24StockContinuity20261031/geometry_contract.json').read_text())['stock']['cut_interface_ring'])
CUT=float(nominal[:,1].mean())
def flatten(ob):
    ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
def triangulate(me):
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
def inputs(kind):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(kind+'.fbx')),use_custom_normals=True)
    obs=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
    if len(obs)!=1:raise ValueError(f'{kind}: unexpected assembly')
    ob=obs[0];flatten(ob)
    mat_index=next(i for i,m in enumerate(ob.data.materials) if 'MI_M24_metal_' in m.name)
    other=next(i for i,m in enumerate(ob.data.materials) if 'MI_M24_stock_' in m.name)
    coords=np.array([v.co[:] for v in ob.data.vertices])
    metal={i for p in ob.data.polygons if p.material_index==mat_index for i in p.vertices}
    furniture={i for p in ob.data.polygons if p.material_index==other for i in p.vertices}
    # FBX welding can remove intermediate points on a straight rim edge.
    # Keep the actual edge vertices of non-cap receiver faces, ordered by
    # projection onto the measured contour of the original assembly.
    boundary={i for p in ob.data.polygons if p.material_index==mat_index and any(abs(coords[k,1]-CUT)>2e-6 for k in p.vertices) for i in p.vertices if abs(coords[i,1]-CUT)<2e-6}
    segments=np.roll(nominal,-1,axis=0)-nominal;lengths=np.linalg.norm(segments,axis=1);offset=np.r_[0,np.cumsum(lengths)]
    ordered=[]
    for v in coords[sorted(boundary)]:
        u=np.clip(np.sum((v-nominal)*segments,axis=1)/np.maximum(lengths**2,1e-18),0,1)
        distance=np.linalg.norm(nominal+u[:,None]*segments-v,axis=1);k=distance.argmin()
        if distance[k]<.00012:ordered.append((offset[k]+u[k]*lengths[k],v))
    result=[]
    for _,v in sorted(ordered,key=lambda entry:entry[0]):
        if not result or np.linalg.norm(v-result[-1])>2e-6:result.append(v)
    if len(result)<100:raise ValueError(f'{kind}: insufficient actual receiver perimeter {len(result)}')
    if np.linalg.norm(result[0]-result[-1])<2e-6:result.pop()
    ring=np.array(result)
    area=lambda a:np.sum(a[:,0]*np.roll(a[:,2],-1)-np.roll(a[:,0],-1)*a[:,2])
    if area(ring)<0:ring=ring[::-1].copy()
    center=(ring.min(0)+ring.max(0))/2
    # Start the UV and shape transition at the centre of the upper edge.
    # The native receiver weld sometimes has only its two corner vertices on
    # that edge. Starting at a corner would twist the crown toward one side.
    crossings=[]
    for i,p in enumerate(ring):
        q=ring[(i+1)%len(ring)]
        if min(p[0],q[0])<=center[0]<=max(p[0],q[0]) and abs(q[0]-p[0])>1e-9:
            crossing=p+(q-p)*((center[0]-p[0])/(q[0]-p[0]))
            crossings.append((crossing[2],i,crossing))
    _,i,crossing=max(crossings,key=lambda v:v[0]);j=(i+1)%len(ring)
    if np.linalg.norm(crossing-ring[i])<2e-6:j=i
    elif np.linalg.norm(crossing-ring[j])>=2e-6:
        ring=np.insert(ring,i+1,crossing,axis=0);j=i+1
    ring=np.roll(ring,-j,axis=0)
    rear=float(coords[list(furniture),1].min())
    bm=bmesh.new();bm.from_mesh(ob.data)
    remove=[f for f in bm.faces if f.material_index!=mat_index or all(abs(v.co.y-CUT)<2e-6 for v in f.verts)]
    bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(ob.data);bm.free()
    # Keep the receiver's source UVs, surfaces and normals. Its original
    # finish is restored by slot at UE import, for this particular chassis.
    mat=bpy.data.materials.get('CS_Receiver') or bpy.data.materials.new('CS_Receiver')
    ob.data.materials.clear();ob.data.materials.append(mat)
    for face in ob.data.polygons:face.material_index=0
    ob.name='Donor receiver | '+kind
    return ob,ring,rear
donors={kind:inputs(kind) for kind in ('Native','Advanced')}
original={};deps=bpy.context.evaluated_depsgraph_get()
for ob in old_parts:
    ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,depsgraph=deps)
    me.transform(ob.matrix_world)
    if len(me.polygons):original[ob.name]=me
umin=min(v.co.x+4.14 for me in original.values() for v in me.vertices);umax=8.05
styles={env[key].name:(label,gain,theta) for key,label,gain,theta in [
    ('carbon_shell','CS_WeaveBody',2.20,8),('carbon_flute','CS_WeaveSpine',2.45,-15),('carbon_comb','CS_WeaveCrown',2.72,17),
    ('rub','CS_Rubber',0,0),('padface','CS_Pad',0,0),('poly','CS_Cheek',0,0),('dark','CS_Dark',0,0),('slate','CS_Metal',0,0),('ti','CS_Titanium',0,0),('ivory','CS_Index',0,0)]}
def game_material(me):
    for i,old in enumerate(list(me.materials)):
        if not old:continue
        name,freq,rot=styles[old.name];new=bpy.data.materials.get(name) or bpy.data.materials.new(name)
        me.materials[i]=new
        if freq and me.uv_layers.active:
            uv=me.uv_layers.active.data;a=math.radians(rot);c,s=math.cos(a),math.sin(a)
            for p in me.polygons:
                if p.material_index!=i:continue
                for li in p.loop_indices:
                    u,v=uv[li].uv;uv[li].uv=(freq*(u*c-v*s),freq*(u*s+v*c))
    if not me.uv_layers:
        layer=me.uv_layers.new(name='DetailUV')
        for p in me.polygons:
            axes=sorted(range(3),key=lambda k:abs(p.normal[k]))[:2]
            for i in p.loop_indices:
                p0=me.vertices[me.loops[i].vertex_index].co;layer.data[i].uv=(p0[axes[0]],p0[axes[1]])
def stock_map(point,rear):
    x,y,z=point;u=x+4.14;long=rear+(u-umin)*(CUT-rear)/(umax-umin)
    centerz=(float(nominal[:,2].min())+float(nominal[:,2].max()))*.5
    z_out=centerz+(z-1.765)*.0573
    # Preserve the level bottom of the butt and favor a level cheek line over
    # the bearing area; retain the deliberately sloped front of the comb.
    z_out+=.0027*ease(.11,.32,u)*(1-ease(2.3,3.4,u))*(1-ease(.32,1.15,z))
    if z>2.45:
        z_out+=.0031*ease(1.74,3.55,u)*(1-ease(3.7,4.7,u))*ease(2.45,2.80,z)
    x_out=-y*.041
    # The front belly is the existing right-hand contact band. Keep the top
    # and bottom of the beam on the native stock datum while tapering the rear.
    w=ease(-.221,-.155,long)
    hi,lo,half=P(u)
    frac=(z-lo)/(hi-lo)
    z_out=z_out*(1-w)+(.0569+(.10545-.0569)*frac)*w
    width=np.interp(long,[-.18,-.15,-.125,-.10,-.08,-.06],[.0186,.01865,.01825,.0157,.01565,.0208])
    x_out=x_out*(1-w)+(-y/half*width)*w
    return np.array((x_out,long,z_out))
def rim_at(ring,t):
    wrap=np.vstack((ring,ring[0]));l=np.r_[0,np.cumsum(np.linalg.norm(np.diff(wrap,axis=0),axis=1))];l/=l[-1]
    return np.column_stack([np.interp(t,l,wrap[:,j]) for j in range(3)]),l
def side_map(point,rear,ring):
    p=stock_map(point,rear);blend=ease(CUT-.047,CUT,p[1])
    if blend<=0:return p
    x,y,z=point;u=x+4.14;hi,lo,half=P(u);s=np.clip((z-lo)/(hi-lo),0,1)
    q=2*s-1;angle=math.acos(math.copysign(abs(q)**(1/.60),q))
    if y<0:angle=2*math.pi-angle
    base=stock_map((x,math.copysign(env['sidewidth'](u,s),y),z),rear)
    contour,_=rim_at(ring,angle/(2*math.pi))
    p[[0,2]]+=blend*(contour[0,[0,2]]-base[[0,2]])
    p[1]-=.0012*blend
    return p
def neck(me,ring):
    # The source shell is a sequence of 104-point sections. Keep its UV0 and
    # re-shape the last sections into the measured receiver loop. End at the
    # exact receiver vertices, matching unequal ring counts with a stitched strip.
    M=104;N=len(me.vertices)//M
    if N*M!=len(me.vertices):raise ValueError('Unexpected carbon shell topology')
    # Continue the carbon UVs across the narrow patch, including the wrap seam.
    rim_uv=[None]*(M+1)
    uvdata=me.uv_layers.active.data
    for j in range(M):
        f=me.polygons[(N-2)*M+j]
        for li in f.loop_indices:
            row,col=divmod(me.loops[li].vertex_index,M)
            if row==N-1:rim_uv[M if j==M-1 and col==0 else col]=uvdata[li].uv.copy()
    donor,l=rim_at(ring,np.arange(M)/M)
    for i in range(N):
        for j in range(M):
            v=me.vertices[i*M+j];p=np.asarray(v.co).copy();t=ease(CUT-.047,CUT,p[1])
            p[[0,2]]=(1-t)*p[[0,2]]+t*donor[j,[0,2]]
            p[1]-=.0012*t;v.co=p
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
    plain=[bm.verts[(N-1)*M+j] for j in range(M)]
    for f in list(bm.faces):
        if all(v.index>=(N-1)*M for v in f.verts):bm.faces.remove(f)
    extra=[bm.verts.new(p.tolist()) for p in ring];i=j=0;n=len(extra)
    uv=bm.loops.layers.uv.active
    position={v:(k/M,False) for k,v in enumerate(plain)}
    position.update({v:(l[k],True) for k,v in enumerate(extra)})
    while i<M or j<n:
        ta=(i+1)/M if i<M else 2.;tb=l[j+1] if j<n else 2.
        start=plain[i%M];end=extra[j%n]
        if abs(ta-tb)<1e-7:
            face=bm.faces.new([start,plain[(i+1)%M],extra[(j+1)%n],end]);i+=1;j+=1
        elif ta<tb:
            face=bm.faces.new([start,plain[(i+1)%M],end]);i+=1
        else:
            face=bm.faces.new([start,extra[(j+1)%n],end]);j+=1
        face.smooth=True
        if uv:
            for loop in face.loops:
                t,front=position[loop.vert]
                if t<1e-7 and any(position[a][0]>.90 for a in face.verts):t=1.
                k=min(int(t*M),M-1);fraction=t*M-k
                u0,v0=rim_uv[k].lerp(rim_uv[k+1],fraction)
                loop[uv].uv=(u0+(.0012*(umax-umin)/(CUT-min(d[2] for d in donors.values())) if front else 0.),v0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
def simplify(ob):
    bpy.context.view_layer.objects.active=ob
    num=sum(len(p.vertices)-2 for p in ob.data.polygons)
    if num<1100:return
    mod=ob.modifiers.new('Game surface density','DECIMATE')
    mod.ratio=.48 if ob.name.startswith('01 |') else .43 if ob.name.startswith('06 |') else .31
    if ob.name.startswith('01 |'):
        group=ob.vertex_groups.new(name='Receiver weld protection')
        # DECIMATE with a vertex group favors protected, non-selected seam.
        eligible=[v.index for v in ob.data.vertices if v.co.y<CUT-.004]
        group.add(eligible,1.,'REPLACE');mod.vertex_group=group.name;mod.vertex_group_factor=1000.
    bpy.ops.object.modifier_apply(modifier=mod.name)
def export(obs,path):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=False,use_tspace=True,use_triangles=True,mesh_smooth_type='FACE')
report={'weave_pitch':1,'models':{},'source_sha':{k:v['sha256'] for k,v in meta.items()}}
assembly_collections=[]
for kind,(receiver,ring,rear) in donors.items():
    col=bpy.data.collections.new(kind+' | fitted to M24');scene.collection.children.link(col);assembly_collections.append(col)
    for c in list(receiver.users_collection):c.objects.unlink(receiver)
    col.objects.link(receiver);parts=[receiver]
    for name,template in original.items():
        me=template.copy();ob=bpy.data.objects.new(name+' '+kind,me);col.objects.link(ob)
        for v in me.vertices:v.co=side_map(v.co,rear,ring) if name.startswith('02 |') else stock_map(v.co,rear)
        if name.startswith('01 |'):neck(me,ring)
        game_material(me);triangulate(me)
        # Keep the precise interface on LOD0. Reduce smaller closed pieces.
        if not name.startswith('01 |'):simplify(ob)
        parts.append(ob)
    file=O/'Exports'/('SM_M24_CarbonSpine_'+kind+'.fbx');export(parts,file)
    report['models'][kind]={'fbx':file.name,'interface_points':len(ring),'ring':ring.tolist(),'shoulder_y_m':rear,'seam_y_m':CUT,
        'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in parts),'material':meta[kind]['slots'][0]['material']}
# Leave the author scene with actual-scale parts and useful editor materials.
for ob in old_parts:
    ob.hide_set(True);ob.hide_render=True
for ob in list(scene.objects):
    if ob.name.startswith('09 | closed graphite'):ob.hide_render=True;ob.hide_set(True)
for ob in assembly_collections[1].objects:ob.hide_set(True);ob.hide_render=True
# Apply the original look to the author materials. The FBX already has mapped
# weave UVs, so use them directly rather than applying its UV scale twice.
for old_name,(new_name,freq,rot) in styles.items():
    target=bpy.data.materials.get(new_name)
    if not target:continue
    src=bpy.data.materials[old_name];new=src.copy();new.name=new_name+'_author'
    for node in new.node_tree.nodes:
        if node.type=='MAPPING':
            node.inputs['Scale'].default_value=(1,1,1);node.inputs['Rotation'].default_value=(0,0,0)
    target.user_remap(new)
    if target.users==0:bpy.data.materials.remove(target)
    new.name=new_name
rc=bpy.data.materials.get('CS_Receiver')
if rc:
    rc.diffuse_color=(.026,.029,.032,1);rc.use_nodes=True
    bs=rc.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.026,.029,.032,1);bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.48
for n in ('woven_face.png','woven_height.png'):bpy.data.images[n].pack()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.region_3d.view_distance=.72;sp.region_3d.view_location=(0,-.03,.075)
            sp.region_3d.view_rotation=Vector((1,.23,-.15)).to_track_quat('-Z','Y');sp.overlay.show_overlays=False;sp.shading.type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_CarbonSpine_Fitted.blend'),compress=True)
(O/'geometry.json').write_text(json.dumps(report,indent=2))
print('M24_CARBON_GAME_EXPORTED',[(k,v['triangles'],v['interface_points']) for k,v in report['models'].items()],flush=True)
