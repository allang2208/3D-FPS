"""Replace overlap sleeves with welded tangent lofts. Preserve original blade/rig."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OLD=P.parent/'MeleeGuards20260915'
ID=sys.argv[sys.argv.index('--')+1];OUT=P/ID;OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(OLD/'OriginalGuardReference.blend'))
obj=bpy.data.objects['FrostCrystalSword_Blade'];mesh=obj.data
for extra in bpy.context.scene.objects:
    if extra!=obj and extra.name not in {'ReferenceCamera','key','fill','rim'}:extra.hide_render=True
oldmat=mesh.materials[0];oldnorm=[n.vector.copy() for n in mesh.corner_normals]
bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
keepnormal=bm.loops.layers.float_vector.new('OriginalCornerNormal')
for f in bm.faces:
    for l,li in zip(f.loops,mesh.polygons[f.index].loop_indices):l[keepnormal]=oldnorm[li]
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
outer=[f for f in bm.faces if abs(f.calc_center_median().x)>.060 and -.048<f.calc_center_median().z<.065]
bmesh.ops.delete(bm,geom=outer,context='FACES');bm.normal_update()
source_vertices=set(bm.verts)
profile=json.loads((OLD/ID/'retopology_profile.json').read_text())
report={'id':ID,'method':'Welded C1 tangent transition from original cut boundary; no sleeves or overlapping caps','sides':{}}

def sorted_ring(vertices):
    center=sum((v.co for v in vertices),Vector())/len(vertices)
    members=set(vertices)
    crossings=[]
    for e in set(e for v in vertices for e in v.link_edges if e.is_boundary and all(w in members for w in e.verts)):
        a,b=e.verts
        if (a.co.z-center.z)*(b.co.z-center.z)<=0 and abs(b.co.z-a.co.z)>1e-9:
            t=(center.z-a.co.z)/(b.co.z-a.co.z);p=a.co.lerp(b.co,t);crossings.append((p.y,e,a,b,t))
    _,edge,a,b,t=min(crossings,key=lambda row:row[0])
    if t<1e-7:start=a
    elif t>1-1e-7:start=b
    else:
        _,start=bmesh.utils.edge_split(edge,a,t);vertices.append(start);members.add(start)
    ordered=[start];previous=None;current=start
    while True:
        neighbors=[e.other_vert(current) for e in current.link_edges if e.is_boundary and e.other_vert(current) in members and e.other_vert(current)!=previous]
        if not neighbors:raise RuntimeError('Broken root boundary')
        nxt=neighbors[0]
        if nxt==start:break
        if nxt in ordered:raise RuntimeError('Branching root boundary')
        ordered.append(nxt);previous,current=current,nxt
    if len(ordered)!=len(vertices):raise RuntimeError('Multiple root contours')
    area=sum(a.co.y*b.co.z-b.co.y*a.co.z for a,b in zip(ordered,ordered[1:]+ordered[:1]))
    if area<0:ordered=[ordered[0]]+list(reversed(ordered[1:]))
    return ordered,center
def ring_edges(vertices):
    return [next(e for e in a.link_edges if e.other_vert(a)==b) for a,b in zip(vertices,vertices[1:]+vertices[:1])]
def refine_ring(vertices,angles,allangles):
    result={}
    for i,a in enumerate(vertices):
        b=vertices[(i+1)%len(vertices)];lo=angles[i];hi=angles[i+1] if i+1<len(vertices) else angles[0]+2*math.pi
        result[round(lo,9)]=a;prev=a;last=lo
        for t in allangles:
            tt=t if t>=lo else t+2*math.pi
            if tt<=lo+1e-8 or tt>=hi-1e-8:continue
            e=next(e for e in prev.link_edges if e.other_vert(prev)==b)
            _,v=bmesh.utils.edge_split(e,prev,(tt-last)/(hi-last));result[round(t,9)]=v;prev=v;last=tt
    return [result[round(t,9)] for t in allangles]
def angle_list(vertices,center):
    lengths=[Vector((a.co.y-b.co.y,a.co.z-b.co.z)).length for a,b in zip(vertices,vertices[1:]+vertices[:1])]
    total=sum(lengths);acc=0;values=[]
    for length in lengths:values.append(-math.pi+2*math.pi*acc/total);acc+=length
    return values

for sign in [-1,1]:
    boundary=[e for e in bm.edges if e.is_boundary and all(sign*v.co.x>.050 for v in e.verts)]
    start,sc=sorted_ring(list(set(v for e in boundary for v in e.verts)))
    # Preserve all real root samples instead of replacing their envelope with a box.
    root_z0=min(v.co.z for v in start);root_z1=max(v.co.z for v in start)
    yc=(min(v.co.y for v in start)+max(v.co.y for v in start))/2
    zc=(root_z0+root_z1)/2
    sz=sum(profile['root_z'])/2;ratio=(root_z1-root_z0)/(profile['root_z'][1]-profile['root_z'][0])
    cut={'bastion_guard':.086,'riposte_guard':.083,'light_guard':.080}[ID]
    tip={'bastion_guard':.147,'riposte_guard':.144,'light_guard':.137}[ID]
    half={'bastion_guard':.013,'riposte_guard':.010,'light_guard':.007}[ID]
    transformed=[]
    for point_index,(x,z) in enumerate(profile['vertices_xz']):
        t=(x-profile['cut'])/(profile['max_x']-profile['cut']);s=min(1,t/.45);s=s*s*(3-2*s)
        zz=(z-sz)*(ratio+(1-ratio)*s)+zc+(t*t*(3-2*t))*(sz-zc)
        beginning=.075 if ID=='light_guard' else .071
        xx=beginning+t*(tip-beginning)
        if ID=='light_guard' and point_index>=profile['loop_ends'][0]:
            # Fill the first 8 mm of the pierced wing into one continuous neck;
            # the opening begins beyond the rounded, welded root.
            hole=profile['vertices_xz'][profile['loop_ends'][0]:]
            h0=min(v[0] for v in hole);h1=max(v[0] for v in hole)
            outer_end=beginning+(h1-profile['cut'])/(profile['max_x']-profile['cut'])*(tip-beginning)
            xx=.084+(x-h0)/(h1-h0)*(outer_end-.084)
        transformed.append((sign*xx,zz))
    n=len(transformed)
    verts=[(x,yc-half,z) for x,z in transformed]+[(x,yc+half,z) for x,z in transformed]
    faces=[list(t) for t in profile['triangles']]+[[i+n for i in reversed(t)] for t in profile['triangles']]
    offset=0
    for end in profile['loop_ends']:
        for i in range(offset,end):
            j=offset if i+1==end else i+1;faces.append([i,j,j+n,i+n])
        offset=end
    data=bpy.data.meshes.new('Wing');data.from_pydata(verts,[],faces);data.update()
    clean=bmesh.new();clean.from_mesh(data);bmesh.ops.recalc_face_normals(clean,faces=list(clean.faces));clean.to_mesh(data);clean.free()
    wing=bpy.data.objects.new('Wing',data);bpy.context.collection.objects.link(wing)
    bpy.ops.object.select_all(action='DESELECT');wing.select_set(True);bpy.context.view_layer.objects.active=wing
    bevel=wing.modifiers.new('Rounded perimeter','BEVEL');bevel.width=.0009 if ID=='light_guard' else .0014;bevel.segments=5
    bevel.limit_method='ANGLE';bevel.angle_limit=.4
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    wbm=bmesh.new();wbm.from_mesh(wing.data);bmesh.ops.recalc_face_normals(wbm,faces=list(wbm.faces))
    bmesh.ops.bisect_plane(wbm,geom=list(wbm.verts)+list(wbm.edges)+list(wbm.faces),dist=.0000001,plane_co=(sign*cut,0,0),plane_no=(sign,0,0),clear_inner=True,clear_outer=False)
    bmesh.ops.remove_doubles(wbm,verts=list(wbm.verts),dist=.000002)
    bad=[v for v in wbm.verts if not v.link_faces]
    if bad:bmesh.ops.delete(wbm,geom=bad,context='VERTS')
    print('WING_BOUNDARY',ID,sign,sum(e.is_boundary for e in wbm.edges),flush=True)
    wbm.to_mesh(wing.data);wbm.free()
    previous=set(bm.verts);bm.from_mesh(wing.data);new=set(bm.verts)-previous
    end,ec=sorted_ring([v for v in new if abs(v.co.x-sign*cut)<.000001 and any(e.is_boundary and all(abs(w.co.x-sign*cut)<.000001 for w in e.verts) for e in v.link_edges)])
    if len(end)<4:raise RuntimeError('No open generated root')
    # Include every source edge corner in both sections, then split boundary
    # edges exactly. The loft shares actual vertices at both ends.
    sa=angle_list(start,sc);ea=angle_list(end,ec)
    angles=sorted(set(round(a,9) for a in sa+ea))
    start=refine_ring(start,sa,angles);end=refine_ring(end,ea,angles)
    bm.normal_update();rings=[start];steps=16
    for k in range(1,steps):
        t=k/steps;ring=[]
        for a,b in zip(start,end):
            distance=abs(b.co.x-a.co.x)
            def tangent(v):
                normal=v.normal.normalized();direction=Vector((sign,0,0));d=direction-normal*direction.dot(normal)
                if abs(d.x)<.4:d=direction
                return d*(distance/max(.4,abs(d.x)))
            m0=tangent(a);m1=tangent(b)
            # Shape follows the source and target tangent planes; roots become
            # thick, hooked or slim according to each actual wing section.
            pos=(2*t**3-3*t*t+1)*a.co+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*b.co+(t**3-t*t)*m1
            ring.append(bm.verts.new(pos))
        rings.append(ring)
    rings.append(end)
    for ra,rb in zip(rings,rings[1:]):
        for i in range(len(ra)):
            j=(i+1)%len(ra);bm.faces.new((ra[i],ra[j],rb[j],rb[i]))
    report['sides'][str(sign)]={'boundary_samples':len(start),'loft_rows':steps,'span_mm':[(min(sign*v.co.x for v in start))*1000,cut*1000],'end_thickness_mm':2*half*1000}
    bpy.data.objects.remove(wing,do_unlink=True)

# Relax scan-scale ripples across both ends of the loft, with zero influence
# beyond the local bronze join and bounded displacement of retained surfaces.
base_positions={v:v.co.copy() for v in bm.verts}
for iteration in range(5):
    moves={}
    for v in bm.verts:
        x=abs(v.co.x)
        if not .043<x<.095 or not -.022<v.co.z<.034:continue
        weight=min(1,(x-.043)/.012,(.095-x)/.012)
        neighbors=[e.other_vert(v) for e in v.link_edges]
        if not neighbors:continue
        average=sum((w.co for w in neighbors),Vector())/len(neighbors)
        target=v.co.lerp(average,.42*weight)
        shift=target-base_positions[v];limit=.0007 if v in source_vertices else .0014
        if shift.length>limit:target=base_positions[v]+shift.normalized()*limit
        moves[v]=target
    for v,target in moves.items():v.co=target
bm.normal_update()
# All three variants use the same continuously blended original bronze finish.
# Old texture/normal remain unchanged outside this small guard transition.
uv0=bm.loops.layers.uv.active
uv1=bm.loops.layers.uv.new('StockBronzeUV')
color=bm.loops.layers.color.new('GuardFinish')
finish=json.loads((OLD/'finish_patch.json').read_text());lo=finish['uv_min'];hi=finish['uv_max']
for f in bm.faces:
    f.material_index=0;f.smooth=True
    for l in f.loops:
        p=l.vert.co
        t=max(0,min(1,(abs(p.x)-.036)/.022));t=t*t*(3-2*t)
        in_guard=-.045<p.z<.050
        original=l.vert in source_vertices
        mix=t if in_guard else 0
        if not original:mix=1
        l[color]=(mix,mix,mix,1)
        # Stable coordinates on both sides of the weld, with no new UV seam.
        u=max(0,min(1,abs(p.x)/.15));v=max(0,min(1,(p.z+.04)/.12))
        l[uv1].uv=(lo[0]+u*(hi[0]-lo[0]),lo[1]+v*(hi[1]-lo[1]))
        if mix>.001:l[keepnormal]=Vector()
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
# Only the two former open seams are relevant here; the original source can
# contain unrelated imported boundaries at blade/grip material islands.
report['open_edges_in_transition']=sum(e.is_boundary and all(.056<abs(v.co.x)<.092 and -.05<v.co.z<.06 for v in e.verts) for e in bm.edges)
bm.to_mesh(mesh);bm.free();mesh.update()
stored=mesh.attributes.get('OriginalCornerNormal')
normals=[tuple(stored.data[i].vector) if stored and stored.data[i].vector.length>.5 else tuple(mesh.corner_normals[i].vector) for i in range(len(mesh.loops))]
mesh.normals_split_custom_set(normals)
mat=bpy.data.materials.new('M_FrostCrystalSword_SeamlessBronze');mat.use_nodes=True
N=mat.node_tree.nodes;L=mat.node_tree.links;bsdf=next(n for n in N if n.type=='BSDF_PRINCIPLED')
col=N.new('ShaderNodeVertexColor');col.layer_name='GuardFinish'
origuv=N.new('ShaderNodeUVMap');origuv.uv_map=mesh.uv_layers[0].name
bronzeuv=N.new('ShaderNodeUVMap');bronzeuv.uv_map='StockBronzeUV'
for suffix,socket in [('texture','Base Color'),('metallic','Metallic'),('roughness','Roughness')]:
    img=next(n.image for n in oldmat.node_tree.nodes if n.type=='TEX_IMAGE' and (suffix in n.image.name if suffix!='texture' else not any(s in n.image.name for s in ['normal','metallic','roughness'])))
    a=N.new('ShaderNodeTexImage');a.image=img;L.new(origuv.outputs['UV'],a.inputs['Vector'])
    b=N.new('ShaderNodeTexImage');b.image=img;L.new(bronzeuv.outputs['UV'],b.inputs['Vector'])
    mix=N.new('ShaderNodeMixRGB');L.new(col.outputs['Color'],mix.inputs[0]);L.new(a.outputs['Color'],mix.inputs[1]);L.new(b.outputs['Color'],mix.inputs[2]);L.new(mix.outputs[0],bsdf.inputs[socket])
img=next(n.image for n in oldmat.node_tree.nodes if n.type=='TEX_IMAGE' and 'normal' in n.image.name)
a=N.new('ShaderNodeTexImage');a.image=img;L.new(origuv.outputs['UV'],a.inputs['Vector'])
mix=N.new('ShaderNodeMixRGB');mix.inputs[2].default_value=(.5,.5,1,1);L.new(col.outputs['Color'],mix.inputs[0]);L.new(a.outputs['Color'],mix.inputs[1])
normal=N.new('ShaderNodeNormalMap');normal.uv_map=mesh.uv_layers[0].name;L.new(mix.outputs[0],normal.inputs['Color']);L.new(normal.outputs[0],bsdf.inputs['Normal'])
mesh.materials.clear();mesh.materials.append(mat)
obj.name='FrostCrystalSword_Seamless';scene=bpy.context.scene
def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
export(OUT/('SM_FrostCrystalSword_'+ID+'.fbx'),[obj])
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.world.color=(.07,.07,.07)
scene.world.use_nodes=True;scene.world.node_tree.nodes.clear()
background=scene.world.node_tree.nodes.new('ShaderNodeBackground');background.inputs['Color'].default_value=(.18,.18,.18,1);background.inputs['Strength'].default_value=.7
world_out=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(background.outputs[0],world_out.inputs[0])
target=Vector((0,0,.015));cam=scene.camera;cam.data.ortho_scale=.35
for view,delta in [('front',(0,-2,0)),('oblique',(.5,-2,.65)),('back',(0,2,.2))]:
    cam.location=target+Vector(delta);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(view+'.png'));bpy.ops.render.render(write_still=True)
# Same geometry/UVs goes to the held sword; leave existing arm skinning alone.
source=P.parent/'MeshyMelee20260915/FrostCrystalSword_Manny_Editable.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=['SK_RuneSword_Rig','SK_Manny_Arms_Export']
for o in dst.objects:scene.collection.objects.link(o)
rig=bpy.data.objects['SK_RuneSword_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export'];rig.animation_data_clear();rig.data.pose_position='REST'
mesh.transform(rig.data.bones['WPN_root'].matrix_local);obj.parent=rig;obj.matrix_parent_inverse=Matrix.Identity(4)
obj.vertex_groups.clear();g=obj.vertex_groups.new(name='WPN_root');g.add(list(range(len(mesh.vertices))),1,'REPLACE')
mod=obj.modifiers.new('Original rigid weapon binding','ARMATURE');mod.object=rig
export(OUT/('SK_FrostCrystalSword_'+ID+'.fbx'),[arms,obj,rig])
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('FrostCrystalSword_'+ID+'_Editable.blend')))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print('SEAMLESS_GUARD_COMPLETE',json.dumps(report),flush=True)
