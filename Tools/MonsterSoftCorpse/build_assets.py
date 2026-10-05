"""One unattended UE authoring session: export, offline cage authoring, save."""
from pathlib import Path
import runpy
import subprocess

scripts = Path(__file__).resolve().parent
runpy.run_path(str(scripts/'prepare_sources.py'), run_name='__main__')
subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',
                str(scripts/'author_cages.py')], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
runpy.run_path(str(scripts/'install_corpses.py'), run_name='__main__')
