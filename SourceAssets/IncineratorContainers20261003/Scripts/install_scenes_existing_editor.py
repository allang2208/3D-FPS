from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'Scripts/install_scenes.py'
exec(compile(script.read_text('utf8'),str(script),'exec'),dict(__file__=str(script),TREATMENT_CONTAINERS_EXISTING_EDITOR=True))
