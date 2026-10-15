"""Create M66-only copies of the current Dragon Breath volume and palette."""
import json,sys,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FurnaceBreathV17');DEST='/Game/Monsters/IncineratorBossM66/FurnaceBreathV17'
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,setdata,put,assignments
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();saved=[]
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before saving M66 furnace assets')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('M66 furnace packages have unsaved changes')
def copy(source,name):
    a=u.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else A.duplicate_asset(name,DEST,u.load_asset(source))
    if not a:raise RuntimeError('Missing effect source '+source)
    return a
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('M66 effect save failed '+asset.get_path_name())
    saved.append(asset.get_path_name())
SOURCE='/Game/Skills/DragonBreath20261013/VolumeV8'
system=copy(SOURCE+'/NS_DragonVolume','NS_M66FurnaceBreath')
base=copy(SOURCE+'/M_DragonVolumeFlame_R2','M_M66FurnaceVolume');mi=copy(SOURCE+'/MI_DragonVolumeFlame_R2','MI_M66FurnaceVolume')
ramps=[n for n in u.ObjectIterator(u.MaterialExpressionCustom) if n.get_outer()==base and str(n.get_editor_property('desc'))=='DragonVolume.ColorRamp.R2']
if len(ramps)!=1:raise RuntimeError('Current Dragon volume palette node differs')
ramps[0].set_editor_property('code','''
float heat=max(Temperature-ColorMin,0)/max(ColorMax-ColorMin,.001);
float t=1-exp2(-heat*1.35);
float3 c=lerp(float3(0,0,0),float3(.18,.010,.003),smoothstep(0,.08,t));
c=lerp(c,float3(.75,.065,.009),smoothstep(.06,.42,t));
c=lerp(c,float3(1.45,.24,.025),smoothstep(.40,.82,t));
return lerp(c,float3(1.9,.62,.11),smoothstep(.82,1,t));
''')
L.set_material_instance_parent(mi,base);L.update_material_instance(mi)
errors=L.recompile_material(base)
if errors:raise RuntimeError(str(errors))
if not u.PoisonMaggotMonster.compile_material_assets([base,mi]):raise RuntimeError('M66 furnace material compilation failed')
save(base);save(mi)
GRID='Grid3D_Gas_Master_Emitter';EXPR='/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
for name,expr in [('Density Gain','.13*saturate(User.Strength)'),('Temperature Color Gain','.28*saturate(User.Strength)'),('Temperature Opacity Gain','.52*saturate(User.Strength)')]:
    put(system,GRID,'EmitterUpdateScript','Grid3D_Gas_MaterialControls',name,'(HlslExpression="'+expr+'")',EXPR)
put(system,GRID,'EmitterUpdateScript','Grid3D_Gas_MaterialControls','Density Albedo','(Value=.035)')
setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,GRID,renderer=1),{'Material':mi.get_path_name(),'StepFactor':.85,'LightingDownsampleFactor':2.,'ShadowStepFactor':3.})
# Preserve the Dragon jet's wall-distance clipping, world-space births and
# transform compensation. Broaden its small vertical opening for a large mouth.
seed='frac((float(Particles.UniqueID)+.5)*.61803398875)';variant='frac((float(Particles.UniqueID)+.5)*.41421356237)'
yaw=f'(({seed}<.7)?(({seed}/.7-.5)*.24):((({seed}-.7)/.3-.5)*2*User.HalfAngle*.95))'
direction=f'normalize(User.Forward*cos({yaw})+User.Side*sin({yaw})+User.Up*(({variant}-.5)*.28))'
ray=f'clamp(int(floor(({yaw}/max(.01,User.HalfAngle)+1)*4+.5)),0,8)';limit='User.Ray8'
for i in reversed(range(8)):limit=f'(({ray}=={i})?User.Ray{i}:{limit})'
FLOAT='/Script/Niagara.NiagaraFloat';VEC3='/Script/CoreUObject.Vector3f'
assignments(system,'ParticleSourceEmitter','ParticleSpawnScript',{
    'Particles.JetDirection':(VEC3,direction),'Particles.Velocity':(VEC3,f'{direction}*2805'),
    'Particles.JetSpeed':(FLOAT,'2805'),'Particles.JetLimit':(FLOAT,f'min(User.Range,{limit})'),
    'Particles.JetCore':(FLOAT,f'({seed}<.7)?1:.42'),
    'Particles.Lifetime':(FLOAT,f'clamp(min(User.Range,{limit})/2805+.035,.05,.55)')})
