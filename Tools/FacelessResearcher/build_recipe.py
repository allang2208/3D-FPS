"""Generate the researcher-specific anatomical binding helper from the Nurse pipeline."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME')
s=(BASE/'Tools/FacelessReceptionist/author_character_v02.py').read_text(encoding='utf-8-sig').split('parts=[];kinds={}')[0]
a=s.index('BASE=Path(');b=s.index('rig=next(')
s=s[:a]+"ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')\nbpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))\nbody=bpy.data.objects['Researcher_SourceBody']\n"+s[b:]
replacements={
 '[0,.1,.54,1.003,1.16,1.36,1.47,1.57,1.652,1.82]':'[0,.108,.60,1.023,1.15,1.37,1.546,1.617,1.714,1.88]',
 'sign*.184,.045,1.47':'sign*.186,.044,1.546',
 'sign*.282,.031,1.218':'sign*.272,.025,1.272',
 'sign*.411,-.023,.960':'sign*.374,-.030,1.040',
 'sign*.105,.025,.995':'sign*.102,.020,1.023',
 'sign*.113,.048,.535':'sign*.116,.032,.600',
 'sign*.132,.066,.089':'sign*.153,.069,.108',
 'sign*.134,-.084,.024':'sign*.154,-.085,.027',
 'sign*.012,.025,1.48':'sign*.012,.031,1.576',
 "sign*v.co.x>.37 and v.co.z<.88":"sign*v.co.x>.35 and .78<v.co.z<.92",
 'seg_distance(shoulder,elbow)/.070,seg_distance(elbow,wrist)/.052':'seg_distance(shoulder,elbow)/.056,seg_distance(elbow,wrist)/.040',
 '[.8,1.02,1.18,1.34,1.48,1.57],[.205,.18,.143,.16,.13,.055]':'[.8,1.02,1.20,1.28,1.44,1.55,1.64],[.19,.20,.14,.118,.15,.15,.055]',
 '[.8,1.02,1.18,1.34,1.48,1.57],[.14,.14,.11,.14,.10,.055]':'[.8,1.02,1.20,1.28,1.44,1.55,1.64],[.09,.115,.10,.095,.125,.083,.054]',
 'p.z<1.16 and abs(p.x)<.215':'p.z<1.22 and abs(p.x)<.215',
 'p.z>1.58':'p.z>1.625',
 'p.z>=1.03':'p.z>=1.06',
 'smooth(1.035,.855,p.z)':'smooth(1.06,.87,p.z)',
 'smooth(.602,.477,p.z)':'smooth(.665,.535,p.z)',
 'smooth(.145,.065,p.z)':'smooth(.175,.070,p.z)',
}
for old,new in replacements.items():
    if old not in s:raise RuntimeError('Missing body recipe anchor '+old)
    s=s.replace(old,new)
(BASE/'Tools/FacelessResearcher/body_fit_helpers.py').write_text(s,encoding='utf-8')
print('Researcher binding recipe written; original Nurse rig preserved')
