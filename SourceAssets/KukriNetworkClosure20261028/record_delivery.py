"""Record this batch's source snapshot and actual execution results."""
from pathlib import Path
import hashlib
import json
from datetime import datetime

out = Path(__file__).resolve().parent
root = out.parents[1]
source = root / 'Source/FPSGAME'
owned = [
    'Weapons/Kukri/KukriAttackReceipt.h',
    'Weapons/Kukri/KukriAttackReceipt.cpp',
    'Weapons/Kukri/KukriNetworkAttack.cpp',
    'Weapons/Kukri/KukriWeaponComponent.h',
    'Weapons/Kukri/KukriWeaponComponent.cpp',
    'Weapons/Kukri/KukriDashAttack.cpp',
    'Multiplayer/ColdSteelPlayerState.h',
    'Multiplayer/ColdSteelPlayerState.cpp',
    'Multiplayer/ColdSteelKukriAuthority.cpp',
    'Multiplayer/KukriNetworkAuditCommandlet.h',
    'Multiplayer/KukriNetworkAuditCommandlet.cpp',
    'Multiplayer/UppercutStaminaReceipt.h',
    'Multiplayer/ColdSteelCampfireRequests.cpp',
    'Multiplayer/ColdSteelTeamTravel.cpp',
    'Movement/FPSCharacterMovementComponent.h',
    'Movement/FPSMeleeMoveRequest.h',
    'Movement/FPSMeleeMovementNetwork.cpp',
    'Movement/FPSDodgeNetwork.cpp',
    'Skills/ColdSteelSkillTypes.h',
]
files = [source / name for name in owned]
files += [root / 'Docs/Weapons/kukri-network-closure-20261028.md',
          root / 'Docs/Weapons/kukri-single-dual-audit-20261028.md',
          out / 'run.ps1', out / 'read_assets.py', Path(__file__).resolve()]
rows = [dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size,
             sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
stages = {stage: json.loads((out / (stage + '-result.json')).read_text(encoding='utf-8-sig'))
          if (out / (stage + '-result.json')).exists() else None
          for stage in ('Editor', 'Audit', 'Assets', 'Game')}
report = dict(recorded=datetime.now().astimezone().isoformat(), files=rows, stages=stages,
              note='Whole-file hashes identify the shared workspace snapshot, not exclusive ownership of every line.',
              animations_changed=False, real_multiplayer_tested=False, visuals_tested=False)
(out / 'delivery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({stage: value.get('exit_code') if value else None for stage, value in stages.items()}))
