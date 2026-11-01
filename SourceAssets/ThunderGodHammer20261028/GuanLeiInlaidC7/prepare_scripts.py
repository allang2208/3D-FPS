"""Freeze the approved C6 authoring method for the GuanLei-only revision."""
from pathlib import Path
P=Path(__file__).resolve().parent
C=P.parent/'SeatInlaidC6'
design=(C/'design.py').read_text(encoding='utf-8')
begin=design.index('STYLES=[');end=design.index('\ndef smooth',begin)
style='''STYLES=[dict(
 id='guan_lei_seat',name='贯雷锤座',bulk=.0011,width=.00265,depth=.00125,
 paths=[[(.0395,.970),(.054,.962),(.048,.956),(.059,.943),(.054,.937)],
        [(.054,.970),(.061,.961),(.055,.955),(.061,.947)]],
 lower=True,seams=False,
 appearance='原厂雷纹圆徽 · 双向嵌银回雷纹 · 一体锻肩')]
'''
(P/'design.py').write_text(design[:begin]+style+design[end:],encoding='utf-8')
replacements={
 'ThorSeats_InlaidC6.blend':'GuanLei_InlaidC7_Editable.blend',
 'M_ThorSeatC6_':'M_GuanLeiC7_',
 'T_ThorSeatC6_':'T_GuanLeiC7_',
 'ALL_FIVE_C_GEOMETRY_EXPORTED':'GUANLEI_C7_GEOMETRY_EXPORTED',
 'Refine and engrave five original solids':'Refine and engrave the original GuanLei-compatible solid',
 'EDITABLE_C_SOURCE_PACKED':'GUANLEI_C7_SOURCE_PACKED',
 'THOR_INLAID_C6_ASSETS_SAVED':'GUANLEI_C7_ASSETS_SAVED',
 '/SeatInlaidC6':'/GuanLeiInlaidC7',
 "len(manifest['parts'])==5":"len(manifest['parts'])==1",
 'Import the five selected C seats':'Import the GuanLei C7 seat',
}
for name in ('author_geometry.py','author_textures.py','finish_source.py','import_assets.py','import.ps1'):
    text=(C/name).read_text(encoding='utf-8-sig')
    for old,new in replacements.items():text=text.replace(old,new)
    (P/name).write_text(text,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8')
print('GUANLEI_C7_AUTHORING_SOURCES_CREATED')
