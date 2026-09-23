"""Import the completed authored boss room through the project's batch bridge."""
from pathlib import Path
import runpy
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root.parent/'DungeonBossHall20260922/Scripts/import_assets.py'),run_name='__main__')
