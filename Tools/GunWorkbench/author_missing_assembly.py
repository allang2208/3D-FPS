"""Derive assembly meshes from installed rigid weapon groups; preserve UVs/normals."""
import bpy,json,math,collections
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

P=Path('D:/FPS3D/FPSGAME');ROOT=Path(globals().get('ASSEMBLY_ROOT', P/'SourceAssets/GunAssemblyCompletion20261015'))
SOURCES=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))['weapons']
DEST='/Game/Building/'+ROOT.name
# Costs follow the existing rifle, pistol and heavy-revolver material tiers.
SPECS={
 'hk416':([('stock','枪托'),('grip','握把'),('magazine','弹匣'),('muzzle','枪口件'),('bolt','枪机组件')],[14,5,2],5),
 'super90':([('stock','枪托'),('grip','握把'),('barrel','枪管组件'),('bolt','枪机组件'),('trigger','扳机')],[16,5,2],5.5),
 'g18':([('slide','套筒'),('barrel','枪管'),('magazine','弹匣'),('trigger','扳机')],[6,3,1],4),
 'pit_viper2011':([('slide','套筒'),('barrel','枪管'),('magazine','弹匣'),('hammer','击锤'),('trigger','扳机')],[8,3,1],4.5),
 'rsh12':([('cylinder','弹巢组件'),('grip','握把'),('trigger','扳机'),('hammer','击锤')],[12,4,2],5),
 'saiga12k':([('stock','枪托'),('grip','握把'),('magazine','弹匣'),('bolt','枪机组件'),('barrel','枪管组件')],[18,0,2],5.5),
 'svch':([('stock','枪托'),('magazine','弹匣'),('bolt','拉机组件'),('barrel','枪管组件'),('trigger','扳机')],[20,0,3],6)}

def classify(key,slot,bone):
    s=slot.lower();b=bone.lower()
    if any(t in b for t in ['new_','wpn_bullet','wpn_case','wpn_round','wpn_loader','wpn_shell']):return None
    if key=='super90' and '12gauge' in s:return None # Both the cycling shell and matchsaver round are ammo.
    if key=='hk416':
        if 'factorystock' in s:return 'stock'
        if 'factoryreargrip' in s:return 'grip'
        if 'magazine' in s:return 'magazine'
        if 'factorymuzzle' in s:return 'muzzle'
        if b in ['wpn_bolt','wpn_charginghandle']:return 'bolt'
    elif key=='super90':
        if 'factorystock' in s:return 'stock'
        if 'factoryreargrip' in s:return 'grip'
        if s=='s90_barrelsteel':return 'barrel'
        if b=='wpn_bolt':return 'bolt'
        if b=='wpn_trigger':return 'trigger'
    elif key in ['g18','pit_viper2011']:
        if b=='wpn_slide':return 'slide'
        if b=='wpn_barrel':return 'barrel'
        if b=='wpn_socket_magazine':return 'magazine'
        if b=='wpn_trigger':return 'trigger'
        if b=='wpn_hammer' and key=='pit_viper2011':return 'hammer'
    elif key=='rsh12':
        if b in ['wpn_cylinder','wpn_crane','wpn_extractor']:return 'cylinder'
        if b=='wpn_hammer':return 'hammer'
        if b=='wpn_trigger':return 'trigger'
        if 'factorygrip' in s:return 'grip'
    elif key=='saiga12k':
        if s in ['saiga12k_shellbrass','saiga12k_shellplastic']:return None
        if s in ['saiga12k_stock','saiga12k_stockpad']:return 'stock'
        if s=='saiga12k_reargrip':return 'grip'
        if b=='wpn_socket_magazine':return 'magazine'
        if b=='wpn_bolt':return 'bolt'
        if s=='saiga12k_barrel':return 'barrel'
    elif key=='svch':
        if s.startswith('bullet_'):return None
        if s=='kvinhibitor_stock':return 'stock'
        if b=='wpn_socket_magazine':return 'magazine'
        if b=='wpn_bolt':return 'bolt'
        if b=='wpn_trigger':return 'trigger'
        if s=='kvinhibitor_barrel':return 'barrel'
    return 'body'

def bounds(points):
    a=np.asarray(points);return Vector(a.min(axis=0)),Vector(a.max(axis=0))

