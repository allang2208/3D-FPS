"""Author irregular blue blade fire and a bounded, reusable shortcut icon. No PIE."""
from pathlib import Path
import json,sys
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
sys.path.insert(0,str(OUT.parent))
import author_flame_armor_fireball_v3 as fire
from author_flame_armor_v2 import API,LIB,ref,setdata,put,assignments,user_parameter,FLOAT,VEC2,VEC3,VEC4,COLOR
from install_flames import blue
DEST='/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103'
SYSTEM=DEST+'/NS_StarMarrowCharge'

def hash_value(value):return 'frac(sin(('+value+')*12.9898)*43758.5453)'
def seed(channel,salt):return hash_value(f'float(Particles.UniqueID)*{1.+channel*.377:.5f}+User.VariationSeed*.713+{salt+channel*31.47:.5f}')
def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

def author_layer(system,name,kind,rate,salt):
    h=[seed(i,salt) for i in range(5)]
    # Shared irregular burn patches, plus loose tongues over the entire blade.
    # IDs choose a stable patch/shape for life; nothing is re-rolled per frame.
    center='(.13+.74*'+hash_value(f'floor({h[0]}*3.)*17.7+User.VariationSeed*.193')+')'
    station=f'({h[1]}<.72?clamp({center}+({h[2]}-.5)*.19,.05,.96):(.05+.91*{h[2]}))'
    along='normalize(User.WeaponEnd+float3(.0001,0,0))'
    side=f'normalize(cross({along},abs({along}.z)<.9?float3(0,0,1):float3(0,1,0)))'
    angle=f'({h[3]}*6.2831853)'
    across=f'({side}*cos({angle})+cross({along},{side})*sin({angle}))'
    point=f'User.WeaponEnd*{station}+{across}*(.35+1.9*{h[4]})*User.FlameProfile.x'
    up=f'normalize(float3(0,0,1)-User.WeaponVelocity*.00045+{across}*(.08+.34*{h[0]}))'
    age='Particles.Age';n='Particles.NormalizedAge'
    curl=f'{across}*sin({age}*(4.5+5.*{h[3]})+{angle})*{age}*(2.+4.*{h[1]})*User.WeaponSize'
    rise=f'{point}+{up}*(.4+{age}*(5.+13.*{h[2]}))*User.WeaponSize+{curl}'
    wave=f'(.72+.18*sin(User.FlameClock*2.17+User.VariationSeed*.11+{salt})+.10*sin(User.FlameClock*4.63+{salt*.73:.3f}))'
    density=f'User.Detail*(.65+.35*saturate(User.Coverage))*{wave}'
    life=f'.38+.52*{h[1]}';size=f'float2(20*(.48+.90*{h[3]}),42*(.55+.95*{h[4]}))*User.WeaponSize*User.FlameProfile.xy'
    spawn=point;update=rise;local=True;opacity=f'User.Fade*(.65+.30*{h[2]})';velocity='float3(0,0,0)'
    if kind=='core':
        life=f'.44+.58*{h[1]}';size=f'float2(11*(.55+.85*{h[3]}),25*(.60+.65*{h[4]}))*User.WeaponSize'
        update=point;up=along;opacity=f'User.Fade*(.38+.27*{h[2]})'
    elif kind=='curl':
        life=f'.46+.47*{h[1]}';size=f'float2(24*(.6+.65*{h[3]}),28*(.65+.8*{h[4]}))*User.WeaponSize*User.FlameProfile.xy'
        opacity=f'User.Fade*(.38+.25*{h[2]})'
    elif kind in ('motion','ember'):
        local=False
        spawn=f'lerp(lerp(User.PreviousStart,User.PreviousEnd,{station}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,{station}),{h[0]})'
        update='Particles.Position+Particles.Velocity*Engine.DeltaTime'
        velocity=f'User.WeaponVelocity*.055+float3(cos({angle})*(4.+8.*{h[4]}),sin({angle})*(4.+8.*{h[4]}),12.+19.*{h[2]})'
        life=f'.13+.21*{h[1]}';size=f'float2(13*(.5+{h[3]}),31*(.65+.8*{h[4]}))*User.WeaponSize*(1-{n}*.6)'
        opacity=f'User.Fade*(.40+.27*{h[2]})'
        if kind=='motion':density+='*User.MotionEnergy*User.FlameProfile.z'
        else:
            size=f'float2(.6,1.6)*(.5+{h[3]})';up='normalize(Particles.Velocity+float3(0,0,.1))'
    fire.V=h[2]
    fire.layer(system,name,'flame' if kind=='motion' else kind,rate,local,life,spawn,update,size,opacity,axis=up,velocity=velocity,scale=density)
    extra={
        'Particles.SpriteRotation':(FLOAT,f'({h[3]}-.5)*(.28+.25*{h[1]})'),
        'Particles.MaterialRandom':(FLOAT,h[4]),
    }
    if kind in ('flame','motion'):
        erosion=f'saturate(({n}-(.20+.18*{h[1]}))/(.80-.18*{h[1]}))'
        smooth_erosion=f'({erosion}*{erosion}*(3.-2.*{erosion}))'
        extra['Particles.DynamicMaterialParameter']=(VEC4,f'float4(.015+.18*{h[0]}+(.48+.27*{h[4]})*{smooth_erosion},1,1,1)')
    if kind=='curl':
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
            'SubImageSize':{'X':6,'Y':6},'bSubImageBlend':True,'PivotInUVSpace':{'X':.5,'Y':.64}})
        extra['Particles.SubImageIndex']=(FLOAT,f'min(35.,{n}*(24.+11.*{h[4]}))')
        extra['Particles.DynamicMaterialParameter']=(VEC4,f'float4({h[2]},.7+1.1*{h[1]}+{n}*.6,0,0)')
    for stage in ['ParticleSpawnScript','ParticleUpdateScript']:assignments(system,name,stage,extra)

