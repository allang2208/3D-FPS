"""Read imported UE LOD0 geometry, measure contacts and render the saved assets.
Never modifies the authored blend, FBX exports, or UE packages.
"""
import bpy, json, math, statistics, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
source=json.loads((ROOT/'ue_meshes.json').read_text(encoding='utf-8'))
# Reuse the original authored material graphs, including the Meshy PBR wood.
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'apprentice_staff_modular.blend'))
wood=bpy.data.objects['SM_Staff_Base'].data.materials[0]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
objects={}; trees={}; metrics={}
def connected(o):
    # UE render vertices are split at UV and normal seams; weld positions only for this topology query.
    keys={}; ids=[]
    for v in o.data.vertices:
        key=tuple(round(c,4) for c in v.co);ids.append(keys.setdefault(key,len(keys)))
    parent=list(range(len(keys)))
    def find(i):
        while parent[i]!=i: parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[a]=b
    for p in o.data.polygons:
        vs=list(p.vertices)
        for i in vs[1:]:union(ids[vs[0]],ids[i])
    groups={}
    for i,v in enumerate(o.data.vertices):groups.setdefault(find(ids[i]),[]).append(i)
    return list(groups.values())
for row in source['meshes']:
    name=row['name'];mesh=bpy.data.meshes.new(name)
    # Reflect UE Y into Blender. UE's clockwise front-face convention becomes
    # Blender's outward winding after reflection; only texture V needs flipping.
    verts=[(v[0],-v[1],v[2]) for v in row['vertices']]
    faces=[(t[0],t[1],t[2]) for t in row['triangles']]
    mesh.from_pydata(verts,[],faces);mesh.update()
    for path in row['materials']:
        short=path.split('.')[-1];mesh.materials.append(wood if short=='M_Staff_Wood' else bpy.data.materials[short])
    uv=mesh.uv_layers.new(name='UVMap')
    for p,t in zip(mesh.polygons,row['triangles']):
        p.material_index=t[3]
        for loop in p.loop_indices:
            u,v=row['uvs'][mesh.loops[loop].vertex_index];uv.data[loop].uv=(u,1-v)
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.hide_render=True
    objects[name]=ob;trees[name]=BVHTree.FromPolygons([v.co for v in mesh.vertices],faces,all_triangles=True)
    parts=connected(ob)
    metrics[name]={'vertices':len(verts),'triangles':len(faces),'min_cm':[min(v[i] for v in verts) for i in range(3)],'max_cm':[max(v[i] for v in verts) for i in range(3)],'connected_pieces':len(parts)}
    metrics[name]['pieces']=[{'vertex_count':len(p),'min_cm':[min(verts[v][i] for v in p) for i in range(3)],'max_cm':[max(verts[v][i] for v in p) for i in range(3)]} for p in parts]

def section(name,z):
    o=objects[name];pts=[]
    for e in o.data.edges:
        a,b=[o.data.vertices[i].co for i in e.vertices]
        if (a.z-z)*(b.z-z)<=0 and abs(a.z-b.z)>1e-7:pts.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
    rs=[p.xy.length for p in pts]
    return {'z':z,'points':len(pts),'radius_min':min(rs) if rs else None,'radius_max':max(rs) if rs else None,'radius_mean':statistics.mean(rs) if rs else None}

def gap(a,b,filter_fn=lambda v:True):
    distances=[]
    for p in objects[a].data.vertices:
        if filter_fn(p.co):
            nearest=trees[b].find_nearest(p.co)
            if nearest[0] is not None:distances.append(nearest[3])
    return {'sample_count':len(distances),'min_cm':min(distances) if distances else None,'median_cm':statistics.median(distances) if distances else None,'max_cm':max(distances) if distances else None}

body='SM_Staff_Body';factory_head='SM_Staff_head_crystal_false';factory_grip='SM_Staff_grip_lining_false'
report={'units':'cm','geometry_source':'saved UE asset LOD0 exported by StaffAssemblyAudit commandlet','meshes':metrics,
        'shaft_sections':[section('SM_Staff_Base',z) for z in [-64,-10,-9.999,0,9.999,10,12,24,31,38,45,60,62,63]],'contacts':{}}
for name in objects:
    if any(s in name for s in ('shaft_rune','mana_line','tail_charm','crown')):
        report['contacts'][name+'_to_body']=gap(name,body)
for k in ['frozen_crystal','magma_core','jade_spirit_crystal','storm_core']:
    report['contacts'][k+'_to_body']=gap('SM_Staff_head_crystal_'+k,body,lambda v:v.z<62.01)
for crown in ['spike_crown','current_crown','wreath_crown','heat_crown']:
    name='SM_Staff_crown_'+crown
    report['contacts'][crown+'_ring_to_factory_head']=gap(name,factory_head,lambda v:v.z<63.7)
    report['contacts'][crown+'_ring_to_frozen_head']=gap(name,'SM_Staff_head_crystal_frozen_crystal',lambda v:v.z<63.7)
report['factory_reconstruction']={name:gap(name,'SM_Staff_Base',lambda v:all(abs(v.z-z)>.001 for z in [-10,10,62])) for name in [body,factory_head,factory_grip]}
def position_hash(name):return hashlib.sha256(json.dumps(sorted(tuple(round(c,5) for c in v.co) for v in objects[name].data.vertices)).encode()).hexdigest()
report['eagle_crit_geometry_identical']=position_hash('SM_Staff_shaft_rune_eagle_eye_rune')==position_hash('SM_Staff_shaft_rune_crit_rune')
report['surface_penetration']={}
def inside_body(point):
    direction=Vector((.963,.267,.008)).normalized();origin=point.copy();hits=0
    for _ in range(32):
        co,normal,index,distance=trees[body].ray_cast(origin,direction,1000)
        if co is None:break
        hits+=1;origin=co+direction*.0001
    return hits%2==1
