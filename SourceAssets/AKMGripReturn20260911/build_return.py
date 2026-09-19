from pathlib import Path
import sys
O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911'
variant=sys.argv[sys.argv.index('--')+1]
s=(B/'build_grip.py').read_text()
s=s.replace('ROOT=Path(__file__).parent',f'ROOT=Path({str(B)!r})')
s=s.replace('O=ROOT/variant;O.mkdir(exist_ok=True);BASE=ROOT',f'O=Path({str(O / "Baked")!r})/variant;O.mkdir(parents=True,exist_ok=True);BASE=ROOT')
s=s.replace('return 1-smooth((f-18)/24)+smooth((f-(end-48))/36) if \'reload\' in clip else 1',"return 1-smooth((f-18)/24)+smooth((f-(380 if 'empty' in clip else 270))/60) if 'reload' in clip else 1")
s=s.replace("exec(compile(code",'''code=code.replace("else:opening=1-smooth((f-(end-20))/20);retreat=1-smooth((f-(end-48))/36)","else:R=440 if 'empty' in clip else 330;opening=1-smooth((f-(R-20))/20);retreat=1-smooth((f-(R-60))/60)")
exec(compile(code''')
sys.argv=['build_grip.py','--',variant,'reload','reload_empty','drum_reload','drum_reload_empty']
exec(compile(s,str(B/'build_grip.py'),'exec'))
