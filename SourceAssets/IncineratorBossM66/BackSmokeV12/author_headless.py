from pathlib import Path
M66_COMMANDLET=True
task_source=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/BackSmokeV12/author_smoke.py')
exec(compile(task_source.read_text(encoding='utf-8'),str(task_source),'exec'))
