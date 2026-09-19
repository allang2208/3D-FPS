from pathlib import Path
O=Path(__file__).parent;A=O.parent/'AKMAttachments20260911';source=O.parent/'AKMReloadPolish20260911/build.py';s=source.read_text()
(O/'Final').mkdir(exist_ok=True)
s=s.replace("O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911';report={}",f'O=Path({str(O / "Final")!r});B=Path({str(O / "Baked")!r});report={{}}')
s=s.replace("for variant in ['base','prism','angled']:","for variant in ['prism','angled']:")
s=s.replace("str(B/'preview_visibility.py')",f'str(Path({str(A / "preview_visibility.py")!r}))')
exec(compile(s,str(source),'exec'))
