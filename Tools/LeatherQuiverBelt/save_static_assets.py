"""Complete independent pickup/icon assets while native body packages are unavailable."""
from pathlib import Path
scope={'__name__':'quiver_static_delivery'}
script=Path('D:/FPS3D/FPSGAME/Tools/LeatherQuiverBelt/save_assets.py').read_text(encoding='utf-8')
prefix=script[:script.index("for row in delivery['records']:")]
tail=script[script.index("rows=next(r['lods']"):]
tail=tail.replace('receipt.update(completed=True,','receipt.update(completed=False,static_assets_completed=True,')
tail=tail.replace('LEATHER_QUIVER_BELT_ASSETS_SAVED','LEATHER_QUIVER_STATIC_ASSETS_SAVED')
exec(compile(prefix+tail,'quiver_static_delivery','exec'),scope)
