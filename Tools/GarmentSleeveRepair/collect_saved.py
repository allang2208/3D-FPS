"""Read saved package receipts without loading assets into an existing PIE."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('collect_saved_disk.py')),run_name='__main__')
