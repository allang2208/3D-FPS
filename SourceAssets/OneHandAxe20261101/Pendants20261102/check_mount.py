"""User-requested static mesh penetration inspection of every pendant/pommel pair."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
FIT='--fit' in sys.argv or ((P/'FitV2/registration_receipt.json').exists() and '--original' not in sys.argv)
UE='--ue' in sys.argv
OUT=P/('FitV2/SavedMeshCheck' if UE else 'FitV2/MountCheck' if FIT else 'MountCheck20261102');OUT.mkdir(parents=True,exist_ok=True)
ROOT=P.parents[2]
catalog_path=P/'FitV2/Before/tactical-hatchet-modules.json' if '--original' in sys.argv else ROOT/'Content/ColdSteelData/tactical-hatchet-modules.json'
catalog=json.loads(catalog_path.read_text('utf-8'))
if FIT:
    fit=json.loads((P/'FitV2/fit.json').read_text('utf-8'))
    for entry in fit['parts']:
        catalog['slots']['lanyard'][entry['id']].update(mesh=entry['mesh'],location_cm=fit['location_cm'])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene

def load(path,name):
    if UE:
        before=set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(P/'FitV2/UEGeometry'/(name+'.fbx')),use_anim=False)
        added=set(bpy.data.objects)-before
        candidates=[o for o in added if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_','USP_','UCP_'))]
        obj=next((o for o in candidates if o.name.startswith(name)),candidates[0])
        bpy.context.view_layer.update()
        obj.data.transform(obj.matrix_world)
        for other in added:
            if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
        print('UE_GEOMETRY',name,'bounds_cm',[[min(v.co[i] for v in obj.data.vertices)*100 for i in range(3)],
              [max(v.co[i] for v in obj.data.vertices)*100 for i in range(3)]],flush=True)
    else:
        with bpy.data.libraries.load(str(path),link=False) as (_,target):target.objects=[name]
        obj=target.objects[0];scene.collection.objects.link(obj)
    obj.hide_render=False;obj.hide_set(False);obj.matrix_world=Matrix.Identity(4)
    return obj

def build_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])

def inside(tree,point):
    direction=Vector((.773,.577,.264)).normalized();origin=point.copy();count=0
    for _ in range(40):
        hit=tree.ray_cast(origin,direction,.5)
        if hit[0] is None:break
        count+=1;origin=hit[0]+direction*2e-7
    return count%2==1

pommels={}
for key,spec in catalog['slots']['pommel'].items():
    if 'mesh' not in spec:continue
    name=spec['mesh'].split('.')[-1]
    obj=load(P.parent/'ModulesV1/TacticalHatchet_Modules_Editable.blend',name)
    pommels[key]=obj
pendants={}
for key,spec in catalog['slots']['lanyard'].items():
    if 'mesh' not in spec:continue
    name=spec['mesh'].split('.')[-1]
    obj=load(P/'FitV2/TacticalHatchet_Pendants_FitV2.blend' if FIT else ROOT/'SourceAssets/KukriRefinement20261027/Kukri_Refinement_Editable.blend',name)
    loc=spec['location_cm'];obj.location=(loc[0]/100,-loc[1]/100,loc[2]/100)
    pendants[key]=obj
bpy.context.view_layer.update()
result={'scope':'Static rest geometry, all installed common pendants and pommel variants; no animation/gameplay test',
        'source':'FBX exported from saved UE StaticMesh packages' if UE else 'Actual author meshes used by saved PhysicsV1 and hatchet module FBX exports',
        'pairs':[]}
for pkey,pommel in pommels.items():
    tree=build_tree(pommel)
    for key,pendant in pendants.items():
        overlaps=tree.overlap(build_tree(pendant))
        penetrations=[];near=[]
        for v in pendant.data.vertices:
            p=pendant.matrix_world@v.co
            if p.z<-.04:continue
            nearest,normal,idx,distance=tree.find_nearest(p)
            if nearest is None:continue
            if (p-nearest).dot(normal)<-0.000025 and inside(tree,p):
                penetrations.append({'vertex':v.index,'position_cm':list(p*100),'depth_mm':distance*1000})
            if abs(p.y)<.006 and -.02<p.z<-.005:
                near.append(list(p*100))
        penetrations.sort(key=lambda r:r['depth_mm'],reverse=True)
        through=[]
        for edge in pendant.data.edges:
            a,b=[pendant.matrix_world@pendant.data.vertices[i].co for i in edge.vertices]
            if a.y*b.y<0:
                q=a.lerp(b,-a.y/(b.y-a.y))
                if -.016<q.z<-.008:through.append(q)
        entry={'pommel':pkey,'pendant':key,'intersecting_face_pairs':len(overlaps),
               'penetrating_vertices_gt_0_025mm':len(penetrations),'deepest':penetrations[:8],
               'cord_vertices_inside_pommel_thickness':len(near),'hole_midplane_edge_crossings':len(through),
               'hole_midplane_section_bounds_cm':[[min(q[i] for q in through)*100 for i in (0,2)],
                                                 [max(q[i] for q in through)*100 for i in (0,2)]] if through else None}
        result['pairs'].append(entry)
        print('PAIR',pkey,key,'crossing_faces',len(overlaps),'inside_vertices',len(penetrations),flush=True)
(OUT/'geometry_report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if '--no-render' in sys.argv:
    print('MOUNT_GEOMETRY_INSPECTION_DONE',flush=True)
    raise SystemExit(0)

def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=.5
    return m
bodymat=mat('Inspection graphite pommel',(.23,.26,.3));cordmat=mat('Inspection orange cord',(1,.22,.035))
for objects,material in [(pommels.values(),bodymat),(pendants.values(),cordmat)]:
    for obj in objects:
        obj.data.materials.clear();obj.data.materials.append(material)
        for poly in obj.data.polygons:poly.material_index=0
for obj in list(pommels.values())+list(pendants.values()):obj.hide_render=True
pommel=pommels['factory'];pendant=pendants['knife_lanyard_braid']
pommel.hide_render=pendant.hide_render=False
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Inspection world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.13,.13,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for pos,power,size in [((.03,-.07,.04),.18,.08),((-.04,.06,-.02),.12,.06)]:
    data=bpy.data.lights.new('Area','AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new('Area',data);scene.collection.objects.link(obj);obj.location=pos;aim(obj,(0,0,-.02))
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam)
scene.camera=cam;data.type='ORTHO';data.ortho_scale=.048;data.clip_start=.001;data.clip_end=10
target=(.002,0,-.021)
for name,pos in [('front',(.002,-.15,-.021)),('oblique',(.065,-.13,-.055)),('back',(-.045,.15,-.035))]:
    cam.location=pos;aim(cam,target);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Mount_Inspection.blend'))
print('MOUNT_INSPECTION_DONE',flush=True)
