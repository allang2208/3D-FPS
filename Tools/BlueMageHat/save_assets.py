"""Import the independent hat rig, PBR surfaces and inventory/drop assets."""
import json, hashlib, importlib.util, sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageHat20261019'
DEST='/Game/Characters/ModularOutfit20260924/BlueMageHat20261019'
ROBE='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'runtime_tested':False}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

materials=module('hat_materials','Tools/BlueMageRobe/materials.py');materials.DEST=DEST
load,save=materials.load,materials.save

def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def create_materials():
    if receipt.get('materials'):return [load(p) for p in receipt['materials']]
    tex={f+'_'+c:load(ROBE+'/Textures/T_'+f+'_'+c) for f in ('BlueMageFabric','BlueMageEmbroidery') for c in ('BaseColor','Normal','ORM')}
    band=materials.material('M_BlueMageHat_Band',tex,'embroidery')
    # Keep the silver embroidery while darkening only its cloth background.
    for node in L.get_material_expressions(band):
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property('code');node.set_editor_property('code',code.replace('OutNormal=', 'color=lerp(color*float3(.22,.27,.34),color,saturate(orm.b));\nOutNormal=',1))
    errors=L.recompile_material(band)
    if errors:raise RuntimeError('Hat band shader compile failed: '+str(errors))
    save(band)
    mats=[load(ROBE+'/Materials/M_BlueMage_Fabric'),load(ROBE+'/Materials/M_BlueMage_Lining'),band,load(ROBE+'/Materials/M_BlueMage_Embroidery'),materials.solid('M_BlueMageHat_Thread',(.57,.55,.49),.25,.6),load(ROBE+'/Materials/M_BlueMage_Silver'),load(ROBE+'/Materials/M_BlueMage_Gem')]
    receipt['materials']=[m.get_path_name() for m in mats];record();return mats

def skeletal(mats,d):
    file=R/'Exports/BlueMageHat.fbx';sha=hashlib.sha256(file.read_bytes()).hexdigest();name='SK_BlueMageHat';path=DEST+'/'+name
    mesh=u.load_asset(path)
    if mesh and E.get_metadata_tag(mesh,'BlueMageHatSHA')==sha:
        receipt['mesh']=mesh.get_path_name();receipt['skeleton']=mesh.skeleton.get_path_name();receipt['fbx_sha256']=sha;record();return mesh
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeleton=mesh.skeleton if mesh else None
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.;data.force_front_x_axis=False
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.options=options;A.import_asset_tasks([task]);mesh=load(path)
    slots=list(mesh.get_editor_property('materials'));byname=dict(zip(d['material_slots'],mats))
    for slot in slots:
        slotname=str(slot.get_editor_property('imported_material_slot_name'))
        slot.set_editor_property('material_interface',byname[slotname]);slot.set_editor_property('material_slot_name',slotname)
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build)
    # This FBX has only LOD0. Let UE allocate imported LOD models sequentially
    # before applying the policy; the clothing helper only adds LODInfo entries.
    if not S.regenerate_lod(mesh,3,False,False):raise RuntimeError('Cannot allocate hat LOD models')
    print('BLUE_MAGE_HAT_LOD_MODELS_CREATED',flush=True)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',DEST,u.SkeletalMeshLODSettings,factory);groups=[]
    for ratio,screen in ((1.,1.),(.55,.18),(.25,.075)):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for prop,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=4,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(prop,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);mesh.set_editor_property('lod_settings',policy)
    models=list(mesh.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    mesh.set_editor_property('source_models',models)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot create hat LODs')
    # Extra bounds accommodate the upper cone's bounded ten-degree swing.
    mesh.set_editor_property('positive_bounds_extension',u.Vector(4,4,3));mesh.set_editor_property('negative_bounds_extension',u.Vector(4,4,1))
    E.set_metadata_tag(mesh,'BlueMageHatSHA',sha);E.set_metadata_tag(mesh,'EquipmentDefinition','ue_blue_mage_hat');save(mesh.skeleton);save(mesh)
    receipt.update(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),fbx_sha256=sha,lod_count=S.get_lod_count(mesh),material_slots=[str(s.material_slot_name) for s in slots]);record();print('BLUE_MAGE_HAT_SKELETAL_SAVED',flush=True);return mesh

