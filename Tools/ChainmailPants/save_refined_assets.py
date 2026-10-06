"""Save only the new ArmorRefineV2 packages; preserve the loaded V1 family."""
import sys
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(P/'Tools/ChainmailPants'))
import save_assets as author

author.R=P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2'
author.DEST='/Game/Characters/ModularOutfit20260924/ChainmailPants20261004/ArmorRefineV2'
author.main()
