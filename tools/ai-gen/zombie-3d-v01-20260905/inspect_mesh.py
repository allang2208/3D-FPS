import bpy, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'zombie-raw.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in meshes:
    world=o.matrix_world.copy()
    o.parent=None
    o.matrix_world=world
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.select_set(False)
verts=[v.co for o in meshes for v in o.data.vertices]
lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)))
hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)))
print('RAW_BOUNDS',list(lo),list(hi),flush=True)
center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
scale=1.9/(hi.z-lo.z)
for o in meshes:
    for v in o.data.vertices: v.co=(v.co-center)*scale
    for p in o.data.polygons:p.use_smooth=True
report={'raw_min':list(lo),'raw_max':list(hi),'height_m':1.9,'meshes':[]}
for o in meshes:
    parent=list(range(len(o.data.vertices)))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for e in o.data.edges:
        a,b=map(find,e.vertices);parent[a]=b
    counts={}
    for i in range(len(parent)):
        r=find(i);counts[r]=counts.get(r,0)+1
    report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'components':len(counts),'largest_component_vertex_fraction':max(counts.values())/len(parent),'materials':len(o.data.materials),'uv_layers':len(o.data.uv_layers)})
    samples={}
    for h in (.05,.2,.45,.65,.85,1.05,1.25,1.45,1.65,1.8):
        vs=[v.co for v in o.data.vertices if abs(v.co.z-h)<.025]
        if vs:samples[str(h)]={'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)]}
    report['samples']=samples
(ROOT/'mesh-inspection.json').write_text(json.dumps(report,indent=2))
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.16,.2,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
def area(name,pos,energy,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,-4,5),420,4);area('Fill',(3,-2,3),250,3);area('Rim',(1,3,4),500,3)
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=2.35
for name,pos in [('front',(0,-5,1.05)),('threequarter',(3,-5,2.1)),('back',(0,5,1.05))]:
    camera.location=pos;camera.rotation_euler=(Vector((0,0,.95))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/f'model-{name}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'zombie-model.blend'))
print(json.dumps(report),flush=True)
