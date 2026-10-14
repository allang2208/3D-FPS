"""Import the combat clips and projectile art; no native class dependency yet."""
from pathlib import Path
helpers=Path('D:/FPS3D/FPSGAME/Tools/BellowSacLobber/import_assets.py').read_text(encoding='utf-8')
exec(compile(helpers.split('previous_fbx=')[0],'bellow_import_helpers','exec'))
COMBAT=ROOT/'CombatV02'
combat=json.loads((COMBAT/'combat_manifest_v02.json').read_text(encoding='utf-8'))
VERSION2=DEST+'/V02'
REPORT=ROOT/'Records/ue_combat_v02.json'
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'saved':[],'stages':[],'runtime_tested':False}
previous_fbx=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    mesh=u.load_asset(VERSION+'/SK_BellowSacLobber')
    clips={}
    for row in combat['clips']:
        role=row['role'];name='A_BellowSacLobber_'+role
        clip=import_file(row['file'],name,VERSION2+'/Animations',fbx(True,mesh.skeleton),u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',False)
        clip.set_preview_skeletal_mesh(mesh)
        report.setdefault('root_units',{})[role]=import_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compilation: '+name)
        save(clip);clips[role]=clip
    save(mesh.skeleton)
    props={}
    for key,name in [('capsule_mesh','SM_BellowSacCapsule'),('ring_mesh','SM_BellowRuptureRing')]:
        options=u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False
        options.import_materials=False;options.import_textures=False
        options.static_mesh_import_data.set_editor_property('convert_scene',True)
        options.static_mesh_import_data.set_editor_property('convert_scene_unit',True)
        options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        asset=import_file(combat[key],name,VERSION2+'/Projectile',options,u.FbxFactory())
        props[key]=asset;save(asset)
    def vec(mat,color):
        node=ME.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        node.set_editor_property('constant',u.LinearColor(*color))
        return node
    def scalar(mat,value):
        node=ME.create_material_expression(mat,u.MaterialExpressionConstant)
        node.set_editor_property('r',value);return node
    materials={}
    for name,ring in [('M_BellowSacCapsule',False),('M_BellowRuptureRing',True)]:
        mat=create(name,VERSION2+'/Projectile',u.Material,u.MaterialFactoryNew())
        ME.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',True)
        if not ring: mat.set_editor_property('used_with_instanced_static_meshes',True)
        slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
        if ring:
            color=vec(mat,(.45,.14,.035,1.));rough=scalar(mat,.65)
            emissive=vec(mat,(1.8,.40,.08,1.))
            ME.connect_material_expressions(emissive,'',slab,'EmissiveColor')
            ME.connect_material_property(emissive,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        else:
            # Warm gray-pink membrane with cooler marbling, using stable UVs.
            uv=ME.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
            append=ME.create_material_expression(mat,u.MaterialExpressionAppendVector)
            ME.connect_material_expressions(uv,'',append,'A')
            ME.connect_material_expressions(scalar(mat,0.),'',append,'B')
            noise=ME.create_material_expression(mat,u.MaterialExpressionNoise)
            noise.set_editor_property('scale',18.);noise.set_editor_property('levels',2)
            ME.connect_material_expressions(append,'',noise,'Position')
            color=ME.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
            ME.connect_material_expressions(vec(mat,(.105,.080,.074,1.)),'',color,'A')
            ME.connect_material_expressions(vec(mat,(.46,.33,.29,1.)),'',color,'B')
            ME.connect_material_expressions(noise,'',color,'Alpha')
            rough=scalar(mat,.37)
        ME.connect_material_expressions(color,'',slab,'BaseColor')
        ME.connect_material_expressions(rough,'',slab,'Roughness')
        ME.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
        ME.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        ME.recompile_material(mat);save(mat);materials[name]=mat
    for key,name in [('capsule_mesh','M_BellowSacCapsule'),('ring_mesh','M_BellowRuptureRing')]:
        props[key].set_material(0,materials[name]);save(props[key])
    path=VERSION2+'/DA_BellowSacLobber_Combat'
    dataset=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(VERSION+'/DA_BellowSacLobber_Locomotion',path)
    actions=dict(dataset.get_editor_property('actions'))
    for row in combat['clips']:
        role=row['role'];entry=u.QuadrupedTemplateAction()
        entry.set_editor_property('sequence',clips[role]);entry.set_editor_property('loop',False)
        entry.set_editor_property('hold_last_pose',True);entry.set_editor_property('blend_seconds',.18)
        entry.set_editor_property('contact_start_seconds',row['contact'])
        entry.set_editor_property('contact_end_seconds',row['contact']+1./60.)
        actions['Attack'+role]=entry
    dataset.set_editor_property('actions',actions);save(dataset)
    report['animation_set']=dataset.get_path_name()
    report['clips']={key:value.get_path_name() for key,value in clips.items()}
    report['projectile_meshes']={key:value.get_path_name() for key,value in props.items()}
    report['materials']={key:value.get_path_name() for key,value in materials.items()}
    if 'art' not in report['stages']:report['stages'].append('art')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BELLOW_COMBAT_ART_SAVED '+json.dumps(report,ensure_ascii=False))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous_fbx))
