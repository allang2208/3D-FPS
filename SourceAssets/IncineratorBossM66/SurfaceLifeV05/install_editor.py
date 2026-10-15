from pathlib import Path

M66_COMMANDLET=False
task_base=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66')
for task_script in ('ClawSweepV04/import_motion.py','ClawSweepV04/install_character.py','SurfaceLifeV05/import_surface.py'):
    exec(compile((task_base/task_script).read_text(encoding='utf-8'),task_script,'exec'))
