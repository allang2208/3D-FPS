"""Run with Blender in background to reproduce the two R5 model sources."""
from pathlib import Path
import json,runpy,subprocess,sys
P=Path(__file__).resolve().parent
original_args=list(sys.argv)
try:
    for kind in ['HeavyCleaver','FoldedArc']:
        sys.argv=original_args[:original_args.index('--')] if '--' in original_args else list(original_args)
        sys.argv+=['--',kind]
        runpy.run_path(str(P/'author_geometry.py'),run_name='__main__')
finally:
    sys.argv=original_args
parts=[json.loads((P/(kind+'.json')).read_text('utf-8')) for kind in ['HeavyCleaver','FoldedArc']]
(P/'parts.json').write_text(json.dumps(parts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
transfer=P.parent/'CrescentReferenceR4_20261104/FactoryFinish20261104/transfer_textures.py'
for kind in ['HeavyCleaver','FoldedArc']:
    subprocess.run(['py','-3.11',str(transfer),'--workdir',str(P/kind)],check=True)
runpy.run_path(str(P/'apply_sources.py'),run_name='__main__')
