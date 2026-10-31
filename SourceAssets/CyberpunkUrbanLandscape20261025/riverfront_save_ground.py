"""Complete revised ground imports after triangulating clipped source borders."""
from pathlib import Path
import runpy,unreal as u
R=Path(__file__).resolve().parent
u.EditorLoadingAndSavingUtils.new_blank_map(False)
for i in range(5):runpy.run_path(str(R/f'riverfront_batch_{i:02}.py'),run_name='__main__')
runpy.run_path(str(R/'riverfront_batch_11.py'),run_name='__main__')
runpy.run_path(str(R/'publish.py'),run_name='__main__')
