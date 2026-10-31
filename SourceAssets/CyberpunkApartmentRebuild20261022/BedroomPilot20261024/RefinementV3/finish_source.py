from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'install_level.py';s=p.read_text('utf8');start=s.index("    native=json.loads((R.parent/'source.json')");end=s.index('    # New visual mesh',start)
s=s[:start]+"    # V2 furniture positions remain exactly as saved; this revision changes assets.\n"+s[end:]
s=s.replace('BEDROOM_V2_MAP_SAVED','BEDROOM_V3_MAP_SAVED');p.write_text(s,encoding='utf8')
