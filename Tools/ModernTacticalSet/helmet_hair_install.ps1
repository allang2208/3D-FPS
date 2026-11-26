$ErrorActionPreference='Stop'
# Filesystem-only publication: the staged packages have new, task-owned names.
# The publisher refuses existing different packages and uses config_transaction
# for the two shared JSON leaves. No editor/bridge operation is performed here.
& python D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/helmet_hair_publish.py
exit $LASTEXITCODE
