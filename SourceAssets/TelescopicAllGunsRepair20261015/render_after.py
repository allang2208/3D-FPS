"""Same audit render recipe after installation, without starting a game."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
source=P/'SourceAssets/TelescopicAllGunsAudit20261015/check_surfaces.py'
exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'))
