"""Private native rune materials: preserve each blade's PBR and follow its contour."""
import json,shutil,runpy
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
D='/Game/Weapons/Zhanmadao20261018/RuneSurfaceV1/Materials'
E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
host=Path(u.Paths.project_dir()).resolve()
staging='-zhanstageonly' in u.SystemLibrary.get_command_line().lower()
if host!=ROOT and not (staging and host==P/'AssetHost'):raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('Preserved game/PIE process; use an authoring commandlet')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D):raise RuntimeError('Preserved unsaved target package: '+package.get_name())
catalog_path=DATA/'zhanmadao-modules.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
source_file=P/'source_bindings.json'
if not source_file.exists():
    sources={key:part.get('materials',{'M_Zhanmadao_Surface_V1':'/Game/Weapons/Zhanmadao20261018/V1/Materials/M_Zhanmadao_Surface_V1'})
        for key,part in catalog['slots']['blade_1'].items()}
    source_file.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sources=json.loads(source_file.read_text(encoding='utf-8'))
layouts=json.loads((P/'layouts.json').read_text(encoding='utf-8'))
if '-zhanfreshmaterialsonly' in u.SystemLibrary.get_command_line().lower():
    for key in layouts:
        for index in range(len(sources[key])):
            target=D+'/M_TangDaoBladeRuneSurface_Zhanmadao_'+key+'_'+str(index)+'_V1'
            for path in [target,target+'_Whirlwind']:
                if L.does_asset_exist(path):raise RuntimeError('Fresh-only batch preserves existing package: '+path)
receipt={'complete':False,'assets_saved':False,'assets':[],'bindings':{},'temporal_bindings':{},
    'native_code_changed':False,'game_tested':False,'pbr_preserved':True,'geometry_changed':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required source missing: '+path)
    return asset
def connect(a,output,b,pin):
    if not E.connect_material_expressions(a,output,b,'' if pin is None or str(pin)=='None' else str(pin)):
        raise RuntimeError('Material connection failed: '+str(pin))
def save(asset):
    errors=list(E.recompile_material(asset) or [])
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    L.set_metadata_tag(asset,'ZhanmadaoRuneSurfaceRevision','BladeContourV1')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Asset save failed')
    receipt['assets'].append(asset.get_path_name());record()
def add_native_runes(material):
    source=load('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2')
    originals=list(E.get_material_expressions(source))
    copies={node.get_name():E.duplicate_material_expression(material,None,node) for node in originals}
    for node in originals:
        for input_node,name in zip(E.get_inputs_for_material_expression(source,node),E.get_material_expression_input_names(node)):
            if input_node:connect(copies[input_node.get_name()],'',copies[node.get_name()],name)
    rgb=E.get_material_property_input_node(source,u.MaterialProperty.MP_EMISSIVE_COLOR)
    coverage=E.get_material_property_input_node(source,u.MaterialProperty.MP_OPACITY)
    emission=copies[rgb.get_name()];opacity=copies[coverage.get_name()]
    multiply=E.create_material_expression(material,u.MaterialExpressionMultiply)
    if isinstance(rgb,u.MaterialExpressionEyeAdaptationInverse):
        original_input=E.get_inputs_for_material_expression(source,rgb)[0]
        connect(copies[original_input.get_name()],'',multiply,'A');connect(opacity,'',multiply,'B')
        connect(multiply,'',emission,E.get_material_expression_input_names(emission)[0])
    else:
        connect(emission,'',multiply,'A');connect(opacity,'',multiply,'B');emission=multiply
    front=E.get_material_property_input_node(material,u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unsupported PBR front node')
    connect(emission,'',front,'Emissive Color')
    if not E.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emissive output missing')
def place(material,key):
    changed=0
    for node in E.get_material_expressions(material):
        if not isinstance(node,u.MaterialExpressionCustom):continue
        code=node.get_editor_property('code')
        if 'RuneTexture' not in code or 'RuneMode' not in code:continue
        inputs={str(pin.get_editor_property('input_name')) for pin in node.get_editor_property('inputs')}
        needed={'P','N','BladeOrigin','BladeAxis','Dimensions','RuneOpacity','HaloOpacity'}
        if not needed.issubset(inputs):raise RuntimeError('Unexpected native rune inputs: '+str(inputs))
        if 'ZHANMADAO_BLADE_CONTOUR_V1' in code:continue
        snapshot=P/'SourceShaders'/(material.get_name()+'_'+node.get_name()+'.hlsl');snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(code,encoding='utf-8')
        node.set_editor_property('code',(P/(key+'_placement.hlsl')).read_text(encoding='utf-8')+'\n'+code)
        changed+=1
    if not changed:raise RuntimeError('No native rune shader was authored for '+material.get_path_name())
for key in layouts:
    receipt['bindings'][key]={}
    for index,(slot,source_path) in enumerate(sources[key].items()):
        # This is the existing native blade-rune family consumed by held,
        # workbench and dropped modular swords, with private Zhanmadao PBR.
        name='M_TangDaoBladeRuneSurface_Zhanmadao_'+key+'_'+str(index)+'_V1'
        target=D+'/'+name
        material=u.load_asset(target)
        if not material:
            source=load(source_path);material=L.duplicate_asset(source.get_path_name(),target)
            if not material:raise RuntimeError('Material duplication failed')
            if not source.get_name().startswith('M_TangDaoBladeRuneSurface'):add_native_runes(material)
            place(material,key);E.layout_material_expressions(material)
        elif L.get_metadata_tag(material,'ZhanmadaoRuneSurfaceRevision')!='BladeContourV1':
            raise RuntimeError('Preserved unfinished target material: '+target)
        save(material)
        temporal_path=target+'_Whirlwind';temporal=u.load_asset(temporal_path)
        if not temporal:
            temporal=L.duplicate_asset(material.get_path_name(),temporal_path)
            if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(temporal)):
                output=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
                one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
                connect(one,'',output,'')
        save(temporal)
        receipt['bindings'][key][slot]=material.get_path_name()
        receipt['temporal_bindings'][material.get_path_name()]=temporal.get_path_name()
if staging:
    receipt.update(staged_assets_saved=True,stage_project=str(host),assets_saved=False)
    record();print('ZHANMADAO_NATIVE_RUNES_STAGED '+json.dumps(receipt),flush=True)
else:
    receipt['assets_saved']=True;record()
    catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
    catalog=runpy.run_path(str(P/'catalog_extension.py'))['extend'](catalog)
    map_path=DATA/'whirlwind-temporal-materials.json';mapping=json.loads(map_path.read_text(encoding='utf-8-sig'))
    mapping.update(receipt['temporal_bindings'])
    for file,data in [(catalog_path,catalog),(map_path,mapping)]:
        backup=P/'Before'/file.name;backup.parent.mkdir(exist_ok=True)
        if not backup.exists():shutil.copy2(file,backup)
        tmp=file.with_suffix('.zhan-runes.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(file)
    receipt.update(complete=True,catalog_saved=True,blade_choices=list(layouts),runes=['strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune'])
    record();print('ZHANMADAO_NATIVE_CONTOUR_RUNES_SAVED '+json.dumps(receipt),flush=True)
