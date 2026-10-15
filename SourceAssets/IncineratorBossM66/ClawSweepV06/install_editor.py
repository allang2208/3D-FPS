from pathlib import Path
M66_COMMANDLET=False
task_base=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ClawSweepV06')
for task_script in ('import_motion.py','install_character.py'):
    exec(compile((task_base/task_script).read_text(encoding='utf-8'),task_script,'exec'))