def subset_object(source,faces,name,transform,material_paths):
    """Copy only complete authored faces and all corner UV/normal data."""
    original=source.data
    ids=sorted({v for f in faces for v in f.vertices});remap={v:i for i,v in enumerate(ids)}
    flip=transform.determinant()<0
    ordered=[list(reversed(f.loop_indices)) if flip else list(f.loop_indices) for f in faces]
    loops=[i for ls in ordered for i in ls]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([transform@original.vertices[v].co for v in ids],[],
        [[remap[original.loops[i].vertex_index] for i in ls] for ls in ordered])
    used=sorted({f.material_index for f in faces});indices={m:i for i,m in enumerate(used)}
    for m in used:mesh.materials.append(original.materials[m])
    for dst,src in zip(mesh.polygons,faces):dst.material_index=indices[src.material_index];dst.use_smooth=src.use_smooth
    for layer in original.uv_layers:
        uv=mesh.uv_layers.new(name=layer.name)
        values=np.empty(len(layer.data)*2,dtype=np.float32);layer.data.foreach_get('uv',values)
        uv.data.foreach_set('uv',values.reshape(-1,2)[loops].ravel())
    for layer in original.color_attributes:
        if layer.domain not in ['POINT','CORNER']:continue
        color=mesh.color_attributes.new(name=layer.name,type=layer.data_type,domain=layer.domain)
        values=np.empty(len(layer.data)*4,dtype=np.float32);layer.data.foreach_get('color',values)
        color.data.foreach_set('color',values.reshape(-1,4)[ids if layer.domain=='POINT' else loops].ravel())
    normals=np.empty(len(original.corner_normals)*3,dtype=np.float32);original.corner_normals.foreach_get('vector',normals)
    n=normals.reshape(-1,3)[loops]@np.asarray(transform.to_3x3().inverted().transposed()).T
    n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
    mesh.normals_split_custom_set(n.tolist());mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    return obj

