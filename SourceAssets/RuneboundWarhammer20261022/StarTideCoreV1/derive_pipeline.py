"""Adapt the repaired violet orb material/import contract to Star Tide assets."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P.parent/'ManaOrbPommelV2/import_assets.py').read_text('utf-8')
for before,after in [
 ('ManaOrbPommelV2','StarTideCoreV1'),('M_ManaOrbV2_','M_StarTide_'),('T_ManaOrbV2_','T_StarTide_'),
 ('M_RuneboundManaOrb_GemV2','M_RuneboundManaOrb_StarTide_Gem'),
 ('M_RuneboundManaOrb_RuneV2','M_RuneboundManaOrb_StarTide_Rune'),
 ('M_RuneboundManaOrb_VolumeV2','M_RuneboundManaOrb_StarTide_Volume'),
 ('M_RuneboundManaOrb_CoreV2','M_RuneboundManaOrb_StarTide_Core'),
 ('M_RuneboundManaOrb_FilamentsV2','M_RuneboundManaOrb_StarTide_Filaments'),
 ('M_RuneboundManaOrb_ParticlesV2','M_RuneboundManaOrb_StarTide_Particles'),
 ('-8.7','-8.0'),('empowered_mana_orb','star_tide_core'),('MANA_ORB_V2_ASSETS_SAVED','STAR_TIDE_ASSETS_SAVED'),
 ("server awakening duration +10 seconds","server active awakening +0.5 seconds per damaging target contact; uncapped"),
 ('24-step local nebula, 5 orbiting solid filaments, 32 solid sparks','24-step blue nebula, 4 double-helix currents, 48 contained stars'),
 ('(.065,.009,.17)','(.004,.035,.14)'),('(.10,.004,.28)','(.003,.12,.55)'),('(.065,.002,.18)','(.001,.022,.11)'),
 ('(.085,.015,.22)','(.006,.065,.21)'),('(.24,.055,.60)','(.006,.13,.42)'),('(.55,.22,1.)','(.14,.50,1.)'),
 ('(.32,.012,.86)','(.008,.25,.95)'),('(.06,.002,.18)','(.002,.025,.10)'),
 ('(.65,.24,1.)','(.18,.55,1.)'),('(.15,.025,.3)','(.02,.06,.15)'),
 ('(.12,.003,.4)','(.002,.05,.22)'),('(.65,.17,1.1)','(.12,.55,1.3)'),('(.02,0,.05)','(.001,.012,.03)'),
 ('(.48,.075,1.)','(.07,.32,1.)'),('(.03,.001,.08)','(.001,.01,.03)'),
 ('(1.15+Awake*1.15)','(1.15+Awake*1.15+Impact*.7)'),('(3.8+Awake*2.4)','(3.8+Awake*2.4+Impact*2.)'),
 ('(1.6+Awake)','(1.6+Awake+Impact*.7)'),('(1.+Awake*.8)','(1.+Awake*.8+Impact*.6)'),
 ]:s=s.replace(before,after)
s=s.replace("return node(mat,u.MaterialExpressionTime),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.)",
 "return node(mat,u.MaterialExpressionTime),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.),node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneImpact',default_value=0.)")
s=s.replace('time,awake=glow_parameters(m)','time,awake,impact=glow_parameters(m)').replace("'Awake':awake","'Awake':awake,'Impact':impact")
compile_stage='''# Compile the actual current-RHI shader resources, not only the asset graph.
# This is production shader compilation; it starts no game or acceptance view.
receipt['gpu_compilation']={}
for key,value in materials.items():
    stats=L.get_statistics(value)
    receipt['gpu_compilation'][key]={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions}
    record()
    if stats.num_pixel_shader_instructions<=0:
        raise RuntimeError('No compiled pixel shader for '+key+'; use the rendering-enabled SM6 author host')

'''
s=s.replace("u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')",compile_stage+"u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')")
(P/'import_assets.py').write_text(s,encoding='utf-8')

# The publisher reads the current catalogs before making only this part's edit.
s=(P.parent/'ManaOrbPommelV2/publish.py').read_text('utf-8-sig')
s=s.replace('empowered_mana_orb','star_tide_core').replace('强化魔力球','星潮之核').replace('ManaOrbPommelV2','StarTideCoreV1')
s=s.replace('外露紫晶球由黑银雕刻护爪托持，球内能量云、流光与微粒围绕魔力核心旋转。','深蓝晶球由交错黑银弧架与符文环轨托持，蓝晶嵌窗依次明灭，双螺旋光流在球内循环。')
s=s.replace('外露紫晶球 · 雕刻黑银护爪 · 内部魔力旋流','深蓝晶球 · 交错弧架与蓝晶环轨 · 球内双螺旋光流')
s=s.replace('延续苏醒｜符文苏醒持续时间增加10秒，由20秒延长至30秒。','星潮续醒｜符文唤醒期间，每次命中目标使持续时间增加0.5秒，持续时间无上限。')
start=s.index("        for trait in value.get('traits',[]):")
end=s.index("    backup=P/'Before'/relative",start)
s=s[:start]+s[end:]
s=s.replace("'duration_seconds':30,'base_duration_seconds':20", "'extension_per_hit_seconds':0.5,'duration_cap_seconds':None,'base_duration_seconds':20")
s=s.replace("P.parent/'ManaOrbPommelConceptV2/design.json'","P.parent/'EverflowOrbConceptV1/design.json'")
s=s.replace("Exclusive purple mana-orb pommel published","Star Tide Core exclusive special pommel published")
s=s.replace(".mana-orb.tmp",".star-tide.tmp")
(P/'publish.py').write_text(s,encoding='utf-8')
print('Star Tide production scripts written')
