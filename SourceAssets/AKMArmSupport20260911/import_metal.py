from pathlib import Path
O=Path(__file__).parent;s=(O/'import.py').read_text().replace("for variant in ['prism','angled']:","for variant in []:").replace('assert len(report)==18','assert len(report)==0').replace("O/'import.json'","O/'metal_import.json'")
exec(compile(s,str(O/'import.py'),'exec'))
