"""Round the exposed extension and floorplate while retaining the insertion end."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
PREV=S/'M1911ExtendedMagazine20260927';auth=json.loads((PREV/'authoring.json').read_text());root=Matrix(auth['root_matrix'])
bpy.ops.wm.open_mainfile(filepath=str(PREV/'M1911_ExtendedMagazine_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
ob=bpy.data.objects['SM_M1911_ext_mag'];ob.hide_set(False);ob.data.transform(root.inverted())
def select(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
def key(p,uv):return tuple(round(v,7) for v in (*p,*uv))
original={}
for p in ob.data.polygons:
    for li in p.loop_indices:
        v=ob.data.vertices[ob.data.loops[li].vertex_index].co
        if v.z>=-.0839:original[key(v,ob.data.uv_layers[0].data[li].uv)]=ob.data.corner_normals[li].vector.copy()

# The old extension was joined as two objects. Weld only its lower seam so the
# fillet crosses the new band without leaving duplicated edge normals.
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if v.co.z<-.0839],dist=1e-7)
bm.normal_update();bm.to_mesh(ob.data);bm.free();ob.data.update()
weights=ob.data.attributes.get('bevel_weight_edge') or ob.data.attributes.new('bevel_weight_edge','FLOAT','EDGE')
bm=bmesh.new();bm.from_mesh(ob.data);bm.edges.ensure_lookup_table();count=0
for e in bm.edges:
    exposed=max(v.co.z for v in e.verts)<-.0839
    hard=e.is_manifold and e.calc_face_angle(0)>math.radians(22)
    # Keep the small stamping and internal feed/catch geometry untouched.
    eligible=exposed and hard and e.calc_length()>.002
    weights.data[e.index].value=1 if eligible else 0
    if eligible:count+=1
bm.free();select(ob)
bevel=ob.modifiers.new('Exposed magazine edge fillets 0.65mm','BEVEL')
bevel.limit_method='WEIGHT';bevel.width=.00065;bevel.segments=5;bevel.profile=.5
bevel.use_clamp_overlap=True;bevel.harden_normals=True
bpy.ops.object.modifier_apply(modifier=bevel.name)

# Smooth only the new exposed region. The unchanged insertion section retains
# its authored UV and corner-normal values, including its sharp feed geometry.
for p in ob.data.polygons:
    if max(ob.data.vertices[i].co.z for i in p.vertices)<-.0839:p.use_smooth=True
select(ob);weighted=ob.modifiers.new('Lower shell broad-face normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=40
bpy.ops.object.modifier_apply(modifier=weighted.name)
normals=[n.vector.copy() for n in ob.data.corner_normals]
for p in ob.data.polygons:
    for li in p.loop_indices:
        v=ob.data.vertices[ob.data.loops[li].vertex_index].co;k=key(v,ob.data.uv_layers[0].data[li].uv)
        if v.z>=-.0839 and k in original:normals[li]=original[k]
ob.data.normals_split_custom_set(normals)
ob.data.transform(root);ob.name='SM_M1911_ext_mag_Rounded20260927'
select(ob);tri=ob.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_RoundedMagazine_Editable.blend'))
group=bpy.data.objects.new('SM_M1911_ext_mag_Rounded20260927',None);bpy.context.collection.objects.link(group);group['fbx_type']='LodGroup'
ob.name='SM_M1911_ext_mag_Rounded20260927_LOD0';ob.parent=group;levels=[ob]
for i,ratio in [(1,.5),(2,.2)]:
    part=ob.copy();part.data=ob.data.copy();part.name='SM_M1911_ext_mag_Rounded20260927_LOD'+str(i);bpy.context.collection.objects.link(part)
    select(part);dec=part.modifiers.new('Distant detail reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=dec.name);levels.append(part)
select(group)
for part in levels:part.select_set(True)
fbx=E/'SM_M1911_ext_mag_Rounded20260927.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
 bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,use_custom_props=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_RoundedMagazine_LODs.blend'))
record={'source':str(PREV/'M1911_ExtendedMagazine_Editable.blend'),'fbx':str(fbx),'root_matrix':auth['root_matrix'],
 'old_asset':auth['mesh'],'asset':auth['mesh'],
 'fillet_width_m':.00065,'fillet_segments':5,'authored_edges':count,'preserved_above_z_m':-.0839,
 'lods':[len(p.data.polygons) for p in levels],'materials':[m.name for m in ob.data.materials],
 'policy':'Original insertion end, capacity, extension length, UVs, material bindings and reload attachment frame retained','game_tested':False}
(O/'magazine_authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('M1911_ROUNDED_MAGAZINE_AUTHORED '+str(count)+' edges',flush=True)
