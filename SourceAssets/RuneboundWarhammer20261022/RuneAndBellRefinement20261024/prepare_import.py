from pathlib import Path
P=Path(__file__).resolve().parent
source=(P.parent/'FinalTollIntegrationV1/install_assets.py').read_text('utf-8')
source=source.replace("MODEL=P.parent/'FinalTollHammerHeadV1'","MODEL=P.parent/'FinalTollHammerHeadV2'")
source=source.replace("D='/Game/Weapons/RuneboundWarhammer20261022/FinalTollV1'","D='/Game/Weapons/RuneboundWarhammer20261022/FinalTollV2'")
source=source.replace("OWNER='FinalTollIntegrationV1_20261023'","OWNER='RuneAndBellRefinement20261024'")
source=source.replace('SM_RuneboundWarhammer_FinalTollHammerHeads_V1','SM_RuneboundWarhammer_FinalTollHammerHeads_V2')
source=source.replace('native_triangles=111240','native_triangles=99000')
source=source[:source.index("exec(compile((P/'install_motion_vfx.py')")]
source += '\nexec(compile((P/"install_runes_icons.py").read_text("utf-8"),str(P/"install_runes_icons.py"),"exec"))\n'
(P/'install_assets.py').write_text(source,encoding='utf-8')
icon=(P.parent/'FinalTollIntegrationV1/author_icon.py').read_text('utf-8')
icon=icon.replace('FinalTollHammerHeadV1','FinalTollHammerHeadV2').replace('SM_RuneboundWarhammer_FinalTollHammerHeads_V1','SM_RuneboundWarhammer_FinalTollHammerHeads_V2')
(P/'author_bell_icon.py').write_text(icon,encoding='utf-8')
print('Prepared V2 model/material import and actual-model icon source')
