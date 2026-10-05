"""Improve only the M25 back discharge presentation and save the existing BP."""
from pathlib import Path
import json, traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Monsters/VortexCofferM25'
DEST=BASE+'/VFX/NS_M25_BackElectric'
BP=BASE+'/BP_VortexCofferM25'
REV='M25BackElectric20261004V2'
EAL=u.EditorAssetLibrary
MAT=u.MaterialEditingLibrary
API=u.get_default_object(u.NiagaraToolset_System)
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False,rendered=False)
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    EAL.set_metadata_tag(asset,'M25.ElectricRevision',REV)
    if not EAL.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    record['saved'].append(asset.get_path_name());receipt()
def ref(s,e,stage='',module='',renderer=-1):
    r=u.NiagaraExt_StackItemReference()
    for key,value in dict(system=s,emitter_name=e,script_name=stage,module_name=module,renderer_index=renderer).items():
        r.set_editor_property(key,value)
    return r
def put(s,e,stage,module,name,value,typ='/Script/Niagara.NiagaraFloat'):
    if not u.RainAssetEditor.set_input(s,e,stage,module,name,typ,value):
        raise RuntimeError('Cannot author '+e+'/'+module+'/'+name)
def data(method,typ,r,values):
    d=typ();d.set_editor_property('property_values',json.dumps(values))
    API.call_method(method,(r,d))
def ribbon_material():
    name='M_M25_BackElectricRibbon_V02';path=BASE+'/VFX/'+name
    if EAL.does_asset_exist(path):
        m=u.load_asset(path)
        if EAL.get_metadata_tag(m,'M25.ElectricRevision')!=REV:raise RuntimeError('Preserve unowned '+path)
    else:m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE+'/VFX',u.Material,u.MaterialFactoryNew())
    MAT.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('disable_depth_test',False)
    MAT.set_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_RIBBONS)
    uv=MAT.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
    clock=MAT.create_material_expression(m,u.MaterialExpressionTime)
    particle=MAT.create_material_expression(m,u.MaterialExpressionParticleColor)
    shape=MAT.create_material_expression(m,u.MaterialExpressionCustom)
    shape.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    # Keep a luminous filament at every point. The inherited travelling mask could
    # reduce the small back connection to isolated sparks; motion modulates, never erases.
    shape.set_editor_property('code',
        'float edge=pow(saturate(1.0-abs(UV.y*2.0-1.0)),1.35);'
        'float flow=.82+.18*sin(UV.x*85.0-Clock*28.0);return edge*flow;')
    pins=[]
    for name,node in [('UV',uv),('Clock',clock)]:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    shape.set_editor_property('inputs',pins)
    MAT.connect_material_expressions(uv,'',shape,'UV')
    MAT.connect_material_expressions(clock,'',shape,'Clock')
    opacity=MAT.create_material_expression(m,u.MaterialExpressionMultiply)
    MAT.connect_material_expressions(shape,'',opacity,'A')
    MAT.connect_material_expressions(particle,'A',opacity,'B')
    MAT.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    MAT.connect_material_property(particle,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=MAT.recompile_material(m)
    if errors:raise RuntimeError('M25 ribbon material compilation failed: '+str(errors))
    save(m);return m
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve session and defer M25 asset writes')
    if any(p.get_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved M25 assets')
    system=u.load_asset(DEST)
    if not system:raise RuntimeError('Existing M25 Niagara missing')
    if EAL.get_metadata_tag(system,'M25.ElectricRevision') not in ('M25BackElectric20261004V1',REV):
        raise RuntimeError('M25 effect has different ownership/revision')
    material=ribbon_material()
    for emitter in ('Currency','MainPower'):
        width='3.4' if emitter=='Currency' else '1.1'
        put(system,emitter,'ParticleSpawnScript','InitializeParticle','Ribbon Width',
            '(HlslExpression="User._Width * '+width+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(system,emitter,'ParticleSpawnScript','InitializeParticle','Lifetime','(Value=2.0)')
        data('SetRendererData',u.NiagaraExt_RendererData,ref(system,emitter,renderer=0),
            {'Material':material.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
             'FacingMode':'Screen','bCastShadows':False})
        top=API.call_method('GetEmitterTopology',(ref(system,emitter),))
        modules={str(m.get_editor_property('module_name')) for m in top.get_editor_property('particle_update_script').get_editor_property('modules')}
        if 'ScaleColor002' in modules:API.call_method('RemoveModule',(ref(system,emitter,'ParticleUpdateScript','ScaleColor002'),))
        if 'ScaleColor' not in modules:
            API.call_method('AddModule',(ref(system,emitter,'ParticleUpdateScript'),u.load_asset('/Niagara/Modules/Update/Color/ScaleColor.ScaleColor')))
        put(system,emitter,'ParticleUpdateScript','ScaleColor','ScaleRGB','(Value=-1)','/Script/Niagara.NiagaraBool')
        put(system,emitter,'ParticleUpdateScript','ScaleColor','ScaleA','(Value=-1)','/Script/Niagara.NiagaraBool')
        put(system,emitter,'ParticleUpdateScript','ScaleColor','Scale RGB',
            '(HlslExpression="float3(User._Brightness, User._Brightness, User._Brightness)")',
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(system,emitter,'ParticleUpdateScript','ScaleColor','Scale Alpha','(Value=1.0)')
    # Spline interface binding is applied after compilation replaces interface defaults.
    if not u.RainAssetEditor.bind_spline_user_object(system,'User.M25Spline'):
        raise RuntimeError('M25 Niagara compile/spline binding failed')
    EAL.set_metadata_tag(system,'M25.Presentation','V2 continuous white-blue filament/halo, brightness 54 width 2.4; four pooled lanes')
    save(system)
    bp=u.load_asset(BP);u.BlueprintEditorLibrary.compile_blueprint(bp)
    component=u.get_default_object(bp.generated_class()).get_editor_property('back_electric')
    for key,value in dict(electric_enabled=True,arc_asset=system,brightness=54.,width=2.4,max_draw_distance=5500.).items():
        component.set_editor_property(key,value)
    save(bp)
    record.update(stage='assets_saved',brightness=54,width=2.4,core_width_cm=2.64,halo_width_cm=8.16,
        max_draw_distance_cm=5500,emitters=2,particles_per_lane=128,max_lanes=4,
        max_particles_per_monster=512,material=material.get_path_name())
    receipt();u.log('M25_BACK_ELECTRIC_V02_SAVED')
try:main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
