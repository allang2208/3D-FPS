from pathlib import Path
O=Path(__file__).parent;source=O.parent/'AKMReloadPolish20260911/import.py';s=source.read_text()
s=s.replace("O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish'",f"O=Path({str(O/'Final')!r});P='/Game/Weapons/AKMIntegration/SovietFab/GripReturn'")
s=s.replace("['base','prism','angled']","['prism','angled']").replace('len(report)==12','len(report)==8')
exec(compile(s,str(source),'exec'))
