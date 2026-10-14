from pathlib import Path
probe_asset='/Game/RPG-FlameAttackVFX/VFX/Niagara/N_FlameAttack.N_FlameAttack'
probe_output='simulation-source.json'
exec(compile(Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/VisibilityFix/simulate.py').read_text(encoding='utf-8'),'dragon-probe','exec'))
