from pathlib import Path
task_base=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ThumbDrapeV10')
for task_script in ('import_skin.py','install_character.py'):
    exec(compile((task_base/task_script).read_text(encoding='utf-8'),task_script,'exec'))
