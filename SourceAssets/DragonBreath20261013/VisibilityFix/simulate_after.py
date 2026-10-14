from pathlib import Path
probe_asset='/Game/Skills/DragonBreath20261013/NS_DragonBreath.NS_DragonBreath'
probe_output='simulation-after.json'
exec(compile(Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/VisibilityFix/simulate.py').read_text(encoding='utf-8'),'dragon-probe','exec'))
