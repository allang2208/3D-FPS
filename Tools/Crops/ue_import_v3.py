"""Crops V3 asset-library import/readback, restricted to its dedicated namespace.

Run through run_v3.ps1. No maps, actors, gameplay systems, or shared config saves.
"""
import hashlib
import json
import re
import traceback
from pathlib import Path

import unreal as u

P = Path('D:/FPS3D/FPSGAME')
ROOT = P / 'SourceAssets/CropsV3_20261022'
SRC = ROOT / 'Source'
DEST = '/Game/Props/Crops/V3'
HOST = P / 'Saved/CropsV3ImportHost'
BATCH = 'CropsV3_20261022'
assert Path(u.Paths.project_dir()).resolve() == HOST.resolve()
assert '-CropsV3AssetBatch' in u.SystemLibrary.get_command_line()
READBACK = '-CropsV3Readback' in u.SystemLibrary.get_command_line()
REFRESH = '-CropsV3RefreshLODs' in u.SystemLibrary.get_command_line()
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
S = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
manifest = json.loads((SRC / 'variant_manifest.json').read_text(encoding='utf-8'))
audit_path=ROOT/'Receipts/fbx-engine-audit.json'
audit = json.loads((audit_path if audit_path.exists() else ROOT/'Receipts/fbx-derived-audit.json').read_text())
assert len(audit['meshes']) == 108 and not audit['errors']
by_file = {r['file']:r for r in audit['meshes']}
image_sizes = {r['file']:r['size'] for r in json.loads((ROOT/'Receipts/package-audit.json').read_text())['images']}
receipt_path = ROOT / ('Receipts/ue-readback.json' if READBACK else 'Receipts/ue-import.json')
report = {'status':'running', 'host':str(HOST), 'asset_root':DEST, 'saved':[], 'meshes':[],
          'materials':[], 'textures':[], 'instances':[], 'runtime_tested':False,
          'shader_render_verified':False, 'maps_saved':False, 'independent_process_readback':READBACK}


def record():
    receipt_path.write_text(json.dumps(report,indent=2),encoding='utf-8')


def owned(path):
    obj = u.load_asset(path) if E.does_asset_exist(path) else None
    if obj:
        assert E.get_metadata_tag(obj,'CropsBatch') == BATCH, 'Unowned existing asset: '+path
    return obj


def save(obj):
    assert obj.get_path_name().startswith(DEST+'/')
    E.set_metadata_tag(obj,'CropsBatch',BATCH)
    assert E.save_loaded_asset(obj,False), obj.get_path_name()
    report['saved'].append(obj.get_path_name())
    record()


def load(path):
    obj=owned(path)
    assert obj, 'Missing '+path
    return obj


def graph_nodes(material):
    todo=[L.get_material_property_input_node(material,u.MaterialProperty.MP_FRONT_MATERIAL)]
    seen=set(); result=[]
    while todo:
        node=todo.pop()
        if not node or node.get_path_name() in seen:continue
        seen.add(node.get_path_name());result.append(node)
        todo.extend(L.get_inputs_for_material_expression(material,node))
    return result


def textures():
    result={}
    for f in sorted((SRC/'Textures').glob('*.png')):
        if 'NormalGL' in f.name:continue
        path=DEST+'/Textures/T_Crops_'+f.stem
        tex=owned(path)
        digest=hashlib.sha256(f.read_bytes()).hexdigest()
        normal='NormalDX' in f.stem; mask='Roughness' in f.stem
        if not tex:
            assert not READBACK,path
            task=u.AssetImportTask();task.filename=str(f);task.destination_path=DEST+'/Textures'
            task.destination_name='T_Crops_'+f.stem;task.automated=True;task.replace_existing=False;task.save=False
            task.factory=u.TextureFactory();A.import_asset_tasks([task]);tex=u.load_asset(path)
            assert isinstance(tex,u.Texture2D),path
            tex.set_editor_property('srgb',not(normal or mask))
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if mask else u.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property('flip_green_channel',False)
            tex.set_editor_property('never_stream',False)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WORLD)
            E.set_metadata_tag(tex,'CropsSourceSHA256',digest);save(tex)
        assert E.get_metadata_tag(tex,'CropsSourceSHA256')==digest
        assert tex.get_editor_property('srgb')==(not(normal or mask))
        assert not tex.get_editor_property('flip_green_channel')
        compression=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if mask else u.TextureCompressionSettings.TC_DEFAULT
        assert tex.get_editor_property('compression_settings')==compression
        assert not tex.get_editor_property('never_stream')
        assert [tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]==image_sizes['Textures/'+f.name]
        result[f.stem]=tex
        report['textures'].append({'path':tex.get_path_name(),'source':f.name,
           'dimensions':[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()],
           'srgb':tex.get_editor_property('srgb'),'compression':str(compression),'flip_green':False})
    return result


