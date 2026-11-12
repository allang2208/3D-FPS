from pathlib import Path
here=Path(__file__).resolve().parent
prior=here.parent/'Wrist37'
script=(prior/'run-wire.ps1').read_text().replace('Wrist37/WireRuns/','Wrist38/WireRuns/')
(here/'run-wire.ps1').write_text(script)
(here/'package_delivery.py').write_text((prior/'package_delivery.py').read_text())
remote=(prior/'FollowupReview/remote_sheets.py').read_text().replace('import json','import json,sys')
remote=remote.replace("RUN=HERE.parent/'WireRuns/20261111-120644'","RUN=Path(sys.argv[1])")
(here/'remote_sheets.py').write_text(remote)