catalog=[];all_manifest=[]
for source in SOURCES:
    key=source['key'];spec,cost,duration=SPECS[key]
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Sources'/(key+'.blend')))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    root_world=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;root_inverse=root_world.inverted()
    material_paths={};groups=collections.defaultdict(list)
    for obj in list(bpy.context.scene.objects):
        if obj.type!='MESH':continue
        if len(obj.data.materials)!=len(source['materials']):raise RuntimeError(key+': source material-slot order differs')
        for i,row in enumerate(source['materials']):
            mat=obj.data.materials[i];mat.name='GA_'+key+'_'+str(i).zfill(2)
            material_paths[mat.name]=row['asset']
        labels={g.index:g.name for g in obj.vertex_groups}
        dominant={v.index:labels[max(v.groups,key=lambda g:g.weight).group] if v.groups else '' for v in obj.data.vertices}
        weapon_bones={'WPN_root'}|{b.name for b in rig.data.bones if any(p.name=='WPN_root' for p in b.parent_recursive)}
        by_group=collections.defaultdict(list)
        for f in obj.data.polygons:
            bone=collections.Counter(dominant[v] for v in f.vertices).most_common(1)[0][0]
            if bone not in weapon_bones:continue
            group=classify(key,source['materials'][f.material_index]['slot'],bone)
            if group is not None:by_group[group].append(f)
        for group,faces in by_group.items():groups[group].append((obj,faces,root_inverse@obj.matrix_world))
    expected={'body'}|{g for g,_ in spec}
    if set(groups)!=expected:raise RuntimeError(key+': unexpected mechanical groups '+str(set(groups)^expected))
    # All pieces share one rigid frame. Never independently rescale mating parts.
    points=[matrix@obj.data.vertices[v].co for entries in groups.values() for obj,faces,matrix in entries for v in {v for f in faces for v in f.vertices}]
    low,high=bounds(points);axes=sorted(range(3),key=lambda a:high[a]-low[a])
    rot=Matrix([[float(i==axes[1]) for i in range(3)],[float(i==axes[2]) for i in range(3)],[float(i==axes[0]) for i in range(3)]])
    if rot.determinant()<0:rot[0]=-rot[0]
    rot=rot.to_4x4();low,high=bounds([rot@p for p in points])
    # Long rifles must remain within the existing mat/drag limits; uniformly fit the whole assembly.
    scale=min(1.,1.14/(high.y-low.y),.39/(high.x-low.x))
    flat=Matrix.Scale(scale,4)@rot;low,high=bounds([flat@p for p in points])
    frame=Matrix.Translation(Vector((.82-(low.x+high.x)/2,-(low.y+high.y)/2,.97-low.z)))@flat
    out=ROOT/'Authored'/key;out.mkdir(parents=True,exist_ok=True)
    recipe={'id':'assemble_'+key,'output':source['definition'],'inputs':[{'item':k,'count':n} for k,n in zip(['ironIngot','copperIngot','wood'],cost)],
        'camera':[20,0,215],'look_at':[75,0,99],'position_tolerance_cm':4 if key in ['g18','pit_viper2011','rsh12'] else 5,
        'angle_tolerance_deg':18,'calibration_seconds':duration,'parts':[]}
    recipe['inputs'].append({'item':'search_assembly_component_box','count':2 if key in ['hk416','super90','rsh12','saiga12k','svch'] else 1})
    if key in ['rsh12','svch']:recipe['inputs'].append({'item':'search_precision_mechanism','count':1})
    created=[];manifest={'key':key,'source_mesh':source['source_mesh'],'uniform_display_scale':scale,'meshes':[]}
    for group,label in [('body','枪身')]+spec:
        pieces=[]
        for i,(obj,faces,matrix) in enumerate(groups[group]):
            pieces.append(subset_object(obj,faces,f'{key}_{group}_{i}',frame@matrix,material_paths))
        bpy.ops.object.select_all(action='DESELECT')
        for obj in pieces:obj.select_set(True)
        bpy.context.view_layer.objects.active=pieces[0]
        if len(pieces)>1:bpy.ops.object.join()
        obj=pieces[0];name='SM_GA_'+key+'_'+group;obj.name=name;obj.data.name=name
        lo,hi=bounds([v.co for v in obj.data.vertices]);center=(lo+hi)*.5;extent=(hi-lo)*50
        mirror=Matrix.Diagonal((1,-1,1,1));obj.data.transform(mirror@Matrix.Translation(-center));obj.data.flip_normals()
        tri=obj.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
        path=DEST+'/'+key+'/'+name;fbx=out/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
            mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
        manifest['meshes'].append({'name':name,'path':path,'fbx':str(fbx),'group':group,'triangles':len(obj.data.polygons),
            'materials':{m.name:material_paths[m.name] for m in obj.data.materials},'extent_cm':list(extent)})
        if group=='body':recipe['body_mesh']=path;recipe['body_position']=list(center*100)
        else:recipe['parts'].append({'id':group,'name':label,'mesh':path,'target':list(center*100),'extent':list(extent),
            'loose':[59,0,95.3+extent.z],'angle':0,'radius':max(3.5,min(extent.x,extent.y)+1.5)})
        created.append(obj)
    # Two side lanes; long pieces get a shallow starting turn to prevent overlap.
    lanes=[[],[]]
    for i,part in sorted(enumerate(recipe['parts']),key=lambda p:p[1]['extent'][1],reverse=True):
        lane=min(range(2),key=lambda n:sum(p['span'] for p in lanes[n]))
        ex,ey,_=part['extent'];angle=15 if ey>12 else [35,-40,55,-30,45,-50][i]
        if lane:angle=-angle
        span=2*(abs(ex*math.sin(math.radians(angle)))+abs(ey*math.cos(math.radians(angle))))+5
        lanes[lane].append({'part':part,'span':span,'angle':angle})
    for lane,entries in enumerate(lanes):
        total=sum(e['span'] for e in entries)
        if total>118:raise RuntimeError(key+': loose part lane is larger than the work mat')
        y=-total/2
        for e in entries:
            part=e['part'];part['angle']=e['angle'];part['loose']=[57 if lane==0 else 110,y+e['span']/2,part['loose'][2]];y+=e['span']
    for obj in list(bpy.data.objects):
        if obj not in created:bpy.data.objects.remove(obj,do_unlink=True)
    # Editable objects display the assembled placement; exported assets keep local centres.
    positions={'body':recipe['body_position']}|{p['id']:p['target'] for p in recipe['parts']}
    for obj,entry in zip(created,manifest['meshes']):
        pos=positions[entry['group']];obj.location=Vector((pos[0],-pos[1],pos[2]))*.01
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(key+'_Assembly.blend')))
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8')
    catalog.append(recipe);all_manifest.append(manifest)
    print('ASSEMBLY_WEAPON_AUTHORED',key,'parts',len(recipe['parts']),'scale',scale,flush=True)
(ROOT/'recipes.json').write_text(json.dumps({'recipes':catalog},ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'manifest.json').write_text(json.dumps({'weapons':all_manifest},ensure_ascii=False,indent=2),encoding='utf-8')