def wire(src,pin,dst,input_name):
    assert L.connect_material_expressions(src,pin,dst,input_name),(pin,input_name)


def constant(mat,value):
    if isinstance(value,(list,tuple)):
        n=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        n.constant=u.LinearColor(*value[:3],1.0)
    else:
        n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=float(value)
    return n


def make_materials(tex):
    result={}
    names=sorted(set(audit['materials']) | {'Soil','PotatoSkin'})
    for name in names:
        path=DEST+'/Materials/M_Crops_'+name
        mat=owned(path)
        textured=name+'_BaseColor' in tex
        foliage=name in ('Leaf','YoungLeaf')
        source=audit['materials'].get(name)
        if not mat:
            assert not READBACK,path
            mat=A.create_asset('M_Crops_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());assert mat
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('used_with_instanced_static_meshes',True)
            values={}
            if textured:
                uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.coordinate_index=0
                for channel,prop in [('BaseColor','BASE_COLOR'),('NormalDX','NORMAL'),('Roughness','ROUGHNESS')]:
                    n=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
                    n.texture=tex[name+'_'+channel]
                    n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='NormalDX' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='Roughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
                    wire(uv,'',n,'UVs');pin='R' if channel=='Roughness' else 'RGB'
                    if channel=='BaseColor' and foliage:
                        tint=L.create_material_expression(mat,u.MaterialExpressionVectorParameter)
                        tint.set_editor_property('parameter_name','FoliageTint')
                        tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
                        mul=L.create_material_expression(mat,u.MaterialExpressionMultiply)
                        wire(n,pin,mul,'A');wire(tint,'',mul,'B');n=mul;pin=''
                    values[prop]=(n,pin)
            else:
                values['BASE_COLOR']=(constant(mat,source['diffuse']),'')
                values['ROUGHNESS']=(constant(mat,source['roughness']),'')
            values['METALLIC']=(constant(mat,0.),'')
            values['SPECULAR']=(constant(mat,source['bsdf'].get('Specular IOR Level',.5) if source else .5),'')
            slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
            slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
            pins={str(s).replace(' ','').lower():str(s) for s in L.get_material_expression_input_names(slab)}
            for prop,(node,pin) in values.items():
                assert L.connect_material_property(node,pin,getattr(u.MaterialProperty,'MP_'+prop))
                wire(node,pin,slab,pins[prop.replace('_','').lower()])
            assert L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
            L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
        assert mat.get_editor_property('two_sided')
        assert mat.get_editor_property('used_with_instanced_static_meshes')
        assert not L.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        nodes=graph_nodes(mat)
        used=sorted(n.texture.get_path_name() for n in nodes if isinstance(n,u.MaterialExpressionTextureSample))
        expected=sorted(tex[name+'_'+c].get_path_name() for c in ('BaseColor','NormalDX','Roughness')) if textured else []
        assert used==expected,(name,used,expected)
        result[name]=mat
        report['materials'].append({'path':mat.get_path_name(),'textures':used,'two_sided':True,
              'substrate_front_material':True,'foliage_tint_parameter':foliage})
    instances={}
    for name in ('Leaf','YoungLeaf'):
        for variant,tint in manifest['variant_tint_presets'].items():
            asset_name='MI_Crops_'+name+'_V'+variant;path=DEST+'/Materials/'+asset_name
            mi=owned(path)
            if not mi:
                assert not READBACK,path
                mi=A.create_asset(asset_name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());assert mi
                L.set_material_instance_parent(mi,result[name])
                # UE 5.8 MaterialEditingLibrary.cpp always returns false here even after setting.
                # Verify the actual parameter value below and again after process reload.
                L.set_material_instance_vector_parameter_value(mi,'FoliageTint',u.LinearColor(*tint,1.0))
                save(mi)
            assert mi.parent==result[name]
            value=L.get_material_instance_vector_parameter_value(mi,'FoliageTint')
            assert max(abs(a-b) for a,b in zip([value.r,value.g,value.b],tint))<1e-5
            instances[(name,variant)]=mi
            report['instances'].append({'path':mi.get_path_name(),'parent':mi.parent.get_path_name(),'tint':tint})
    return result,instances


def bind_materials(mesh,source_names,variant,mats,instances):
    canon=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
    indices={canon(n):i for i,n in enumerate(source_names)}
    slots=[];remap={}
    for source_name in source_names:
        slot=u.StaticMaterial();slot.material_slot_name=source_name
        slot.material_interface=instances.get((source_name,variant),mats[source_name]);slots.append(slot)
    for i,slot in enumerate(mesh.static_materials):
        key=canon(slot.material_slot_name);assert key in indices,(mesh.get_path_name(),key)
        remap[i]=indices[key]
    for lod in range(3):
        for section in range(mesh.get_num_sections(lod)):
            S.set_lod_material_slot(mesh,remap[S.get_lod_material_slot(mesh,lod,section)],lod,section)
    mesh.set_editor_property('static_materials',slots)
    for i,slot in enumerate(slots):mesh.set_material(i,slot.material_interface)


def mesh_assets(mats,instances):
    plan=json.loads((ROOT/'Receipts/lod-refresh-plan.json').read_text()) if REFRESH else {}
    for asset in manifest['assets']:
        name='SM_'+asset['id'];path=DEST+'/Meshes/'+name
        source=[by_file[Path(asset[k]).name] for k in ('mesh_file','lod1_file','lod2_file')]
        signature=hashlib.sha256(''.join(x['sha256'] for x in source).encode()).hexdigest()
        mesh=owned(path)
        if not mesh:
            assert not READBACK,path
            task=u.AssetImportTask();task.filename=str(ROOT/source[0]['read_path'])
            task.destination_path=DEST+'/Meshes';task.destination_name=name
            task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
            opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
            opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
            d.transform_vertex_to_absolute=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False
            d.remove_degenerates=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(path)
            assert isinstance(mesh,u.StaticMesh),(path,task.imported_object_paths)
            for lod in (1,2):
                assert S.import_lod(mesh,lod,str(ROOT/source[lod]['read_path']))==lod
            for lod in range(3):
                settings=S.get_lod_build_settings(mesh,lod)
                for key,value in {'remove_degenerates':False,'recompute_normals':False,'recompute_tangents':True,
                  'use_mikk_t_space':True,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True,
                  'generate_lightmap_u_vs':False}.items():settings.set_editor_property(key,value)
                S.set_lod_build_settings(mesh,lod,settings)
            # These are small thin foliage meshes with explicit authored LODs, no Nanite conversion.
            nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;S.set_nanite_settings(mesh,nan,True)
            bind_materials(mesh,source[0]['slots'],asset['variant'],mats,instances)
            assert S.set_lod_screen_sizes(mesh,[1.,.45,.18])
            E.set_metadata_tag(mesh,'CropsSourceSHA256',signature)
            E.set_metadata_tag(mesh,'CropsStableID',asset['id']);save(mesh)
        rebuild=False
        if E.get_metadata_tag(mesh,'CropsSourceSHA256')!=signature:
            assert REFRESH and asset['id'] in plan and not READBACK,(path,'Unexpected source change')
            entry=plan[asset['id']]
            assert E.get_metadata_tag(mesh,'CropsSourceSHA256')==entry['previous_source_signature']
            for lod in entry['lods']:
                assert S.import_lod(mesh,lod,str(ROOT/source[lod]['read_path']))==lod
            bind_materials(mesh,source[0]['slots'],asset['variant'],mats,instances)
            E.set_metadata_tag(mesh,'CropsSourceSHA256',signature);rebuild=True
        assert E.get_metadata_tag(mesh,'CropsSourceSHA256')==signature
        for lod in range(3):
            settings=S.get_lod_build_settings(mesh,lod)
            changed=False
            for key,value in {'recompute_tangents':True,'recompute_normals':False,'use_mikk_t_space':True,
                  'remove_degenerates':False,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True}.items():
                if settings.get_editor_property(key)!=value:
                    assert not READBACK,(path,lod,key)
                    settings.set_editor_property(key,value);changed=True
            if changed:S.set_lod_build_settings(mesh,lod,settings);rebuild=True
        if rebuild:
            E.set_metadata_tag(mesh,'CropsTangentBuild','MikkTSpace');save(mesh)
        assert S.get_lod_count(mesh)==3,path
        tri=[mesh.get_num_triangles(i) for i in range(3)]
        assert tri==[x['triangles'] for x in source],(path,tri)
        b=mesh.get_bounds();dims=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
        expected=[v*100 for v in source[0]['dimensions_m']]
        assert abs(dims[2]-expected[2])<.03 and max(abs(a-b) for a,b in zip(sorted(dims[:2]),sorted(expected[:2])))<.03,(path,dims,expected)
        assert abs(b.origin.z-b.box_extent.z-source[0]['bounds_min_m'][2]*100)<.03,(path,'Z origin changed')
        assert abs(b.origin.z+b.box_extent.z-source[0]['bounds_max_m'][2]*100)<.03
        sections=[]
        for lod in range(3):
            indices=[S.get_lod_material_slot(mesh,lod,s) for s in range(mesh.get_num_sections(lod))]
            assert all(0<=i<len(mesh.static_materials) for i in indices),(path,indices)
            names=[str(mesh.static_materials[i].material_slot_name) for i in indices]
            assert set(names)==set(source[lod]['material_triangles']),(path,lod,names,source[lod]['material_triangles'])
            sections.append(indices)
        for slot in mesh.static_materials:
            source_name=str(slot.material_slot_name)
            assert slot.material_interface==instances.get((source_name,asset['variant']),mats[source_name]),(path,source_name)
        assert not mesh.get_editor_property('nanite_settings').enabled
        assert S.get_simple_collision_count(mesh)==0 and S.get_convex_collision_count(mesh)==0
        screen=list(S.get_lod_screen_sizes(mesh))
        if not READBACK and any(abs(a-b)>1e-5 for a,b in zip(screen,[1.,.45,.18])):
            assert S.set_lod_screen_sizes(mesh,[1.,.45,.18]);save(mesh);screen=list(S.get_lod_screen_sizes(mesh))
        assert max(abs(a-b) for a,b in zip(screen,[1.,.45,.18]))<1e-5,(path,screen)
        report['meshes'].append({'id':asset['id'],'path':mesh.get_path_name(),'triangles':tri,
             'dimensions_cm':dims,'bounds_min_cm':[b.origin.x-b.box_extent.x,b.origin.y-b.box_extent.y,b.origin.z-b.box_extent.z],
             'bounds_max_cm':[b.origin.x+b.box_extent.x,b.origin.y+b.box_extent.y,b.origin.z+b.box_extent.z],
             'lod_screen_sizes':screen,'sections':sections,
             'recompute_tangents':True,'recompute_normals':False,
             'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]})
        record();print('CROPS_MESH_READY',asset['id'])


try:
    # Reject a foreign asset before performing any mutations.
    for path in E.list_assets(DEST,True,False):owned(path)
    tex=textures();mats,instances=make_materials(tex);mesh_assets(mats,instances)
    if READBACK:
        basis_script=P/'Tools/Crops/ue_basis_v3.py'
        exec(compile(basis_script.read_text(encoding='utf-8'),str(basis_script),'exec'),{'__name__':'__crops_basis__'})
    report['status']='reloaded_verified' if READBACK else 'imported_saved'
    report['counts']={'meshes':len(report['meshes']),'materials':len(report['materials']),
                      'material_instances':len(report['instances']),'textures':len(report['textures'])}
    record();print('CROPS_V3_COMPLETE',json.dumps(report['counts']))
except Exception:
    report['status']='failed';report['error']=traceback.format_exc();record();raise
