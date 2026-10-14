"""Researcher-derived horticulture workwear. Production only, no renders/tests."""
import bpy,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/EcologyGardener20261014/V01'
SOURCE=PROJECT/'SourceAssets/FacelessResearcher20261009/V05/Authoring/FacelessResearcher_V05.blend'
for folder in ('Authoring','Delivery','Textures','Logs'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['root'];body=bpy.data.objects['Researcher_CompleteBody']
coat=bpy.data.objects['Researcher_LabCoat_Continuous'];pants=bpy.data.objects['Researcher_Trousers']
display=bpy.data.objects['Researcher_OutfitBody']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0)
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])

# Reuse the existing station-workwear PBR author, not its male mesh or clothes.
tree=ast.parse((PROJECT/'Tools/CargoStationStaff/author_variants.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='material'],type_ignores=[]),'workwear_material','exec'))
mats={
    'Workwear':material('Gardener_Workwear',(.135,.18,.075),.81),
    'Apron':material('Gardener_Apron',(.115,.068,.031),.52,'rubber'),
    'Trousers':material('Gardener_Trousers',(.061,.077,.047),.85),
    'Rubber':material('Gardener_Rubber',(.035,.047,.033),.58,'rubber'),
    'Binding':material('Gardener_Binding',(.20,.15,.071),.87),
}

def dress(o,mat):
    o.data.materials.clear();o.data.materials.append(mat)
    for face in o.data.polygons:face.material_index=0

def shift(o,offset):
    if o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks:
            for v in key.data:v.co+=offset
    else:
        for v in o.data.vertices:v.co+=offset

for o in list(bpy.context.scene.objects):
    if o.type!='MESH':continue
    if o.name.startswith(('Researcher_ID','Researcher_ChestPocket','Researcher_CoatButton','Researcher_CentrePlacket')):
        bpy.data.objects.remove(o,do_unlink=True);continue
    if o.name.startswith('Researcher_HipPocket'):
        dress(o,mats['Binding' if 'Edge' in o.name else 'Apron'])
        shift(o,Vector((0,-.006,0)))
    elif o==coat:dress(o,mats['Workwear'])
    elif o==pants:dress(o,mats['Trousers'])
    elif o.name.startswith('Researcher_ClosedShoe'):dress(o,mats['Rubber'])

def surface_patch(source,name,predicate,mat,offset=.003,thickness=.0014,outer=None,leg=False):
    """Copy sewn faces and every existing corrective key with explicit vertex mapping."""
    source.data.update()
    chosen=[p for p in source.data.polygons if (outer is None or max(p.vertices)<outer) and predicate(p.center,p.normal)]
    if not chosen:raise RuntimeError('No garment surface for '+name)
    ids=sorted({i for p in chosen for i in p.vertices});index={v:i for i,v in enumerate(ids)};count=len(ids)
    normal=np.array([source.data.vertices[i].normal[:] for i in ids],dtype=np.float32)
    basis=np.array([source.data.vertices[i].co[:] for i in ids],dtype=np.float32)
    radial=basis.copy();radial[:,2]=0;radial[:,1]-=.012 if leg else .017
    if leg:radial[:,0]-=np.sign(radial[:,0])*.175
    normal[(normal*radial).sum(axis=1)<0]*=-1
    vertices=np.vstack((basis+normal*offset,basis+normal*(offset-thickness)))
    faces=[];edges={}
    for p in chosen:
        face=tuple(index[i] for i in p.vertices)
        outward=Vector((p.center.x-(math.copysign(.175,p.center.x) if leg else 0),p.center.y-.017,0))
        if p.normal.dot(outward)<0:face=tuple(reversed(face))
        faces.append(face);faces.append(tuple(i+count for i in reversed(face)))
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)))
            if key in edges:edges[key]=None
            else:edges[key]=(a,b)
    for edge in edges.values():
        if edge:
            a,b=edge;faces.append((b,a,a+count,b+count))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices.tolist(),[],faces);mesh.update()
    result=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(result)
    result.matrix_world=source.matrix_world.copy();result.parent=source.parent
    result.matrix_parent_inverse=source.matrix_parent_inverse.copy()
    result.matrix_basis=source.matrix_basis.copy()
    for group in source.vertex_groups:result.vertex_groups.new(name=group.name)
    for j,i in enumerate(ids):
        for group in source.data.vertices[i].groups:
            result.vertex_groups[group.group].add([j,j+count],group.weight,'REPLACE')
    mod=result.modifiers.new('ResearcherSkin','ARMATURE');mod.object=rig
    if source.data.shape_keys:
        for original in source.data.shape_keys.key_blocks:
            key=result.shape_key_add(name=original.name);data=np.empty((len(source.data.vertices),3),np.float32)
            original.data.foreach_get('co',data.ravel());p=data[ids]
            key.data.foreach_set('co',np.vstack((p+normal*offset,p+normal*(offset-thickness))).ravel());key.value=0
    uv=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(p.x/.2,p.z/.2)
    dress(result,mat);result['derived_from']=source.name;result['paired_shell_vertices']=count
    return result

