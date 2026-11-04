"""Keep common pendant bodies; rebuild only the fixed root for the actual axe hole."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
BASE=P.parent
for d in ['Export']: (P/d).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
catalog=json.loads((ROOT/'Content/ColdSteelData/kukri-modules.json').read_text('utf-8'))
mount=json.loads((BASE/'mount.json').read_text('utf-8'))
location=list(mount['location_cm']);location[2]-=.5
hole=mount['hatchet']['holes'][0]['center_cm']
hole_x=(hole[0]-location[0])/100;hole_z=(hole[2]-location[2])/100
connector=bpy.data.materials.new('M_TacticalHatchet_PendantCord_FitV2');connector.diffuse_color=(.035,.045,.028,1)
manifest={'location_cm':location,'root_radius_mm':.75,'cut_z_cm':-1.8,'parts':[]}

def load(name):
    with bpy.data.libraries.load(str(ROOT/'SourceAssets/KukriRefinement20261027/Kukri_Refinement_Editable.blend'),link=False) as (_,dst):dst.objects=[name]
    obj=dst.objects[0];scene.collection.objects.link(obj);obj.hide_set(False);obj.hide_render=False
    obj.matrix_world=Matrix.Identity(4);return obj

def make_loop(center):
    # Rounded rectangle in YZ: top passes fully through the hole, side legs
    # stay outside both faces, and the lower join clears the pommel underside.
    r=.0023;y=.0108;z0=-.018;z1=hole_z
    corners=[(y-r,z1-r,0,90),(y-r,z0+r,-90,0),(-y+r,z0+r,180,270),(-y+r,z1-r,90,180)]
    # Clockwise closed perimeter: top-right, bottom-right, bottom-left, top-left.
    corners=[(y-r,z1-r,90,0),(y-r,z0+r,0,-90),(-y+r,z0+r,-90,-180),(-y+r,z1-r,180,90)]
    pts=[]
    for cy,cz,a,b in corners:
        for j in range(13):
            angle=math.radians(a+(b-a)*j/12);py=cy+r*math.cos(angle);pz=cz+r*math.sin(angle)
            t=max(0,min(1,(z1-pz)/(z1-z0)));px=hole_x+(center.x-hole_x)*t*t*(3-2*t)
            pts.append(Vector((px,py,pz)))
    vertices=[];faces=[];N=12;radius=.00075
    for i,p in enumerate(pts):
        tangent=(pts[(i+1)%len(pts)]-pts[(i-1)%len(pts)]).normalized()
        a=Vector((1,0,0));b=tangent.cross(a).normalized()
        for j in range(N):vertices.append(p+radius*(math.cos(2*math.pi*j/N)*a+math.sin(2*math.pi*j/N)*b))
    for i in range(len(pts)):
        for j in range(N):faces.append((i*N+j,i*N+(j+1)%N,((i+1)%len(pts))*N+(j+1)%N,((i+1)%len(pts))*N+j))
    mesh=bpy.data.meshes.new('ThroughHoleCord');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('ThroughHoleCord',mesh);scene.collection.objects.link(obj);mesh.materials.append(connector)
    for poly in mesh.polygons:poly.use_smooth=True
    # Compact knot joins both thin-cord legs to the unchanged common body.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=center)
    knot=bpy.context.object;knot.name='CordJoin';knot.scale=(.003,.002,.0021)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    knot.data.materials.append(connector)
    for poly in knot.data.polygons:poly.use_smooth=True
    return obj,knot

for key in ['knife_lanyard_braid','knife_lanyard_tassel','knife_lanyard_tag']:
    spec=catalog['slots']['lanyard'][key]
    obj=load(spec['mesh'].split('.')[-1]);original_material=obj.data.materials[0].name.split('.')[0]
    bm=bmesh.new();bm.from_mesh(obj.data)
    cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
        plane_co=(0,0,-.018),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.018)<1e-5 for v in e.verts)]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    rim=[v.co for v in obj.data.vertices if abs(v.co.z+.018)<1e-5]
    center=sum(rim,Vector())/len(rim);center.z=-.018
    obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))
    loop,knot=make_loop(center)
    bpy.ops.object.select_all(action='DESELECT')
    for part in [obj,loop,knot]:part.select_set(True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    name='SM_TacticalHatchet_'+key.removeprefix('knife_').title().replace('_','')+'_FitV2'
    obj.name=obj.data.name=name
    fbx=P/'Export'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,add_leaf_bones=False)
    manifest['parts'].append({'id':key,'object':name,'fbx':str(fbx),'source_material':spec['materials'][spec['material_slot_names'][0]],
        'mesh':'/Game/Weapons/TacticalHatchet20261101/PendantsV2/'+name+'.'+name,
        'material_slot_names':[m.name for m in obj.data.materials], 'body_cut_center_cm':list(center*100)})
    obj.hide_set(True);obj.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_Pendants_FitV2.blend'))
(P/'fit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('HATCHET_PENDANTS_FIT_AUTHORED',flush=True)
