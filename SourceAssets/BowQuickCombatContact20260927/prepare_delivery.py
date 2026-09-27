"""Prepare scoped UE import and contact views from the existing bow pipeline."""
from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'BowQuickCombatPush20260927/import_push.py').read_text()
source=source.replace('requested horizontal push; no preview or gameplay test','surface-fitted right grasp; no gameplay test')
source=source.replace('generated_push_v3.py','generated_contact_v4.py').replace('BOW_HORIZONTAL_PUSH_SAVED','BOW_RIGHT_CONTACT_SAVED')
(P/'import_contact.py').write_text(source,encoding='utf-8')
source=(P.parent/'BowQuickCombat20260927/render_grab.py').read_text()
source=source.replace("[('before',P.parent/'BowQuickCombat20260926','author_action.py'),('after',P,'generated_action_v2.py')]",
    "[('before',P.parent/'BowQuickCombatPush20260927','generated_push_v3.py'),('after',P,'generated_contact_v4.py')]")
source=source.replace('(.08,.14,.22,.32)','(.10,.14,.32,.66)')
start=source.index('    for t in (.07,');end=source.index("print('BOW_GRAB_REVIEW_SAVED'",start)
source=source[:start]+source[end:]
(P/'render_player_contact.py').write_text(source,encoding='utf-8')