def displays(mats,d):
    sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
    io=module('hat_dynamic_io','Tools/BlueMageRobe/save_assets.py')
    static=module('hat_static_io','Tools/ChainmailPants/save_assets.py');static.DEST=DEST
    T=u.GeometryScript_MeshTransforms
    center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)]
    display_sha=hashlib.sha256((R/'Authored/hat.json').read_bytes()).hexdigest()
    for kind in ('Icon','Pickup'):
        if receipt.get(kind.lower()) and receipt.get(kind.lower()+'_source_sha256')==display_sha:continue
        dm=io.dynamic(d)
        T.translate_mesh(dm,u.Vector(*[-v for v in center]))
        if kind=='Icon':T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
        receipt[kind.lower()]=static.static(dm,DEST+'/'+kind+'s/SM_BlueMageHat_'+kind,mats);receipt[kind.lower()+'_source_sha256']=display_sha;record()
    if not receipt.get('icon_texture'):
        task=u.AssetImportTask();task.filename=str(R/'ue_blue_mage_hat.png');task.destination_path=DEST+'/Icons';task.destination_name='T_BlueMageHat_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(DEST+'/Icons/T_BlueMageHat_Icon')
        for prop,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(prop,value)
        save(tex);receipt['icon_texture']=tex.get_path_name();record()

def imported_fits(mesh,d):
    # Resolve the actual FBX coordinate frame before applying the authored fit.
    # The three non-collinear tip joints determine orientation and unit scale.
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot resolve imported hat coordinate frame')
    bones={str(b.name):b.world_transform.translation for b in u.GeometryScript_BoneWeights.get_all_bones_info(dm)[1]}
    names=['HatTipBase','HatTipMid','HatTipEnd'];source=[u.Vector(*d['bones'][n]['position']) for n in names];actual=[bones[n] for n in names]
    K=u.MathLibrary
    scale=(actual[1]-actual[0]).length()/(source[1]-source[0]).length()
    authored=u.Transform(location=source[0],rotation=K.make_rot_from_xy(source[1]-source[0],source[2]-source[0]),scale=u.Vector(1,1,1))
    imported=u.Transform(location=actual[0],rotation=K.make_rot_from_xy(actual[1]-actual[0],actual[2]-actual[0]),scale=u.Vector(scale,scale,scale))
    correction=K.compose_transforms(K.invert_transform(imported),authored)
    fits=json.loads((R/'fit.json').read_text())['fits'];result={}
    for key,fit in fits.items():
        pitch,yaw,roll=fit['rotation'];target=u.Transform(location=u.Vector(*fit['location']),rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=u.Vector(*fit['scale']))
        target=K.compose_transforms(correction,target);r=target.rotation.rotator()
        result[key]=dict(location=[target.translation.x,target.translation.y,target.translation.z],rotation=[r.pitch,r.yaw,r.roll],scale=[target.scale3d.x,target.scale3d.y,target.scale3d.z])
    receipt['imported_tip_positions']={n:[bones[n].x,bones[n].y,bones[n].z] for n in names};return result

def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Preserve assets during PIE')
    receipt['completed']=False;record();E.make_directory(DEST)
    d=json.loads((R/'Authored/hat.json').read_text());mats=create_materials();mesh=skeletal(mats,d);fits=imported_fits(mesh,d);displays(mats,d)
    sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
    from save_icons import apply_item
    apply_item('ue_blue_mage_hat')
    receipt.update(completed=True,source_triangles=len(d['triangles']),fit=fits,tip_bones=['HatTipBase','HatTipMid','HatTipEnd'],simulation='local_bounded_angular_spring');record();print('BLUE_MAGE_HAT_ASSETS_SAVED',flush=True)

if __name__=='__main__':main()
