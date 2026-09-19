"""Author dedicated fountain stone, small step chamfers, and PCM loop assets.

Preserves the V8 water, source mesh, shared stone materials and collision contract.
No game launch, rendering, listening or performance test.
"""
import importlib.util
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('fountain_helpers', HERE/'build_cascade_v7_20260919.py')
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)
ROOT = '/Game/Props/RomanFountain20260917/PolishV9'
E, M, TOOLS = v7.E, v7.M, v7.TOOLS
node, custom, scalar, wire, prop = v7.node, v7.custom, v7.scalar, v7.wire, v7.prop
REPORT = {'runtime_tested':False, 'assets':[]}


def save(asset):
    if isinstance(asset, u.Material):
        errors = M.recompile_material(asset)
        if errors:
            raise RuntimeError(str(errors))
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    REPORT['assets'].append(asset.get_path_name())
    print('FOUNTAIN_V9_SAVED '+asset.get_path_name())


def constant(mat, value, kind=1):
    return custom(mat, 'return '+value+';', {}, kind)


def stone_material():
    surface = u.load_asset('/Game/Props/RomanFountain20260917/SM_RomanFountain_20').get_material(0)
    REPORT['source_surface'] = surface.get_path_name()
    parent = surface
    while isinstance(parent, u.MaterialInstance):
        parent = parent.get_editor_property('parent')
    path = ROOT+'/M_FountainStoneV9'
    mat = u.load_asset(path) if E.does_asset_exist(path) else None
    if not mat:
        mat = E.duplicate_asset(parent.get_path_name(), path)
        # Read and extend the copied graph, retaining its original dry stone look.
        originals = {}
        for key in ('BASE_COLOR', 'ROUGHNESS', 'NORMAL'):
            p = getattr(u.MaterialProperty, 'MP_'+key)
            originals[key] = (M.get_material_property_input_node(mat, p), M.get_material_property_input_node_output_name(mat, p))
        world = node(mat, u.MaterialExpressionWorldPosition)
        local = node(mat, u.MaterialExpressionTransformPosition)
        local.set_editor_property('transform_source_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        local.set_editor_property('transform_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(world, local, '')
        tex = node(mat, u.MaterialExpressionTextureObjectParameter)
        tex.set_editor_property('parameter_name', 'FountainWearNoise')
        tex.set_editor_property('texture', u.load_asset('/Game/Props/RomanFountain20260917/OverflowV8/T_FountainFlowNoiseV8'))
        tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        masks = custom(mat, '''
float r=length(P.xy);
float a=atan2(P.y,P.x)/6.2831853;
float4 n=Texture2DSampleLevel(NoiseTex,NoiseTexSampler,float2(a,P.z*.0018),1);
float low=smoothstep(325,375,r)*(1-smoothstep(425,455,r))*exp2(-abs(P.z-148)/32);
float mid=smoothstep(220,247,r)*(1-smoothstep(275,295,r))*exp2(-abs(P.z-416)/27);
float top=smoothstep(145,165,r)*(1-smoothstep(186,205,r))*exp2(-abs(P.z-568)/22);
float socle=(1-smoothstep(212,232,r))*smoothstep(145,170,r)*exp2(-abs(P.z-148)/17);
float wet=saturate(max(max(low,mid),max(top,socle))*(.45+.55*smoothstep(.18,.78,n.r))*Wetness);
float deposit=wet*(exp2(-abs(P.z-150)/3)+exp2(-abs(P.z-419)/3)+exp2(-abs(P.z-570)/3))*(.3+.7*n.g);
return float3(wet,saturate(deposit)*Mineral,n.b);
''', dict(P=local, NoiseTex=tex, Wetness=scalar(mat, 'FountainWetness', .85), Mineral=scalar(mat, 'FountainMineral', .12)), 3)
        base, base_output = originals['BASE_COLOR']
        base = base or constant(mat, 'float3(.62,.61,.58)', 3)
        color = custom(mat, 'return lerp(Base*lerp(1,.78,Mask.x),float3(.62,.60,.53),Mask.y);', dict(Base=base, Mask=masks), 3)
        wire(base, color, 'Base', base_output)
        prop(color, 'BASE_COLOR')
        rough, rough_output = originals['ROUGHNESS']
        rough = rough or constant(mat, '.6')
        roughness = custom(mat, 'return lerp(Rough,max(.18,Rough*.42),Mask.x);', dict(Rough=rough, Mask=masks))
        wire(rough, roughness, 'Rough', rough_output)
        prop(roughness, 'ROUGHNESS')
        # Small staggered scale facets on the finial only; no outline displacement.
        facets = custom(mat, '''
float a=atan2(P.y,P.x);
float row=P.z/15;
float2 cell=float2(frac(a/6.2831853*14+floor(row)*.5)-.5,frac(row)-.5);
float inside=saturate(1-abs(cell.x)*2-cell.y*cell.y*3);
float mask=smoothstep(573,590,P.z)*(1-smoothstep(702,718,P.z))*(1-smoothstep(68,82,length(P.xy)));
float side=-sign(cell.x)*inside*.10*mask*Strength;
float vertical=-cell.y*inside*.16*mask*Strength;
return float3(-sin(a)*side,cos(a)*side,vertical);
''', dict(P=local, Strength=scalar(mat, 'FountainFinialDetail', .8)), 3)
        delta = node(mat, u.MaterialExpressionTransform)
        delta.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        delta.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
        wire(facets, delta, '')
        normal, normal_output = originals['NORMAL']
        normal = normal or constant(mat, 'float3(0,0,1)', 3)
        normal_result = custom(mat, 'return normalize(N+Delta);', dict(N=normal, Delta=delta), 3)
        wire(normal, normal_result, 'N', normal_output)
        prop(normal_result, 'NORMAL')
        save(mat)
    instance_path = ROOT+'/MIC_FountainStoneV9'
    instance = u.load_asset(instance_path) if E.does_asset_exist(instance_path) else None
    if not instance:
        instance = TOOLS.create_asset('MIC_FountainStoneV9', ROOT, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        M.set_material_instance_parent(instance, mat)
        if isinstance(surface, u.MaterialInstance):
            for name in M.get_scalar_parameter_names(surface):
                M.set_material_instance_scalar_parameter_value(instance, name, M.get_material_instance_scalar_parameter_value(surface,name))
            for name in M.get_vector_parameter_names(surface):
                M.set_material_instance_vector_parameter_value(instance, name, M.get_material_instance_vector_parameter_value(surface,name))
            for name in M.get_texture_parameter_names(surface):
                texture = M.get_material_instance_texture_parameter_value(surface,name)
                if texture:
                    M.set_material_instance_texture_parameter_value(instance,name,texture)
        save(instance)
    return instance


def step_chamfers(material):
    source_path = '/Game/Props/RomanFountain20260917/SM_RomanFountain_20'
    path = ROOT+'/SM_FountainPolishedV9'
    existing = u.load_asset(path) if E.does_asset_exist(path) else None
    if existing and E.get_metadata_tag(existing,'FountainPolishComplete') == '1':
        return existing
    source = u.load_asset(source_path)
    materials = [source.get_material(i) for i in range(len(source.get_editor_property('static_materials')))]
    materials[0] = material
    svc = u.ModelingService
    handles = []
    def operation(result):
        if not result.success:
            raise RuntimeError(str(result.message))
        return result
    try:
        loaded = operation(svc.load_mesh_from_static_mesh(source_path))
        h = loaded.handle
        handles.append(h)
        # Only the two base step shells: the basin rim and all water are untouched.
        for name, point in [('LowerStep',u.Vector(480,0,10)), ('UpperStep',u.Vector(440,0,30))]:
            if svc.select_connected(h, name, point) <= 0:
                raise RuntimeError('Cannot select '+name)
            operation(svc.delete_faces(h, name))
        steps = operation(svc.create_mesh()).handle
        handles.append(steps)
        profiles = [[(0,0),(479,0),(480,1),(480,19),(479,20),(0,20)],
                    [(0,12),(439,12),(440,13),(440,39),(439,40),(0,40)]]
        for profile in profiles:
            operation(svc.append_revolve_polygon(steps,u.Transform(),[u.Vector2D(r,z) for r,z in profile],0.,96,360.,0))
        operation(svc.recompute_normals(steps,35.))
        operation(svc.auto_uv(steps,'XAtlas',0))
        operation(svc.append_mesh(h,steps,u.Transform()))
        asset = existing or E.duplicate_asset(source_path,path)
        options = u.GeometryScriptCopyMeshToAssetOptions()
        for key,val in dict(enable_recompute_normals=False,enable_recompute_tangents=True,
                            replace_materials=True,new_materials=materials,use_build_scale=False).items():
            options.set_editor_property(key,val)
        _,outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(svc.get_dynamic_mesh(h),asset,options,u.GeometryScriptMeshWriteLOD())
        if outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Could not save polished geometry')
        # Duplicate keeps the source collision policy; triangle collision uses the
        # updated geometry, including the existing open basin/solid support shape.
        E.set_metadata_tag(asset,'FountainPolishComplete','1')
        save(asset)
        REPORT['mesh_edit'] = {'source':source_path,'step_chamfer_cm':1.,'profiles':profiles,'basin_rims':'unchanged'}
        return asset
    finally:
        for h in reversed(handles):
            svc.release_mesh(h)


def import_audio():
    for name in ('FountainBed','FountainDetail'):
        stem = 'S_'+name+'_LoopV9'
        path = ROOT+'/Audio/'+stem
        sound = u.load_asset(path) if E.does_asset_exist(path) else None
        if not sound:
            task = u.AssetImportTask()
            for key,val in dict(filename=str(HERE/'AudioV9'/(stem+'.wav')),destination_path=ROOT+'/Audio',
                                destination_name=stem,automated=True,save=False).items():
                task.set_editor_property(key,val)
            TOOLS.import_asset_tasks([task])
            sound = u.load_asset(path)
        if not sound:
            raise RuntimeError('Failed to import '+stem)
        sound.set_editor_property('looping',True)
        sound.set_editor_property('volume',3.0)  # User requested 3x playback gain; loop samples stay unchanged.
        sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
        sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
        sound.set_editor_property('virtualization_mode',u.VirtualizationMode.DISABLED)
        save(sound)


def integrate_palette(mesh, material):
    # Reload at the point of mutation and update this one entry only.
    palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    entries = list(palette.get_editor_property('components'))
    for entry in entries:
        if str(entry.get_editor_property('id')) == 'roman_fountain':
            entry.set_editor_property('mesh', mesh)
            entry.set_editor_property('surface', material)
            break
    else:
        raise RuntimeError('Fountain entry missing from build palette')
    palette.set_editor_property('components', entries)
    # Save only the source data package, never the live PIE world/instance.
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(palette.get_path_name().split('.')[0])],False):
        raise RuntimeError('Fountain palette package save failed')
    REPORT['assets'].append(palette.get_path_name())


if __name__ == '__main__':
    E.make_directory(ROOT)
    material = stone_material()
    mesh = step_chamfers(material)
    import_audio()
    integrate_palette(mesh, material)
    out = Path(u.Paths.project_saved_dir())/'FountainPolishV9'
    out.mkdir(parents=True,exist_ok=True)
    (out/'authoring.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    print('FOUNTAIN_V9_AUTHORING_COMPLETE')
