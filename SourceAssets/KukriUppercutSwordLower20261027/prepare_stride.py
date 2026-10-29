"""Read the exact forward stride used by the two-handed uppercut mixer."""
from pathlib import Path
path = Path(__file__).with_name('prepare.py')
source = path.read_text().replace("['Melee.FullBody.Uppercut']", "['Unarmed.Jog.Fwd']")
source = source.replace('sword-lower-inputs.json', 'sword-stride-inputs.json')
source = source.replace('SWORD_LOWER', 'SWORD_STRIDE')
exec(compile(source, str(path), 'exec'), {'__file__':str(path),'__name__':'__main__'})
