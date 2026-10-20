"""Manufacturing edges on the existing SVCH; preserve interfaces and native arms."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
O=Path(__file__).parent;B=O.parent;SRC=B.parent/'SVCHSketchfab20261017'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(B/'R5/SVCH_Refined_R5.blend'))
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST'
body=bpy.data.objects['SM_SVCH_Body'];mats=list(body.data.materials)
hold=json.loads((SRC/'Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
inventory=json.loads((SRC/'audit/measurements.json').read_text())['scene_inventory']['islands'];byid={i['id']:i for i in inventory}
report={'source':'R5 with original-source planar shells','parts':[],'arms':'untouched; runtime remains native V9','animations':'unchanged','materials':[m.name for m in mats]}
def native(v):
    g=(np.array((v[0]*100,-v[1]*100,v[2]*100))-HT)@HR
    return np.array((g[0]+18.7444,g[2],g[1]+1.5268))
def blender(p):
    q=np.array((p[0]-18.7444,p[2]-1.5268,p[1]))@HR.T+HT
    return (q[0]/100,-q[1]/100,q[2]/100)
def groups(mesh,weld=False):
    bm=bmesh.new();bm.from_mesh(mesh)
    if weld:bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    todo=set(bm.verts);result=[]
    while todo:
        seed=todo.pop();vs={seed};stack=[seed]
        while stack:
            for e in stack.pop().link_edges:
                for v in e.verts:
                    if v in todo:todo.remove(v);vs.add(v);stack.append(v)
        vs=list(vs);idx={v:i for i,v in enumerate(vs)};fs=list({f for v in vs for f in v.link_faces})
        points=np.array([native(v.co) for v in vs]);lo,hi=points.min(0),points.max(0)
        item=min(inventory,key=lambda a:np.linalg.norm(lo-a['bbox_native_units']['min'])+np.linalg.norm(hi-a['bbox_native_units']['max']))
        error=float(np.linalg.norm(lo-item['bbox_native_units']['min'])+np.linalg.norm(hi-item['bbox_native_units']['max']))
        result.append({'id':item['id'] if error<.12 else None,'error':error,'v':[tuple(v.co) for v in vs],
            'f':[[idx[v] for v in f.verts] for f in fs],'m':[f.material_index for f in fs]})
    bm.free();return result
old=groups(body.data)
with bpy.data.libraries.load(str(SRC/'Authoring/SVCH_Viewmodel.blend'),link=False) as (a,b):b.objects=['SM_SVCH_Body']
raw_ob=b.objects[0];raw={p['id']:p for p in groups(raw_ob.data,True) if p['id'] is not None}
bpy.data.objects.remove(raw_ob,do_unlink=True)
preserve={0,30,36,6,7,8,11,12,14,38,39,40,43}
round_ids={5,41,42}
def roughness(ident,material):
    if material=='SVCH_Polymer':return .52
    if material=='SVCH_Rubber':return .69
    if material=='SVCH_BarrelSteel':return .43
    label=byid.get(ident,{}).get('part','')
    if 'rail' in label:return .44
    if 'sight' in label:return .40
    if 'screw' in label or 'pin' in label or 'knob' in label:return .34
    if 'stock' in label:return .43
    if ident==15:return .36
    if 'receiver' in label:return .39
    return .40
made=[]
for number,p in enumerate(old):
    ident=p['id'];material=max(set(p['m']),key=p['m'].count);mode='preserved';width=0.
    use=p
    if ident in raw and ident not in preserve|round_ids:
        use=raw[ident];mode='source-shell bevel'
        label=byid[ident]['part'];width=.00012 if 'rail' in label else .00035 if ('receiver' in label or 'handguard' in label or ident==15) else .00018
    verts=use['v'];faces=use['f']
    if ident in round_ids:
        points=np.array([native(v) for v in p['v']]);lo,hi=points.min(0),points.max(0);c=(lo+hi)/2;r=(hi-lo)/2;n=64
        verts=[blender((c[0]+r[0]*math.cos(i*2*math.pi/n),y,c[2]+r[2]*math.sin(i*2*math.pi/n))) for y in (lo[1],hi[1]) for i in range(n)]
        faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
        mode='round original disc';width=.00018
    me=bpy.data.meshes.new('R8Part');me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me)
    if mode=='round original disc':bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.normal_update()
    if width:
        es=[e for e in bm.edges if e.is_manifold and e.calc_face_angle(0)>math.radians(40)]
        if es:bmesh.ops.bevel(bm,geom=es,offset=width,segments=3,profile=.5,affect='EDGES',clamp_overlap=True,material=material)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    collapsed=[f for f in bm.faces if f.calc_area()<5e-13]
    if collapsed:bmesh.ops.delete(bm,geom=collapsed,context='FACES_ONLY')
    bm.normal_update();layer=bm.faces.layers.float.new('R8Roughness')
    for f in bm.faces:f.smooth=True;f.material_index=material;f[layer]=roughness(ident,mats[material].name)
    for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle(math.pi)<math.radians(35)
    for mat in mats:me.materials.append(mat)
    bm.to_mesh(me);bm.free();me.update()
    ob=bpy.data.objects.new('R8Part_%03d'%number,me);bpy.context.collection.objects.link(ob);made.append(ob)
    report['parts'].append({'id':ident,'name':byid.get(ident,{}).get('part','unclassified retained shell'),'mode':mode,'bevel_mm':width*1000,'triangles':len(me.polygons)})
bpy.data.objects.remove(body,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in made:ob.select_set(True)
bpy.context.view_layer.objects.active=made[0];bpy.ops.object.join();body=made[0];body.name='SM_SVCH_Body';body.parent=rig
body.vertex_groups.new(name='WPN_root').add(list(range(len(body.data.vertices))),1,'REPLACE')
# Applied weighted normals on weapon surfaces only. Preserve the existing arms.
for ob in [x for x in bpy.context.scene.objects if x.type=='MESH' and x.name.startswith('SM_SVCH_')]:
    for mod in list(ob.modifiers):ob.modifiers.remove(mod)
    if ob==body:
        wn=ob.modifiers.new('MachinedNormals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
        bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=wn.name)
    if 'R8Roughness' not in ob.data.attributes:
        a=ob.data.attributes.new('R8Roughness','FLOAT','FACE')
        value={'Magazine':.51,'BoltCarrier':.31,'MagRelease':.36,'Selector':.35,'Cartridge':.28}.get(ob.name.removeprefix('SM_SVCH_'),.4)
        for x in a.data:x.value=value
    # Existing UV0 was anonymous tiled projection; retain a copy, create a
    # unique weapon-only bake atlas. Native arm UVs are never processed here.
    if ob.data.uv_layers:
        old_uv=ob.data.uv_layers[0];old_uv.name='UVMap'
        backup=ob.data.uv_layers.get('OriginalTiledUV') or ob.data.uv_layers.new(name='OriginalTiledUV')
        for a,b in zip(backup.data,old_uv.data):a.uv=b.uv
        ob.data.uv_layers.active_index=0
    else:ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.006,area_weight=.5,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT');ob.data.uv_layers[0].active_render=True
    ob.modifiers.new('NativeRigidBinding','ARMATURE').object=rig
report['objects']={}
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':
        ob.data.calc_loop_triangles();report['objects'][ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles)}
report['triangles']=sum(x['triangles'] for x in report['objects'].values())
(O/'model_receipt.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob==rig or ob.type=='MESH':ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_R8Surface.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_R8Surface.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
print('SVCH_R8_SOURCE_SAVED',report['triangles'],flush=True)
