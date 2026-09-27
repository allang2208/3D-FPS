"""Import the authored station and register a separate buildable prefab. No level/PIE."""
import datetime
import json
import math
from pathlib import Path
import sys
import unreal as u

ROOT=Path(u.Paths.project_dir())
HERE=ROOT/'SourceAssets/CastingStation20260926'
MAN=json.loads((HERE/'Authored/manifest.json').read_text(encoding='utf8'))
DEST='/Game/Props/CastingStation20260926'
PALETTE='/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from furnace_material_graph import node,wire,prop,custom
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
SAVED=[]

def save(asset):
    if isinstance(asset,u.Material):L.recompile_material(asset)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    SAVED.append(asset.get_path_name())

def surface(name,water=False):
    path=DEST+'/Materials/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if E.get_metadata_tag(m,'CastingStation')=='v1':return m
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('used_with_nanite',True)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    clock=node(m,u.MaterialExpressionTime)
    grain=custom(m,'return .5+.5*sin(UV.x*987+sin(UV.y*41)*.12);',{'UV':uv})
    tint=custom(m,'return float3(.028,.072,.079);' if water else 'return float3(.30,.325,.35)*(.92+.08*Grain);',{'Grain':grain},3)
    rough=custom(m,'return .16;' if water else 'return .22+.12*Grain;',{'Grain':grain})
    metal=node(m,u.MaterialExpressionConstant);metal.set_editor_property('r',0. if water else 1.)
    normal=custom(m,'return normalize(float3(.025*sin(UV.x*52+Time*.8),.025*cos(UV.y*57-Time*.7),1));' if water else
        'return normalize(float3((Grain-.5)*.06,0,1));',{'UV':uv,'Time':clock,'Grain':grain},3)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for output,pin,value in [('BASE_COLOR','BaseColor',tint),('ROUGHNESS','Roughness',rough),('METALLIC','Metallic',metal),('NORMAL','Normal',normal)]:
        prop(m,value,output);wire(value,slab,pin)
    prop(m,slab,'FRONT_MATERIAL')
    E.set_metadata_tag(m,'CastingStation','v1');save(m)
    return m

def run():
    targets={PALETTE}|{DEST+'/'+n for n in MAN['assets']}
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts=targets.intersection(dirty)
    if conflicts:raise RuntimeError('Unsaved target packages: '+str(conflicts))
    E.make_directory(DEST)
    mats={
        'Masonry':u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_Masonry'),
        'DarkSteel':u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_WroughtIron'),
        'Wood':u.load_asset('/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A'),
        'PolishedSteel':surface('M_AnvilFace'),'Water':surface('M_CoolingWater',True)}
    if any(m is None for m in mats.values()):raise RuntimeError('Missing existing station surface library')
    meshes={}
    for name,record in MAN['assets'].items():
        path=DEST+'/'+name
        mesh=u.load_asset(path) if E.does_asset_exist(path) else None
        if mesh is None:
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
            d=opt.static_mesh_import_data
            d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
            d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
            d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            t=u.AssetImportTask();t.filename=record['fbx'];t.destination_path=DEST;t.destination_name=name
            t.automated=True;t.replace_existing=False;t.save=False;t.options=opt;t.factory=u.FbxFactory()
            A.import_asset_tasks([t]);mesh=u.load_asset(path)
            if mesh is None:raise RuntimeError('Import failed '+path)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            label=str(slot.get_editor_property('material_slot_name')).split('.')[0]
            if label not in mats:raise RuntimeError('Unknown material slot '+label)
            mesh.set_material(i,mats[label])
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        settings=mesh.get_editor_property('nanite_settings')
        settings.enabled=name not in ('SM_BlacksmithTongs','SM_CoolingWater')
        mesh.set_editor_property('nanite_settings',settings)
        if name=='SM_CastingStation':
            for label,point in MAN['sockets_ue_cm'].items():
                if mesh.find_socket(label):continue
                sock=u.new_object(u.StaticMeshSocket,outer=mesh)
                sock.set_editor_property('socket_name',label);sock.set_editor_property('relative_location',u.Vector(*point))
                mesh.add_socket(sock)
        E.set_metadata_tag(mesh,'SourceAuthoring','SourceAssets/CastingStation20260926/author_station.py')
        save(mesh);meshes[name]=mesh
    palette=u.load_asset(PALETTE)
    entries=list(palette.get_editor_property('components'))
    if not any(str(e.get_editor_property('id'))=='casting_station' for e in entries):
        mesh=meshes['SM_CastingStation'];bounds=mesh.get_bounds()
        size=[float(v)*2 for v in (bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z)]
        cells=MAN['footprint_cells']
        entry=u.VoxelBuildPrefab();entry.set_editor_property('id','casting_station')
        entry.set_editor_property('display_name',u.Text('铸造台'))
        entry.set_editor_property('mesh',mesh);entry.set_editor_property('material','')
        entry.set_editor_property('footprint',u.IntVector(*cells))
        entry.set_editor_property('pivot_offset_cm',u.Vector(0,0,-(cells[2]*20-size[2])*.5))
        entries.append(entry);palette.set_editor_property('components',entries);save(palette)
    receipt={'saved':SAVED,'prefab':'casting_station','footprint_cells':MAN['footprint_cells'],
             'sockets_ue_cm':MAN['sockets_ue_cm'],'materials':{k:v.get_path_name() for k,v in mats.items()},
             'runtime_tested':False,'rendered':False}
    (HERE/'Receipts').mkdir(exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    (HERE/'Receipts'/('import-'+stamp+'.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('CASTING_STATION_INSTALLED '+json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':
    # Preserve the current reference-shaped anvil when reinstalling the assembly.
    revision=HERE/'AnvilReferenceV3'
    realism=ROOT/'SourceAssets/CastingStationRealism20260927'
    if (realism/'Authored/manifest.json').exists():
        import runpy
        runpy.run_path(str(realism/'install.py'),run_name='__main__')
    elif (revision/'Authored/manifest.json').exists():
        prerequisites=[DEST+'/'+n for n in MAN['assets']]+[DEST+'/Materials/M_AnvilFace',DEST+'/Materials/M_CoolingWater']
        if not all(E.does_asset_exist(path) for path in prerequisites):run()
        import runpy
        runpy.run_path(str(revision/'install.py'),run_name='__main__')
    else:run()
