"""Save the local forest palette and update the actual streamed ground masters."""
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
BATCH=ROOT/'SourceAssets/HillsRainforestCarpet20261111'
BASE='/Game/WorldGeneration/TemperateHills'
TEX=BASE+'/WetForest/Textures'
TUFT=BASE+'/WetForest/WildGrass'
MATERIAL=TUFT+'/M_WetWildGrass'
DATA=BASE+'/DA_TemperateHillsStreaming'
GROUND=[BASE+'/M_TemperateGround',BASE+'/PebbleShore/M_PebbleShoreGround']
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=[]
variants=('B','D','E')
images={'T_LivingGrass_BaseColor':('TC_DEFAULT',True),'T_LivingGrass_Normal':('TC_NORMALMAP',False),
        'T_LivingGrass_ARH':('TC_MASKS',False),'T_WildTuft_ColorOpacity':('TC_DEFAULT',True)}
owned=[DATA,MATERIAL,*GROUND,*[TEX+'/'+name for name in images],*[TUFT+'/SM_WetGrass_'+v for v in variants]]
if globals().get('ONLY_GROUND_TEXTURES'):
    owned=[TEX+'/'+name for name in images if name.startswith('T_LivingGrass_')]
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Wait for the current play session to end before importing')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(owned):raise RuntimeError('Unsaved target packages: '+repr(dirty.intersection(owned)))
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
for path in owned:
    for ext in ('.uasset','.ubulk','.uexp'):
        src=ROOT/'Content'/(path[6:]+ext)
        if src.is_file():
            dst=BATCH/'Backups'/stamp/(path[6:]+ext)
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)

wet_spec=importlib.util.spec_from_file_location('forest_wet_materials',ROOT/'Tools/WorldGeneration/forest_wet_materials.py')
wet=importlib.util.module_from_spec(wet_spec)
wet_spec.loader.exec_module(wet)

def save(obj):
    if isinstance(obj,u.Material) and L.recompile_material(obj):raise RuntimeError('Material compile request: '+obj.get_name())
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    saved.append(obj.get_path_name())

def import_file(name,ext,directory,cls):
    task=u.AssetImportTask()
    for prop,value in dict(filename=str(BATCH/'Prepared'/(name+ext)),destination_path=directory,
            destination_name=name,automated=True,replace_existing=True,save=False).items():
        task.set_editor_property(prop,value)
    AT.import_asset_tasks([task])
    results=[obj for obj in task.get_objects() if isinstance(obj,cls)]
    if len(results)!=1:raise RuntimeError('Expected one imported '+name+', got '+repr(results))
    obj=results[0]
    target=directory+'/'+name
    if obj.get_path_name().split('.')[0]!=target:
        if not E.rename_loaded_asset(obj,target):raise RuntimeError('Could not name '+target)
    return obj

def import_texture(name,compression,srgb):
    tex=import_file(name,'.png',TEX,u.Texture2D)
    tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,compression))
    tex.set_editor_property('srgb',srgb)
    tex.set_editor_property('never_stream',False)
    if name=='T_WildTuft_ColorOpacity':
        tex.set_editor_property('compression_no_alpha',False)
        tex.set_editor_property('do_scale_mips_for_alpha_coverage',True)
        tex.set_editor_property('alpha_coverage_thresholds',u.Vector4(0,0,0,.28))
    E.set_metadata_tag(tex,'Quixel.ScanId','vlkhcbxia' if name=='T_WildTuft_ColorOpacity' else 'tkynejer')
    save(tex)

if globals().get('ONLY_GROUND_TEXTURES'):
    for name,(compression,srgb) in images.items():
        if name.startswith('T_LivingGrass_'):
            import_texture(name,compression,srgb)
    (BATCH/'Receipts/final-ground.json').write_text(json.dumps({'saved':saved,'scan':'tkynejer',
        'time':datetime.now().astimezone().isoformat()},indent=2),encoding='utf-8')
