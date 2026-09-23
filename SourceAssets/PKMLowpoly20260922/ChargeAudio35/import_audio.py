"""Import and save the four original-video charging sounds in their own folder."""
from pathlib import Path
prior=Path(__file__).parent.parent/'BeltAudio22/import_audio.py'
script=prior.read_text().replace("DEST = '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22'",
    "DEST = '/Game/Weapons/PKMLowpoly20260922/ChargeAudio35'").replace('PKM_RELOAD22','PKM_CHARGE35')
exec(compile(script,str(prior),'exec'))
