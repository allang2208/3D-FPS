from pathlib import Path
FAMILY='angled'
exec(compile(Path(__file__).with_name('import_animations.py').read_text(),__file__,'exec'))
