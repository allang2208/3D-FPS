"""Keep a Meshy credential only in this interactive production process."""
import getpass
import os
from pathlib import Path
import runpy
import shlex
import sys

pipeline = Path(__file__).with_name('meshy_pipeline.py')
os.environ['MESHY_API_KEY'] = getpass.getpass('Meshy credential (hidden): ').strip()
print('Meshy production session ready.', flush=True)
try:
    while True:
        command = input('meshy> ').strip()
        if command == 'exit':
            break
        if not command:
            continue
        sys.argv = [str(pipeline), *shlex.split(command)]
        try:
            runpy.run_path(str(pipeline), run_name='__main__')
        except SystemExit as exc:
            print(f'Command completed with exit status {exc.code}.', flush=True)
        except Exception as exc:
            print(f'Command failed: {type(exc).__name__}', flush=True)
finally:
    os.environ.pop('MESHY_API_KEY', None)
