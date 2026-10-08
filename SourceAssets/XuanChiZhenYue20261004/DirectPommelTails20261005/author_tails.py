"""Fit compact direct-tassel seats to six counterweights, without the copper ring.

This is asset production only. No preview rendering or gameplay testing.
All body end contacts are sampled from the original mesh surfaces.
"""
import bpy,json,math,copy
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;ROOT=P.parents[2];SRC=P.parents[1]
OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
catalog=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
library=json.loads((ROOT/'Content/ColdSteelData/shared-sword-pommels.json').read_text(encoding='utf-8-sig'))
inputs=json.loads((P.parent/'PommelTails20261005/interface_inputs.json').read_text(encoding='utf-8'))
native=P.parent/'SurfaceV2/XuanChi_SurfaceV2_Editable.blend'

def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0]
    if obj is None:raise RuntimeError('Missing original component '+name)
    scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=False
    return obj

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=obj

def join(objects,name):
    activate(objects[0])
    for obj in objects:obj.select_set(True)
    bpy.ops.object.join();obj=bpy.context.object;obj.name=name;obj.data.name=name+'_Geometry'
    return obj

def export(obj):
    activate(obj);location=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,
        mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    obj.location=location

def tree_for(obj,scale=1.):
    return BVHTree.FromPolygons([v.co*scale for v in obj.data.vertices],
        [list(f.vertices) for f in obj.data.polygons])

tail=append(native,'SM_XuanChi_Tassel')
tail.matrix_world=Matrix.Identity(4)
# Compact only the suspension loop formerly tied around the large copper ring.
# Below the first 1.5 cm, jade, beads, silk and their native UV1 weights stay exact.
mesh=tail.data;source=[v.co.copy() for v in mesh.vertices]
normals=[n.vector.copy() for n in mesh.corner_normals]
top=max(v.z for v in source);start=-.015;span=top-start;z_reduction=top-.004
normal_matrices=[]
for vertex,p in zip(mesh.vertices,source):
    t=max(0.,min(1.,(p.z-start)/span));s=t*t*(3-2*t)
    derivative=6*t*(1-t)/span if 0<t<1 else 0.
    radius_scale=1-.72*s;radius_derivative=-.72*derivative
    vertex.co=(p.x*radius_scale,p.y*radius_scale,p.z-z_reduction*s)
    jacobian=Matrix(((radius_scale,0,p.x*radius_derivative),
                     (0,radius_scale,p.y*radius_derivative),
                     (0,0,1-z_reduction*derivative)))
    normal_matrices.append(jacobian.inverted().transposed())
mesh.update()
mesh.normals_split_custom_set([(normal_matrices[l.vertex_index]@normals[l.index]).normalized() for l in mesh.loops])
dynamic_mat=tail.data.materials[0].copy();dynamic_mat.name='M_XuanChi_WeightedTassel'
tail.data.materials[0]=dynamic_mat
assembly=tail;assembly.name='SM_XuanChi_DirectTassel'
export(assembly);assembly.hide_render=True;assembly.hide_set(True)
N=96
rim=[Vector((math.cos(k*math.tau/N)*.005,math.sin(k*math.tau/N)*.004,0)) for k in range(N)]

