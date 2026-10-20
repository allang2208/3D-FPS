"""Read the short nonlinear source interval at independent subframe times."""
from pathlib import Path
source=Path(__file__).with_name('export_compressed_dense.py')
code=source.read_text().replace('rate=1920;times=[i/rate for i in range(round(.9*rate)+1)]',
    'rate=15360;times=[i/rate for i in range(66*128,70*128+1)]')
code=code.replace('compressed-1920.json.gz','compressed-window-15360.json.gz')
exec(compile(code,str(source),'exec'),globals())
