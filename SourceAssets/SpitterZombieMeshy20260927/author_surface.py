"""Bake the accepted Mutant3 infected-skin recipe onto this mesh's own UVs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
source=PROJECT/'Tools/MonsterStyle/author_surface.py'
code=source.read_text(encoding='utf-8')
code=code.replace("ROOT = PROJECT / 'SourceAssets/MonsterStyleV1'", "ROOT = PROJECT / 'SourceAssets/SpitterZombieMeshy20260927/Surface'")
code=code.replace("ROOT / 'settings.json'", "PROJECT / 'SourceAssets/MonsterStyleV1/settings.json'")
code=code.replace("MODE = sys.argv[sys.argv.index('--') + 1]", "MODE = 'mutant'\nSETTINGS['mutant'] = dict(SETTINGS['mutant'], source='SourceAssets/SpitterZombieMeshy20260927/SpitterZombie_Meshy_Source.blend', texture_size=2048)")
exec(compile(code,str(source),'exec'),{'__file__':str(source),'__name__':'__main__'})
