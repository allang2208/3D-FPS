from pathlib import Path
M66_COMMANDLET=True
task_base=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FurnaceBreathV17')
for task_script in ('import_skin.py','import_motion.py','author_effect.py','install_character.py'):
    exec(compile((task_base/task_script).read_text(encoding='utf-8'),task_script,'exec'))
