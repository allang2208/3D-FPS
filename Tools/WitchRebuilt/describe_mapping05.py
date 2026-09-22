import unreal as u
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
u.SystemLibrary.execute_console_command(None,'WitchRebuilt.DescribeDrapeMapping')
source=root/'Saved/WitchRebuilt-DrapeMapping.txt'
text=source.read_text(encoding='utf-8-sig')
(root/'SourceAssets/WitchRebuilt20260921/Spike20260922/mapping_before.txt').write_text(text,encoding='utf-8')
print(text)