def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before saving charge fire and icon')
    targets={SYSTEM,DEST+'/M_StarMarrowBlueRoll',DEST+'/T_StarMarrowChargeIcon'}
    if targets.intersection(p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved changes to charge fire/icon')
    system=u.load_asset(SYSTEM)
    if system is None:raise RuntimeError('Install base blue flame system first')
    roll=u.load_asset(DEST+'/M_StarMarrowBlueRoll')
    if roll is None:roll=u.EditorAssetLibrary.duplicate_asset('/Game/Skills/FireMagic20260921/RealisticV5/M_NaturalRollingFlame',DEST+'/M_StarMarrowBlueRoll')
    if roll is None:raise RuntimeError('Rolling flame donor is missing')
    blue(roll)
    fire.MATERIALS={'core':DEST+'/M_StarMarrowBlueCore','flame':DEST+'/MI_StarMarrowBlueFlame',
        'curl':DEST+'/M_StarMarrowBlueRoll','ember':DEST+'/M_StarMarrowBlueEmber'}
    for parameter in ['VariationSeed','FlameClock']:user_parameter(system,parameter,FLOAT)
    layers=[('WeaponFireballCore','core',7,11.),('WeaponFireballTongues','flame',20,23.),
        ('WeaponFireballCurls','curl',10,39.),('MotionFireballFlame','motion',16,53.),('WeaponEmbers','ember',6,79.)]
    for args in layers:author_layer(system,*args)
    if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Charge fire Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system,'StarMarrow.Revision','IrregularBlueFireV2-20261104');save(system)
    icon_path=DEST+'/T_StarMarrowChargeIcon'
    icon=u.load_asset(icon_path)
    if icon is None:
        task=u.AssetImportTask();task.set_editor_property('filename',str(ROOT/'Content/ColdSteelData/AttachmentIcons20260913/ue_frost_crystal_sword_blade_1_star_marrow.png'))
        task.set_editor_property('destination_path',DEST);task.set_editor_property('destination_name','T_StarMarrowChargeIcon')
        task.set_editor_property('automated',True);task.set_editor_property('save',False)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);icon=u.load_asset(icon_path)
    if icon is None:raise RuntimeError('Charge shortcut icon import failed')
    icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    icon.set_editor_property('max_texture_size',256);icon.set_editor_property('never_stream',True);save(icon)
    receipt=dict(saved_assets=[system.get_path_name(),roll.get_path_name(),icon.get_path_name()],
        emitters=len(layers),max_spawn_rate=sum(row[2] for row in layers),lights_added=0,
        icon_source='existing approved StarMarrow blade icon',icon_max_size=256,gameplay_tested=False,rendered=False)
    (OUT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('STAR_MARROW_VARIATION_AND_ICON_SAVED',receipt)

if __name__=='__main__':run()
