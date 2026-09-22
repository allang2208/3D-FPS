"""Clean upper shading/skin support and reduce hidden cloth workload."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Revision06'
sys.path.insert(0,str(Path(__file__).parent))
from author_drape04 import export
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Master.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');r.data.pose_position='REST'
rest={b.name:(r.matrix_world@b.matrix_local).translation for b in r.data.bones}
upper=bpy.data.objects['Witch_UpperRobe'];before=len(upper.data.vertices)
bm=bmesh.new();bm.from_mesh(upper.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
tiny=[f for f in bm.faces if f.calc_area()<1e-10]
if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
# Preserve real hems and folds; only calm noisy interior facets.
smooth=[v for v in bm.verts if len(v.link_edges)>2 and all(e.is_manifold and e.calc_face_angle(0)<1.05 for e in v.link_edges)]
for _ in range(3):bmesh.ops.smooth_vert(bm,verts=smooth,factor=.12,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(upper.data);bm.free()
if upper.data.has_custom_normals:upper.data.normals_split_custom_set([(0.,0.,0.)]*len(upper.data.loops))
for p in upper.data.polygons:p.use_smooth=True
material=upper.data.materials[0];nodes=material.node_tree.nodes;links=material.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
source_color=bs.inputs['Base Color'].links[0].from_socket
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.28;mix.inputs[2].default_value=(.12,.10,.068,1)
links.new(source_color,mix.inputs[1]);links.new(mix.outputs[0],bs.inputs['Base Color'])
for link in list(bs.inputs['Roughness'].links):links.remove(link)
bs.inputs['Roughness'].default_value=.87;bs.inputs['Specular IOR Level'].default_value=.18
for n in nodes:
    if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.24
# Existing sleeve weights used only the main forearm; share axial rotation with
# the helper bones now animated by Arm06 instead of twisting only the wrist.
for side in ('l','r'):
    base='lowerarm_'+side;names=['lowerarm_twist_02_'+side,'lowerarm_twist_01_'+side]
    if base not in upper.vertex_groups:continue
    for n in names:
        if n not in upper.vertex_groups:upper.vertex_groups.new(name=n)
    a=rest[base];b=rest['hand_'+side];axis=b-a
    for v in upper.data.vertices:
        ws={upper.vertex_groups[g.group].name:g.weight for g in v.groups}
        weight=ws.get(base,0.)
        if weight<.001:continue
        t=max(0.,min(1.,(v.co-a).dot(axis)/axis.length_squared))
        share=.65*t;upper.vertex_groups[base].add([v.index],weight*(1-share),'REPLACE')
        blend=max(0.,min(1.,(t-.25)/.5))
        for n,w in zip(names,(1-blend,blend)):
            if w*share>0:upper.vertex_groups[n].add([v.index],ws.get(n,0.)+weight*share*w,'REPLACE')
# Retain the original UV chart for every tangent-space normal sample.
for obj in (upper,bpy.data.objects['WitchRebuilt_Lining']):
    uv0=obj.data.uv_layers[0];uv1=obj.data.uv_layers[1]
    for i in range(len(uv0.data)):uv1.data[i].uv=uv0.data[i].uv*32.

lower=bpy.data.objects['WitchRebuilt_SimulationProxy'];old=lower.data
verts=[old.vertices[(j*2)*64+i*2].co.copy() for j in range(17) for i in range(32)]
faces=[]
for j in range(16):
    for i in range(32):
        a=j*32+i;b=j*32+(i+1)%32;c=b+32;d=a+32;faces.extend(((a,c,b),(a,d,c)))
mesh=bpy.data.meshes.new('WitchLowerProxy06');mesh.from_pydata(verts,[],faces);mesh.update()
for mat in old.materials:mesh.materials.append(mat)
lower.data=mesh;lower.vertex_groups.clear();g=lower.vertex_groups.new(name='pelvis');g.add(list(range(len(verts))),1.,'REPLACE')

up=bpy.data.objects['WitchRebuilt_UpperSimulationProxy']
for mod in list(up.modifiers):up.modifiers.remove(mod)
raw=[v.co.copy() for v in upper.data.vertices];pv=[];pf=[]
def tube(centers,axes,base_radii,samples,slices):
    offset=len(pv);radii=[];bases=[]
    for j,(center,axis) in enumerate(zip(centers,axes)):
        axis=axis.normalized();vertical=Vector((0,0,1))
        if abs(axis.dot(vertical))>.95:vertical=Vector((1,0,0))
        x=(vertical-axis*vertical.dot(axis)).normalized();y=axis.cross(x).normalized();bases.append((x,y))
        local=[]
        for p in samples:
            v=p-center;axial=v.dot(axis);radial=v-axis*axial
            if abs(axial)<.028 and .035<radial.length<.28:local.append((radial.normalized(),radial.length))
        for i in range(slices):
            radial=x*math.cos(2*math.pi*i/slices)+y*math.sin(2*math.pi*i/slices)
            values=sorted(d for n,d in local if n.dot(radial)>.97)
            radii.append(values[int((len(values)-1)*.5)] if values else base_radii[j])
    for _ in range(3):
        prev=radii[:]
        for j in range(len(centers)):
            for i in range(slices):
                k=j*slices+i;radii[k]=.55*prev[k]+.15*prev[j*slices+(i-1)%slices]+.15*prev[j*slices+(i+1)%slices]+.075*prev[max(0,j-1)*slices+i]+.075*prev[min(len(centers)-1,j+1)*slices+i]
    for j,center in enumerate(centers):
        x,y=bases[j]
        for i in range(slices):pv.append(center+(x*math.cos(2*math.pi*i/slices)+y*math.sin(2*math.pi*i/slices))*radii[j*slices+i])
    for j in range(len(centers)-1):
        for i in range(slices):
            a=offset+j*slices+i;b=offset+j*slices+(i+1)%slices;c=b+slices;d=a+slices;pf.extend(((a,b,c),(a,c,d)))

# Three deliberately regular sheets replace the non-manifold decimated proxy:
# torso/cape and two sleeves, each fixed at its attachment region.
centers=[Vector((0,.015,1.02+.56*j/14)) for j in range(15)]
tube(centers,[Vector((0,0,1))]*15,[.18]*15,[p for p in raw if abs(p.x)<.255],32)
for side in ('l','r'):
    a,b,c=[rest[n+'_'+side] for n in ('upperarm','lowerarm','hand')];l1=(b-a).length;l2=(c-b).length
    centers=[];axes=[];radii=[]
    for j in range(17):
        d=(l1+l2-.018)*j/16
        centers.append(a.lerp(b,d/l1) if d<l1 else b.lerp(c,(d-l1)/l2))
        axes.append((b-a).normalized() if d<l1 else (c-b).normalized());radii.append(.075+.025*math.sin(math.pi*j/16))
    tube(centers,axes,radii,[p for p in raw if (p.x> .19 if side=='l' else p.x<-.19)],20)
mesh=bpy.data.meshes.new('WitchUpperRegularProxy06');mesh.from_pydata(pv,[],pf);mesh.update();up.data=mesh
up.vertex_groups.clear()
for group in upper.vertex_groups:up.vertex_groups.new(name=group.name)
tree=KDTree(len(raw))
for i,p in enumerate(raw):tree.insert(p,i)
tree.balance()
for i,p in enumerate(pv):
    _,nearest,_=tree.find(p)
    for g in upper.data.vertices[nearest].groups:up.vertex_groups[g.group].add([i],g.weight,'REPLACE')
up.data.materials.clear();up.data.materials.append(bpy.data.materials.new('WitchRebuilt_UpperSimulationProxy'))
mod=up.modifiers.new('WitchRig','ARMATURE');mod.object=r;up.hide_render=True
r['surface_revision']='Surface06';r['drape_revision']='Drape06'
export(r);r.data.pose_position='POSE';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
report={'upper_vertices_before':before,'upper_vertices_after':len(upper.data.vertices),'upper_tiny_faces_removed':len(tiny),'lower_proxy_vertices':len(lower.data.vertices),'upper_proxy_vertices':len(up.data.vertices),'detail_uv':'UV0-aligned tangent frame; no per-face projection switches','actor_scale_changed':False}
(OUT/'surface06.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
