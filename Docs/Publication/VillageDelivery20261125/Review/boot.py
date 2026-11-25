import os
from pathlib import Path
source=Path(os.environ['VILLAGE_AUDIT_SCRIPT'])
namespace={'__name__':'delivery_review','__file__':str(source)}
exec(compile(source.read_text(encoding='utf8'),str(source),'exec'),namespace)