else:
    for name,(compression,srgb) in images.items():import_texture(name,compression,srgb)
    mat=u.load_asset(MATERIAL) if E.does_asset_exist(MATERIAL) else AT.create_asset('M_WetWildGrass',TUFT,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    mat.set_editor_property('opacity_mask_clip_value',.28)
    mat.set_editor_property('max_world_position_offset_displacement',2.0)
    def n(cls,key):return wet.node(mat,cls,'WildTuft'+key)
    def shader(key,code,**inputs):return wet.custom(mat,'WildTuft'+key,code,inputs,3)
    sample=n(u.MaterialExpressionTextureSample,'Atlas')
    sample.set_editor_property('texture',u.load_asset(TEX+'/T_WildTuft_ColorOpacity'))
    random=n(u.MaterialExpressionPerInstanceRandom,'Variation')
    color=shader('Color','return Atlas.rgb*float3(.87,1.03,.89)*lerp(.87,1.06,R);',Atlas=sample,R=random)
    wet.connect(mat,'BASE_COLOR',color)
    wet.connect(mat,'SUBSURFACE_COLOR',shader('Transmission','return C*float3(.54,.67,.44);',C=color))
    rough=n(u.MaterialExpressionConstant,'Roughness');rough.set_editor_property('r',.68)
    wet.connect(mat,'ROUGHNESS',rough)
    dither=n(u.MaterialExpressionMaterialFunctionCall,'Dither')
    dither.set_editor_property('material_function',u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
    wet.wire(n(u.MaterialExpressionPerInstanceFadeAmount,'Fade'),dither,L.get_material_expression_input_names(dither)[0])
    alpha=n(u.MaterialExpressionMultiply,'Cutout')
    wet.wire((sample,'A'),alpha,'A');wet.wire(dither,alpha,'B');wet.connect(mat,'OPACITY_MASK',alpha)
    wind=n(u.MaterialExpressionCollectionParameter,'ForestWind')
    wind.set_editor_property('collection',u.load_asset(wet.MPC));wind.set_editor_property('parameter_name','ForestWind')
    p=n(u.MaterialExpressionWorldPosition,'Position')
    p.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    local=n(u.MaterialExpressionPreSkinnedPosition,'Local')
    wpo=shader('Wind','''
    float tip=saturate(Local.z/25);
    float wave=sin(T*2.1+P.x*.006+P.y*.009);
    return float3(W.xy*(W.z*1.25*tip*tip*wave),0);
    ''',Local=local,T=n(u.MaterialExpressionTime,'Time'),P=p,W=wind)
    wet.connect(mat,'WORLD_POSITION_OFFSET',wpo);save(mat)

    palette=[]
    for variant in variants:
        mesh=import_file('SM_WetGrass_'+variant,'.glb',TUFT,u.StaticMesh)
        box=mesh.get_bounding_box()
        size=box.max-box.min
        if not (48<max(size.x,size.y)<85 and 12<size.z<41):
            raise RuntimeError('Unexpected imported metre conversion: '+mesh.get_name()+' '+str(size))
        if not mesh.get_editor_property('static_materials'):
            slot=u.StaticMaterial();slot.set_editor_property('material_interface',mat)
            slot.set_editor_property('material_slot_name','Grass')
            mesh.set_editor_property('static_materials',[slot])
        else:mesh.set_material(0,mat)
        opts=u.StaticMeshReductionOptions()
        opts.set_editor_property('auto_compute_lod_screen_size',False)
        rows=[]
        for fraction,screen in [(1.,1.),(.55,.042),(.24,.016)]:
            row=u.StaticMeshReductionSettings()
            row.set_editor_property('percent_triangles',fraction);row.set_editor_property('screen_size',screen);rows.append(row)
        opts.set_editor_property('reduction_settings',rows);SM.set_lods(mesh,opts)
        SM.remove_collisions(mesh)
        save(mesh);palette.append(mesh)
    for path in GROUND:
        ground=u.load_asset(path)
        wet.apply_ground(ground);save(ground)
    # An older terrain rebuild must keep the currently authored blade palette.
    underfoot=BASE+'/WetForest/Underfoot/SM_'
    folded=[underfoot+name for name in ('LowSward','RibbonGrass','BankSedge')]
    if all(E.does_asset_exist(path) for path in folded):
        palette=[E.load_asset(path) for path in folded]
    da=u.load_asset(DATA);da.set_editor_property('rainforest_grass',palette);save(da)
    (BATCH/'Receipts/saved.json').write_text(json.dumps({'time':datetime.now().astimezone().isoformat(),
        'saved':saved,'rainforest_grass':[m.get_name() for m in palette],'playtested':False},indent=2),encoding='utf-8')
    u.log('RAINFOREST_CARPET_SAVED '+str(len(saved)))
