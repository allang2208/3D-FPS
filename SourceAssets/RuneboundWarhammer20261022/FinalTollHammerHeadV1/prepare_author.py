"""Freeze shared production helpers, then author a new open bell-chamber head."""
from pathlib import Path
import ast

P=Path(__file__).resolve().parent
source=(P.parent/'StarOathHammerHeadV1/author_model.py').read_text('utf-8')
source=source.replace('StarOath','FinalToll').replace('STAR_OATH','FINAL_TOLL').replace('star_oath_sealing_anvil','final_toll_soul_bell').replace('星誓·封界之砧','终律·镇魂钟')
source=source.replace('(.015,.27,1,1)','(1,.64,.22,1)').replace('(.008,.07,.24)','(.25,.14,.025)')
source=source.replace('(.24,.145,.055),(.43,.29,.12),.32','(.15,.12,.065),(.32,.26,.13),.38')
source=source.replace("    crystal=join_group(CRYSTALS,'FinalToll_Optical_Crystals')\n    unwrap(crystal)\n",'')
source=source.replace('[metal,brass,crystal,energy]','[metal,brass,energy]')
source=source.replace("    final['not_runtime_integrated']=True","    final['not_runtime_integrated']=True\n    final['chamber_count']=2\n    final['resonance_columns_per_chamber']=6\n    final['construction']='Open three-window gothic cages, solid strike plates, retained factory collars'")
tree=ast.parse(source)
old=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_head')
lines=source.splitlines()
new=(P/'bell_geometry.py').read_text('utf-8').splitlines()
lines[old.lineno-1:old.end_lineno]=new
(P/'author_model.py').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('FINAL_TOLL_AUTHOR_PREPARED',flush=True)
