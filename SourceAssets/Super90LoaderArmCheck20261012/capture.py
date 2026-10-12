import unreal as u
from pathlib import Path
O=Path(__file__).parent
if not u.Super90LoaderArmAuditCommandlet.capture(str(O/'Capture')):
    raise RuntimeError('Production graph capture failed; inspect UE log')
print('SUPER90_LOADER_ARM_CAPTURE_COMPLETED',flush=True)