outer=int(coat['outer_vertex_count'])
def apron(p,n):
    width=float(np.interp(p.z,[.81,1.09,1.18,1.40],[.19,.17,.125,.103]))
    return .81<p.z<1.40 and abs(p.x)<width and p.y<-.045
surface_patch(coat,'Gardener_WaterproofApron',apron,mats['Apron'],outer=outer)
surface_patch(coat,'Gardener_ShoulderStraps',lambda p,n:1.38<p.z<1.575 and .072<abs(p.x)<.106,
              mats['Binding'],offset=.004,outer=outer)
surface_patch(coat,'Gardener_WaistBelt',lambda p,n:1.095<p.z<1.125 and abs(p.x)<.21,
              mats['Binding'],offset=.0047,outer=outer)
surface_patch(coat,'Gardener_BibPocket',lambda p,n:1.225<p.z<1.32 and abs(p.x)<.082 and p.y<-.08,
              mats['Apron'],offset=.008,outer=outer)
surface_patch(pants,'Gardener_RubberBootUppers',lambda p,n:.112<p.z<.30,
              mats['Rubber'],offset=.0035,thickness=.002,outer=len(pants.data.vertices)//2,leg=True)

# Soil contact is authored in rest space, so stains follow skinning and all FR morphs.
allmeshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body]
for o in allmeshes:
    if o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks:key.value=0
    if o==display:continue
    attr=o.data.color_attributes.get('GardenerWear') or o.data.color_attributes.new(name='GardenerWear',type='FLOAT_COLOR',domain='CORNER')
    colors=np.ones((len(o.data.loops),4),np.float32)
    for loop in o.data.loops:
        p=o.data.vertices[loop.vertex_index].co
        noise=.5+.5*math.sin(p.x*137+p.z*71)*math.sin(p.y*93-p.z*117)
        low=max(0.,1-p.z/.46);hem=max(0.,1-abs(p.z-.83)/.12)*.28
        cuffs=max(0.,(abs(p.x)-.40)/.18)*.24
        dirt=min(.86,(low*.77+hem+cuffs)*(.35+.65*noise))
        colors[loop.index]=[dirt,dirt,dirt,1]
    attr.data.foreach_set('color',colors.ravel());o.data.color_attributes.active_color=attr
    o.data.color_attributes.render_color_index=list(o.data.color_attributes).index(attr)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/EcologyGardener_V01.blend'))
keynames=sorted({key.name for o in allmeshes if o.data.shape_keys for key in o.data.shape_keys.key_blocks if key.name!='Basis'})
copies=[]
for o in allmeshes:
    copy=o.copy();copy.data=o.data.copy();bpy.context.collection.objects.link(copy);copy.hide_set(False);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT')
active=copies[0]
if not active.data.shape_keys:active.shape_key_add(name='Basis')
for name in keynames:
    if name not in active.data.shape_keys.key_blocks:active.shape_key_add(name=name)
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=active;bpy.ops.object.join();merged=bpy.context.object;merged.name='SK_EcologyGardener_V01'
bpy.ops.object.select_all(action='DESELECT');merged.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SK_EcologyGardener_V01.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
report={'source':str(SOURCE),'mesh':'SK_EcologyGardener_V01','file':'Delivery/SK_EcologyGardener_V01.fbx',
    'material_families':list(mats),'material_slots':[m.name for m in merged.data.materials],
    'triangles':sum(len(p.vertices)-2 for p in merged.data.polygons),'bones':len(rig.data.bones)+1,
    'corrective_morphs':keynames,'morph_count':len(keynames),
    'production':'Researcher V05 body, sewn skin and all FR curves; added paired-shell apron, shoulder straps, belt, bib pocket and boot uppers',
    'runtime_tested':False,'rendered':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('GARDENER_AUTHORED '+json.dumps({k:v for k,v in report.items() if k!='corrective_morphs'}),flush=True)