edge='saturate((Particles.JetLimit-Particles.Age*Particles.JetSpeed)/max(25,User.CellSize*2))'
put(system,'ParticleSourceEmitter','ParticleUpdateScript','SetFluidSourceAttributes','Density','(HlslExpression=".18*'+edge+'")',EXPR)
E.set_metadata_tag(system,'M66.Furnace','V17: independent Dragon Volume R5 copy; dark ash/red embers; 80 axis runtime grid, 9 ray clipping')
if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('M66 furnace Niagara compilation failed')
save(system)

glow=u.load_asset(DEST+'/M_M66FurnaceGlow') if E.does_asset_exist(DEST+'/M_M66FurnaceGlow') else A.create_asset('M_M66FurnaceGlow',DEST,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(glow);glow.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE);glow.set_editor_property('two_sided',True)
def node(cls):return L.create_material_expression(glow,cls)
def wire(a,b,pin):
    if not L.connect_material_expressions(a,'',b,pin):raise RuntimeError('Furnace glow wire '+pin)
uv=node(u.MaterialExpressionTextureCoordinate);power=node(u.MaterialExpressionScalarParameter);power.set_editor_property('parameter_name','Intensity');power.set_editor_property('default_value',0.)
shape=node(u.MaterialExpressionCustom);shape.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
pins=[]
for name in ('UV','Power'):
    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
shape.set_editor_property('inputs',pins);shape.set_editor_property('code','float2 p=(UV-.5)*2; float r=length(p); float folds=.8+.2*sin(p.y*27+p.x*15); return saturate(pow(saturate(1-r),1.8)*folds*Power*.7);')
wire(uv,shape,'UV');wire(power,shape,'Power')
color=node(u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(2.,.16,.012,1))
lit=node(u.MaterialExpressionMultiply);wire(color,lit,'A');wire(shape,lit,'B');trans=node(u.MaterialExpressionOneMinus);wire(shape,trans,'')
surface=node(u.MaterialExpressionSubstrateUnlitBSDF);wire(lit,surface,'EmissiveColor');wire(trans,surface,'TransmittanceColor')
if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Furnace glow output')
L.layout_material_expressions(glow);errors=L.recompile_material(glow)
if errors:raise RuntimeError(str(errors))
if not u.PoisonMaggotMonster.compile_material_assets([glow]):raise RuntimeError('Furnace glow compilation failed')
save(glow)
att=u.load_asset(DEST+'/ATT_M66Furnace') if E.does_asset_exist(DEST+'/ATT_M66Furnace') else A.create_asset('ATT_M66Furnace',DEST,u.SoundAttenuation,u.SoundAttenuationFactory())
settings=att.get_editor_property('attenuation');settings.set_editor_property('attenuate',True);settings.set_editor_property('spatialize',True)
settings.set_editor_property('attenuation_shape_extents',u.Vector(250,0,0));settings.set_editor_property('falloff_distance',2200.)
att.set_editor_property('attenuation',settings);save(att)
task=u.AssetImportTask();task.filename=str(ROOT/'Export/M66_furnace_inhale.wav');task.destination_path=DEST;task.destination_name='S_M66FurnaceInhale';task.automated=True;task.replace_existing=True;task.save=False
A.import_asset_tasks([task]);inhale=u.load_asset(DEST+'/S_M66FurnaceInhale');release=copy('/Game/Skills/FireMagic20260921/S_FireMagicCast','S_M66FurnaceRelease')
for sound in (inhale,release):
    sound.set_editor_property('attenuation_settings',att);save(sound)
report={'complete':True,'saved':saved,'source_system':SOURCE+'/NS_DragonVolume','player_assets_modified':False,'grid_axis':80,'visible_flame_sprites':0,'runtime_tested':False,'rendered':False,'auditioned':False}
(ROOT/'Records/effect_install.json').write_text(json.dumps(report,indent=2));print('M66_FURNACE_EFFECTS_SAVED '+json.dumps(report))