copper=bpy.data.materials.new('M_XuanChi_TerminalCopper');copper.use_nodes=True
bs=copper.node_tree.nodes.get('Principled BSDF')
def linear(c):c=c/255.;return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
bs.inputs['Base Color'].default_value=(*(linear(c) for c in [222,157,109]),1.)
bs.inputs['Metallic'].default_value=.97;bs.inputs['Roughness'].default_value=.31
source_rows={
    'ballast_hardened':('RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_Meteor',(.019,.015)),
    'ballast_rune':('RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_JadeStar',(.010,.008)),
    'ballast_magic_orb':('RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_Swiftstar',(.009,.009)),
    'pommel_hardened':('FrostSwordPommelsRepair20260915/ballast_hardened/FrostPommel_Editable.blend','SM_FrostPommel_ballast_hardened',(.016,.012)),
    'pommel_runic':('FrostSwordPommelsRepair20260915/ballast_rune/FrostPommel_Editable.blend','SM_FrostPommel_ballast_rune',(.012,.010)),
    'pommel_mana_orb':('FrostSwordPommelsRepair20260915/ballast_magic_orb/FrostPommel_Editable.blend','SM_FrostPommel_ballast_magic_orb',(.013,.011)),
}
rows=[]
for key,(source,name,seat_radius) in source_rows.items():
    body=append(SRC/source,name);body.matrix_world=Matrix.Identity(4)
    interface=library['options'][key]['interface']
    fit=catalog['pommel_profile']['interfaces'][interface]
    scale=fit['scale'][0];body_tree=tree_for(body,scale)
    body_origin=Vector(fit['location_cm'])*.01
    adapter_origin=Vector(fit['adapter']['location_cm'])*.01
    def end_surface(x,y):
        hit,n,face,dist=body_tree.ray_cast(Vector((x,y,-.5)),Vector((0,0,1)),.55)
        if hit is None:raise RuntimeError('Terminal contact missed '+key)
        return hit,n,face
    center,_,_=end_surface(0,0)
    # Short closed copper ferrule: the red tie goes straight into its underside.
    seat_bottom=body_origin.z+center.z-.007
    tail_anchor=seat_bottom-.0037
    top=[]
    for k in range(N):
        a=k*math.tau/N
        hit,_,_=end_surface(math.cos(a)*seat_radius[0]*scale,math.sin(a)*seat_radius[1]*scale)
        p=hit+body_origin-adapter_origin;p.z+=.0006
        top.append(p)
    verts=[];faces=[];uvs=[]
    def face(ids,coords):faces.append(tuple(ids));uvs.append(coords)
    steps=14
    for j in range(steps+1):
        t=j/steps;s=t*t*(3-2*t)
        for a,b in zip(top,rim):
            end=b+Vector((0,0,seat_bottom-adapter_origin.z))
            p=a.lerp(end,s)
            # Rounded lip around the compact silk suspension knot.
            lip=.00025*math.sin(math.pi*max(0,min(1,(t-.7)/.3)))
            d=Vector((p.x,p.y,0)).normalized();p+=d*lip
            verts.append(p)
    for j in range(steps):
        for k in range(N):
            n=(k+1)%N
            ids=[j*N+k,(j+1)*N+k,(j+1)*N+n,j*N+n]
            face(ids,[(k/N,j/steps),(k/N,(j+1)/steps),((k+1)/N,(j+1)/steps),((k+1)/N,j/steps)])
    # Both closed caps sit inside their native mounting surfaces.
    face(list(range(N)),[(v.x/.05+.5,v.y/.05+.5) for v in verts[:N]])
    face(list(reversed(range(steps*N,(steps+1)*N))),[(verts[i].x/.05+.5,verts[i].y/.05+.5) for i in reversed(range(steps*N,(steps+1)*N))])

    # Four fitted copper claws carry the glass orb from its existing metal cage.
    # The paths follow the sampled outer stone and terminate in the bottom seat.
    claw_anchors=[]
    if key=='pommel_mana_orb':
        for anchor in inputs[key]['metal_cradle_anchors']:
            anchor=Vector(anchor)*scale
            angle=math.atan2(anchor.y,anchor.x);start_r=math.hypot(anchor.x,anchor.y)
            radial=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-radial.y,radial.x,0))
            points=[]
            for j in range(23):
                t=j/22;r=start_r*(1-t)+.009*t
                p,n,_=end_surface(radial.x*r,radial.y*r)
                if j==0:p=anchor
                # Negative Z offsets place the strap outside the lower shell.
                p.z-=.00035
                points.append(p+body_origin-adapter_origin)
            base=len(verts)
            for j,p in enumerate(points):
                tangent=points[min(j+1,len(points)-1)]-points[max(0,j-1)]
                normal=tangent.cross(side).normalized()
                if normal.z>0:normal.negate()
                for s,h in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                    verts.append(p+side*(s*.0016)+normal*(h*.00045))
            for j in range(len(points)-1):
                for c in range(4):
                    d=(c+1)%4
                    face([base+j*4+c,base+(j+1)*4+c,base+(j+1)*4+d,base+j*4+d],
                         [(c/4,j/22),(c/4,(j+1)/22),((c+1)/4,(j+1)/22),((c+1)/4,j/22)])
            face([base+3,base+2,base+1,base],[(0,0),(1,0),(1,1),(0,1)])
            end=base+(len(points)-1)*4
            face([end,end+1,end+2,end+3],[(0,0),(1,0),(1,1),(0,1)])
            claw_anchors.append(list((anchor+body_origin)*100))

    mesh=bpy.data.meshes.new('TerminalSeat_'+key);mesh.from_pydata(verts,[],faces);mesh.update()
    mesh.materials.append(copper);uv=mesh.uv_layers.new(name='UVMap')
    for poly,coords in zip(mesh.polygons,uvs):
        poly.use_smooth=len(poly.vertices)==4
        for loop,coord in zip(poly.loop_indices,coords):uv.data[loop].uv=coord
    seat=bpy.data.objects.new('TerminalSeat_'+key,mesh);scene.collection.objects.link(seat)
    # Add the new seat to the existing adapter draw, preserving its upper fitting.
    adapter=append(native,'SM_XuanChi_Adapter_'+interface);adapter.matrix_world=Matrix.Identity(4)
    original_mat=adapter.data.materials[0].copy();original_mat.name='M_XuanChi_ExistingMount'
    adapter.data.materials[0]=original_mat
    adapter=join([adapter,seat],'SM_XuanChi_DirectPommelMount_'+key);export(adapter)
    adapter.hide_set(True);adapter.hide_render=True
    body.hide_set(True);body.hide_render=True
    fixed=catalog['slots']['pommel']['factory']['tassel']
    capsules=copy.deepcopy(fixed['collision_capsules_cm'])
    delta=fixed['location_cm'][2]-tail_anchor*100
    for capsule in capsules:capsule[2]+=delta;capsule[5]+=delta
    radius=max(math.hypot(v.co.x,v.co.y) for v in body.data.vertices)*scale*100
    # Keep the capsule's lower surface above the suspension root. The former
    # ring gave 8 cm of clearance; using its old oversized capsule would push
    # the first tassel segment out of this new direct attachment.
    lower=(body_origin.z+center.z-tail_anchor)*100+radius+.15
    upper=max(lower,(body_origin.z-tail_anchor)*100-radius)
    capsules.append([0,0,upper,0,0,lower,radius])
    rows.append({'option':key,'adapter_mesh':adapter.name,'interface':interface,
        'adapter_location_cm':fit['adapter']['location_cm'],
        'seat_bottom_location_cm':[0,0,seat_bottom*100],
        'tassel_location_cm':[0,0,tail_anchor*100],
        'guides_cm':fixed['guides_cm'],'collision_capsules_cm':capsules,
        'sampled_end_cap_cm':list((center+body_origin)*100),
        'cradle_metal_anchors_cm':claw_anchors,
        'adapter_triangles':sum(len(f.vertices)-2 for f in adapter.data.polygons)})

assembly.hide_set(False);assembly.hide_render=False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_DirectPommelTails_Editable.blend'))
manifest={'revision':'XuanChiDirectPommelTails20261005','tail_mesh':assembly.name,
    'tail_triangles':sum(len(f.vertices)-2 for f in assembly.data.polygons),
    'tail_material_slots':[m.name for m in assembly.data.materials],
    'modified_pommel_rings_removed':True,'native_tassel_uv1_preserved':True,
    'suspension_loop_compacted':True,'jade_beads_and_silk_below_1_5_cm_unchanged':True,
    'shared_pommel_bodies_unchanged':True,'options':rows,'game_tested':False}
(P/'exports.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_DIRECT_POMMEL_TAILS_AUTHORED '+json.dumps({'mesh':assembly.name,'options':len(rows)}),flush=True)
