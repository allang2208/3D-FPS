from pathlib import Path
FAMILY='prism'
exec(compile(Path(__file__).with_name('import_animations.py').read_text(),__file__,'exec'))