for name in objects:
    if not any(s in name for s in ('shaft_rune','mana_line')):continue
    signed=[]
    for vertex in objects[name].data.vertices:
        co,normal,index,distance=trees[body].find_nearest(vertex.co)
        signed.append(-distance if inside_body(vertex.co) else distance)
    report['surface_penetration'][name]={'sample_count':len(signed),'inside_count':sum(d<-.001 for d in signed),'inside_percent':100*sum(d<-.001 for d in signed)/len(signed),'max_depth_cm':-min(signed),'max_exposed_height_cm':max(signed)}
report['pendant_to_connector_gap']={}
for key in ['ice_soul_pendant','thunder_bell','purification_vine','flame_pendant']:
    name='SM_Staff_tail_charm_'+key;o=objects[name]
    groups=connected(o);pendant=min(groups,key=lambda p:min(o.data.vertices[i].co.z for i in p))
    rod=min((p for p in groups if p!=pendant),key=lambda p:min(o.data.vertices[i].co.z for i in p))
    def group_tree(group):
        indices=set(group);faces=[list(p.vertices) for p in o.data.polygons if all(i in indices for i in p.vertices)]
        return BVHTree.FromPolygons([v.co for v in o.data.vertices],faces,all_triangles=True)
    rod_tree=group_tree(rod);pendant_tree=group_tree(pendant)
    distances=[rod_tree.find_nearest(o.data.vertices[i].co)[3] for i in pendant]+[pendant_tree.find_nearest(o.data.vertices[i].co)[3] for i in rod]
    report['pendant_to_connector_gap'][key]={'minimum_vertex_to_triangle_cm':min(distances),'pendant_max_z_cm':max(o.data.vertices[i].co.z for i in pendant),'rod_min_z_cm':min(o.data.vertices[i].co.z for i in rod)}
(ROOT/'geometry_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GEOMETRY_MEASURED',len(objects),flush=True)

# Headless inspection sheets use the actual imported triangles, not the design image.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.cycles.use_denoising=True;scene.cycles.device='CPU'
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.18,.18,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
def area(name,pos,energy,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,10))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(60,-85,150),400000,140);area('Fill',(-100,-50,30),150000,120);area('Rim',(0,80,120),350000,130)
camdata=bpy.data.cameras.new('AuditCamera');cam=bpy.data.objects.new('AuditCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.clip_start=.01;camdata.clip_end=2000
instances=[]
def assembly(x,replacements):
    names=[body];slots={'head_crystal':'false','grip_lining':'false'};slots.update(replacements)
    names += ['SM_Staff_'+s+'_'+p for s,p in slots.items() if p]
    for n in names:
        o=bpy.data.objects.new('inspection_'+n,objects[n].data);scene.collection.objects.link(o);o.location.x=x;instances.append(o)
def render(name,cases,z,height,step=18,res=(1500,700)):
    for o in instances:bpy.data.objects.remove(o,do_unlink=True)
    instances.clear()
    for i,parts in enumerate(cases):assembly((i-(len(cases)-1)/2)*step,parts)
    cam.location=(0,-220,z);cam.rotation_euler=(Vector((0,0,z))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x,scene.render.resolution_y=res
    width=max(height*res[0]/res[1],len(cases)*step)
    camdata.ortho_scale=max(width,width*res[1]/res[0])
    scene.render.filepath=str(ROOT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('AUDIT_RENDER',name,flush=True)
render('01_factory_and_four_heads',[{},*({'head_crystal':p} for p in ['frozen_crystal','magma_core','jade_spirit_crystal','storm_core'])],68,28,18,(1500,600))
render('02_crowns_on_factory_head',[{'crown':p} for p in ['spike_crown','current_crown','wreath_crown','heat_crown']],66,32,19,(1500,640))
render('03_runes_on_actual_shaft',[{'shaft_rune':p} for p in ['eagle_eye_rune','crit_rune','storm_rune']],35,40,10,(1200,1000))
render('04_factory_and_replacement_grips',[{},*({'grip_lining':p} for p in ['alloy_grip','pine_grip','sandalwood_grip'])],0,29,12,(1400,900))
render('05_tail_connections',[{'tail_charm':p} for p in ['ice_soul_pendant','thunder_bell','purification_vine','flame_pendant']],-70,24,15,(1500,750))
render('06_mana_lines',[{'mana_line':p} for p in ['chain_mana','direct_mana']],36,58,13,(850,1300))
render('07_complete_combinations',[{}, {'head_crystal':'frozen_crystal','crown':'spike_crown','shaft_rune':'eagle_eye_rune','grip_lining':'alloy_grip','tail_charm':'ice_soul_pendant','mana_line':'chain_mana'}, {'head_crystal':'storm_core','crown':'current_crown','shaft_rune':'storm_rune','grip_lining':'sandalwood_grip','tail_charm':'thunder_bell','mana_line':'direct_mana'}],0,172,25,(1150,1500))
for head in ['frozen_crystal','magma_core','jade_spirit_crystal','storm_core']:
    render('08_crowns_on_'+head,[{'head_crystal':head,'crown':c} for c in ['spike_crown','current_crown','wreath_crown','heat_crown']],68,28,19,(1500,640))
print('STAFF_GEOMETRY_AUDIT_DONE',flush=True)
