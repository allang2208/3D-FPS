"""Reuse the read-only audit against the newly saved assets."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
source=P/'SourceAssets/TelescopicAllGunsAudit20261015/capture.py'
exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'))
