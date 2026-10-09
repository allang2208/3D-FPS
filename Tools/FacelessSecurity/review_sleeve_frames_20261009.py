"""Expand the requested sleeve containment check to every authored frame."""
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurityReview20261009');R.mkdir(parents=True,exist_ok=True)
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/check_sleeve_overlap_v13.py').read_text(encoding='utf-8')
src=src.replace("ROOT=BASE/'V13'","ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurityReview20261009')")
src=src.replace("for version in ['V11','V13']:","for version in ['V13']:")
src=src.replace('nine samples per active native action','every authored frame per active native action')
src=src.replace('sorted(set(round(lo+(hi-lo)*i/8) for i in range(9)))','range(round(lo),round(hi)+1)')
src=src.replace("'Diagnosis/sleeve_overlap.json'","'sleeve_all_frames.json'")
exec(compile(src,'sleeve_full_frame_review','exec'))
