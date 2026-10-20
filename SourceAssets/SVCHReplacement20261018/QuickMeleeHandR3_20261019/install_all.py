"""Install only the reviewed SVCH action layers and native glove correctives."""
from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
for script in ['install_profiles.py','install_glove.py']:
    runpy.run_path(str(root/script),run_name='__main__')
