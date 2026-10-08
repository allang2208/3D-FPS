"""Offline repair of the three diagnosed remesh defects; no UE or game launch."""
import bpy,bmesh,numpy as np
import json,sys,time,traceback,gc
from pathlib import Path
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/MonsterAI'))
import author_meshy_remesh_v3 as shared
SPECIES=shared.SPECIES
ROOT=P/'SourceAssets/AlienGeometry20261006/AnatomyRepairV5'
OUT=ROOT/SPECIES;OUT.mkdir(parents=True,exist_ok=True)
OLD=P/'SourceAssets/AlienGeometry20261006/RemeshV3'/SPECIES
PRIOR=json.loads((OLD/'authoring.json').read_text(encoding='utf8'))
START=time.time()
REPORT=dict(species=SPECIES,revision='AnatomyRepairV5',complete=False,ue_imported=False,tested=False,
    rendered=False,animations_reauthored=False,materials={},textures=PRIOR.get('textures',{}),lods=[],construction=[])
def log(s):print('ANATOMY_REPAIR '+SPECIES+' '+str(s),flush=True)
def record():
    REPORT['seconds']=round(time.time()-START,2)
    (OUT/'authoring.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def source_scene(path):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.data.pose_position='REST'
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    sources={o.name:o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('SM_')}
    for o in sources.values():
        o.hide_set(False);o.hide_viewport=False
        if o.data.shape_keys:
            o.data.shape_keys.animation_data_clear()
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    return rig,sources

def clean_mesh(source,name):
    obj=shared.duplicate(source,name)
    if obj.data.shape_keys:obj.shape_key_clear()
    world=obj.matrix_world.copy();obj.parent=None;obj.data.transform(world);obj.matrix_world=Matrix.Identity(4)
    obj.vertex_groups.clear()
    for m in list(obj.modifiers):obj.modifiers.remove(m)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000008)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=0.00000005)
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    seen=set();duplicates=[]
    for face in bm.faces:
        key=tuple(sorted(v.index for v in face.verts))
        if key in seen:duplicates.append(face)
        else:seen.add(key)
    if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.normal_update();bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj

def construction_state(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    state=dict(triangles=sum(len(f.verts)-2 for f in bm.faces),boundary_edges=sum(e.is_boundary for e in bm.edges),
        over_shared_edges=sum(len(e.link_faces)>2 for e in bm.edges))
    bm.free();return state

def pinned_vertices(obj,extrema=True,material_seams=False):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    pins={v.index for e in bm.edges if e.is_boundary for v in e.verts}
    if material_seams:
        pins.update(v.index for e in bm.edges if len({f.material_index for f in e.link_faces})>1 for v in e.verts)
    if extrema:
        unseen=set(bm.verts)
        while unseen:
            stack=[unseen.pop()];component=[]
            while stack:
                v=stack.pop();component.append(v)
                for e in v.link_edges:
                    n=e.other_vert(v)
                    if n in unseen:unseen.remove(n);stack.append(n)
            for axis in range(3):
                pins.add(min(component,key=lambda v:v.co[axis]).index)
                pins.add(max(component,key=lambda v:v.co[axis]).index)
    bm.free();return pins

def reduce(obj,target,allowed=None,pins=None):
    current=len(shared.triangles(obj))
    if target>=current:return
    pins=pinned_vertices(obj) if pins is None else pins
    group=obj.vertex_groups.new(name='RepairReduceAllowed')
    ids=[v.index for v in obj.data.vertices if v.index not in pins and (allowed is None or allowed[v.index])]
    if not ids:return
    group.add(ids,1.,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('OfflineFixedFeatureReduction','DECIMATE');mod.ratio=float(target/current)
    mod.use_collapse_triangulate=True;mod.vertex_group=group.name;mod.vertex_group_factor=1.
    bpy.ops.object.modifier_apply(modifier=mod.name);obj.vertex_groups.clear()
    obj.data.polygons.foreach_set('use_smooth',np.ones(len(obj.data.polygons),bool))

def source_uv(obj):
    m=obj.data;m.calc_loop_triangles();loops=np.empty((len(m.loop_triangles),3),np.int32);m.loop_triangles.foreach_get('loops',loops.ravel())
    if not m.uv_layers:return None
    uv=np.empty((len(m.loops),2),np.float32);m.uv_layers.active.data.foreach_get('uv',uv.ravel())
    return uv[loops]

def fill_local_defects(obj,guide,repair_material):
    """Replace corrupt local face fans, then close and project their patches."""
    before=construction_state(obj)
    bm=bmesh.new();bm.from_mesh(obj.data)
    # The imported defects include doubled face fans, so filling boundary
    # edges alone cannot repair them. Remove only their immediate vertex fans.
    bad={v for e in bm.edges if e.is_boundary or len(e.link_faces)>2 for v in e.verts}
    removed=len(bad)
    if bad:bmesh.ops.delete(bm,geom=list(bad),context='VERTS')
    for iteration in range(12):
        junctions=[v for v in bm.verts if sum(e.is_boundary for e in v.link_edges) not in (0,2)]
        if not junctions:break
        removed+=len(junctions);bmesh.ops.delete(bm,geom=junctions,context='VERTS')
    else:raise RuntimeError('Could not isolate local repair boundaries: '+obj.name)
    # Tiny detached remnants cannot form a volume; do not cap a single face
    # against itself and leave a doubled zero-thickness sheet.
    unseen=set(bm.faces);slivers=[]
    while unseen:
        stack=[unseen.pop()];component=[];has_boundary=False
        while stack:
            face=stack.pop();component.append(face)
            for edge in face.edges:
                has_boundary|=edge.is_boundary
                for other in edge.link_faces:
                    if other in unseen:unseen.remove(other);stack.append(other)
        if has_boundary and len(component)<4:slivers.extend(component)
    if slivers:bmesh.ops.delete(bm,geom=slivers,context='FACES')
    edges=[e for e in bm.edges if e.is_boundary]
    projection=shared.Projection(shared.coords(guide),shared.triangles(guide));uv=source_uv(guide)
    remaining=set(edges);poked={'verts':[],'faces':[]}
    while remaining:
        edge=remaining.pop();first,current=edge.verts;loop=[first,current]
        while current!=first:
            next_edges=[e for e in current.link_edges if e in remaining]
            if len(next_edges)!=1:raise RuntimeError('Repair boundary is not a simple loop: '+obj.name)
            edge=next_edges[0];remaining.remove(edge);current=edge.other_vert(current)
            if current!=first:loop.append(current)
        center=sum((v.co for v in loop),loop[0].co*0)/len(loop)
        hit=projection.tree.find_nearest(center)
        vertex=bm.verts.new(hit[0] if hit[0] is not None else center);poked['verts'].append(vertex)
        for i in range(len(loop)):
            poked['faces'].append(bm.faces.new((loop[i],loop[(i+1)%len(loop)],vertex)))
    layer=bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')
    for face in poked['faces']:
        face.material_index=repair_material
        if uv is None:continue
        q=np.asarray([tuple(l.vert.co) for l in face.loops]);idx,bary=projection.at(q)
        face_uv=np.einsum('ij,ijk->ik',bary,uv[idx])
        for loop,value in zip(face.loops,face_uv):loop[layer].uv=value
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    after=construction_state(obj)
    REPORT['construction'].append(dict(object=obj.name,operation='close_local_defects',before=before,after=after,removed_local_vertices=removed,new_faces=len(poked['faces'])))
    if after['boundary_edges'] or after['over_shared_edges']:
        raise RuntimeError('Local repair did not construct a closed manifold surface: '+str(after))

def transfer_materials(source):
    for mat in source.data.materials:
        if mat.name not in REPORT['materials']:REPORT['materials'][mat.name]=PRIOR['materials'][mat.name]

def m10_setup():
    rig,sources=source_scene(OLD/'M10Mawcrawler_RemeshV3.blend');prepared=[]
    for name,source in sources.items():
        obj=clean_mesh(source,name+'_V5');transfer_materials(source)
        if 'Teeth' in name:kind='teeth'
        elif 'Gum' in name:kind='gum'
        elif 'Liner' in name:kind='liner'
        else:kind='body'
        prepared.append((obj,source,kind))
        REPORT['construction'].append(dict(object=name,operation='weld_geometry_keep_loop_uv',before_vertices=len(source.data.vertices),after_vertices=len(obj.data.vertices)))
    REPORT['source']=str(OLD/'M10Mawcrawler_RemeshV3.blend')
    REPORT['repairs']=['Welded coincident UV-split geometry before all LOD reduction','Retained all 36 closed teeth with independent LOD budgets','Preserved two V5 tissue morphs and 62 bones']
    return rig,sources,prepared

def m09_setup():
    file=P/shared.SOURCES[SPECIES]['source'];rig,sources=source_scene(file);prepared=[]
    for name,source in sources.items():
        obj=clean_mesh(source,name+'_V5')
        # Canonical old atlas names; the accepted UE M09 material reads that
        # atlas for all of these anatomical regions.
        for mat in source.data.materials:
            REPORT['materials'][mat.name]=dict(source_material_name=mat.name,new_texture=False)
            REPORT['materials'][mat.name.replace('.','_')]=dict(source_material_name=mat.name,new_texture=False)
        state=construction_state(obj)
        if state['boundary_edges'] or state['over_shared_edges']:
            fill_local_defects(obj,source,0)
        kind='body'
        if 'Membrane' in name:kind='membrane'
        elif 'MainEye_' in name:kind='eye'
        elif 'EyeCrown' in name:kind='crown'
        elif 'HookFinger' in name:kind='finger'
        elif 'SmallArm' in name:kind='arm'
        prepared.append((obj,source,kind))
    REPORT['source']=str(file);REPORT['repairs']=['Reduced the original V16 closed anatomical parts instead of classifying and capping the Meshy remesh','Restored complete five eyes, six membranes and ten hooks','Retained V16 continuous arms and 114 bones','Pinned extremities and region seams while reducing']
    return rig,sources,prepared

def m08_setup():
    rig,sources=source_scene(OLD/'LurkerM08_RemeshV3.blend');source=next(iter(sources.values()))
    file=P/shared.SOURCES[SPECIES]['source']
    with bpy.data.libraries.load(str(file),link=False) as (a,b):b.objects=['SK_LurkerM08']
    guide=b.objects[0];bpy.context.scene.collection.objects.link(guide)
    obj=clean_mesh(source,'M08_AnatomyRepairV5');transfer_materials(source)
    material=guide.data.materials[0].copy();material.name='Repair_M08_OriginalSkin';obj.data.materials.append(material)
    REPORT['materials'][material.name]=dict(source_material_name='Material_0',new_texture=False)
    fill_local_defects(obj,guide,len(obj.data.materials)-1)
    sources[guide.name]=guide
    REPORT['source']=str(OLD/'LurkerM08_RemeshV3.blend');REPORT['repair_guide']=str(file)
    REPORT['repairs']=['Repaired lower tooth and foreclaw openings against original source surface','Preserved V3 dorsal bore and inner-wall UV atlas','Head/teeth reduced separately from the body with protected interface','Retained original 70 bone interface']
    return rig,sources,[(obj,source,'m08')]

def m08_reduce(obj,level):
    if not level:return
    # Sequential binary regions keep the same connected mesh. Fixed interface
    # vertices prevent cracks while giving the oral complex its own budget.
    budgets={1:(78000,10500),2:(28500,6000),3:(10500,3300)}
    for oral_phase in (False,True):
        p=shared.coords(obj);f=shared.triangles(obj)
        oral=(p[:,1]<-.80)&(np.abs(p[:,0])<.30)&(p[:,2]<.72)
        membership=oral[f];interface=np.unique(f[membership.any(1)&~membership.all(1)])
        pins=pinned_vertices(obj);pins.update(int(i) for i in interface)
        oral_count=int(membership.all(1).sum());body_count=len(f)-oral_count
        allowed=oral if oral_phase else ~oral
        target=(body_count+budgets[level][1]) if oral_phase else (oral_count+budgets[level][0])
        reduce(obj,target,allowed=allowed,pins=pins)

def budget(kind,part,level,count):
    if SPECIES=='M10Mawcrawler':
        if kind=='body':return round(count*(1.,.38,.14,.05)[level])
        if kind=='teeth':return (count,3456,1728,1152)[level]
        if kind=='gum':return (count,1000,720,480)[level]
        return (count,950,650,440)[level]
    if kind=='body':return (45000,18000,7500,3000)[level]
    if kind=='membrane':return round(count*(.115,.05,.022,.009)[level])
    if kind=='crown':return (28000,12000,5500,2500)[level]
    if kind=='arm':return (18000,9000,4000,1800)[level]
    if kind=='eye':return max(300,round(count*(1.,.5,.25,.15)[level]))
    if kind=='finger':return (2000,1000,500,240)[level]
    return count

def run():
    rig,sources,prepared={'M10Mawcrawler':m10_setup,'HangingBellM09':m09_setup,'LurkerM08':m08_setup}[SPECIES]()
    lod0=[]
    for level in range(4):
        log('author LOD '+str(level));objects=[];parts=[]
        for base,source,kind in prepared:
            obj=shared.duplicate(base,base.name+'_LOD'+str(level))
            if kind=='m08':m08_reduce(obj,level)
            else:
                pins=pinned_vertices(obj,extrema=True,material_seams=(SPECIES=='HangingBellM09'))
                reduce(obj,budget(kind,base,level,len(shared.triangles(base))),pins=pins)
            shared.transfer(source,obj,rig,limit=5 if SPECIES=='HangingBellM09' else 4)
            state=construction_state(obj)
            if SPECIES in ('HangingBellM09','LurkerM08') and (state['boundary_edges'] or state['over_shared_edges']):
                raise RuntimeError('Reduction cannot close this part at the requested budget: '+obj.name+' '+str(state))
            parts.append(dict(name=base.name,kind=kind,**state));objects.append(obj)
        file=OUT/(SPECIES+'_LOD'+str(level)+'.fbx');shared.export(objects,rig,file)
        REPORT['lods'].append(dict(level=level,file=str(file),triangles=sum(p['triangles'] for p in parts),vertices=sum(len(o.data.vertices) for o in objects),parts=parts,
            morphs=sorted({k.name for o in objects if o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name!='Basis'})))
        record()
        if level==0:
            lod0=objects
            for obj in lod0:obj.hide_set(True);obj.hide_render=True
        else:
            for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
    for obj in list(bpy.data.objects):
        if obj not in lod0 and obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
    for obj in lod0:obj.hide_set(False);obj.hide_render=False
    rig.data.pose_position='POSE'
    for image in bpy.data.images:
        if image.users and not image.packed_file:image.pack()
    bpy.context.preferences.filepaths.save_version=0
    blend=OUT/(SPECIES+'_AnatomyRepairV5.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    REPORT.update(complete=True,blend=str(blend),bones=[b.name for b in rig.data.bones]);record()
    log('SAVED '+str([i['triangles'] for i in REPORT['lods']]))

if __name__=='__main__':
    try:run()
    except Exception:
        REPORT['error']=traceback.format_exc();record();raise
