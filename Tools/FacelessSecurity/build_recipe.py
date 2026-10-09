"""Create a standalone male authoring recipe from the established rig helpers."""
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
src=(ROOT/'Tools/FacelessReceptionist/author_character_v02.py').read_text(encoding='utf-8-sig')
prefix=src[:src.index('parts=[];kinds={}')]
start=prefix.index('BASE=Path(')
end=prefix.index('rig=next(')
prefix=prefix[:start]+'''ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
body=bpy.data.objects['Security_SourceBody']
'''+prefix[end:]
prefix=prefix.replace('Author Meshy receptionist','Author Meshy male security')
prefix=prefix.replace('[0,.1,.54,1.003,1.16,1.36,1.47,1.57,1.652,1.82]', '[0,.105,.57,1.035,1.20,1.39,1.54,1.63,1.70,1.90]')
prefix=prefix.replace('sign*.184,.045,1.47','sign*.235,.034,1.525').replace('sign*.282,.031,1.218','sign*.312,.041,1.265').replace('sign*.411,-.023,.960','sign*.412,-.010,1.008')
prefix=prefix.replace('sign*.105,.025,.995','sign*.110,.018,1.035').replace('sign*.113,.048,.535','sign*.157,.020,.580').replace('sign*.132,.066,.089','sign*.205,.080,.105').replace('sign*.134,-.084,.024','sign*.240,-.080,.025')
prefix=prefix.replace('sign*.012,.025,1.48','sign*.012,.020,1.55')
prefix=prefix.replace("sign*v.co.x>.37 and v.co.z<.88", "sign*v.co.x>.36 and .73<v.co.z<.88")
prefix=prefix.replace('seg_distance(shoulder,elbow)/.070,seg_distance(elbow,wrist)/.052','seg_distance(shoulder,elbow)/.084,seg_distance(elbow,wrist)/.062')
prefix=prefix.replace('[.8,1.02,1.18,1.34,1.48,1.57],[.205,.18,.143,.16,.13,.055]', '[.8,1.05,1.20,1.39,1.54,1.65],[.230,.215,.190,.235,.200,.073]')
prefix=prefix.replace('[.8,1.02,1.18,1.34,1.48,1.57],[.14,.14,.11,.14,.10,.055]', '[.8,1.05,1.20,1.39,1.54,1.65],[.135,.148,.140,.158,.133,.080]')
prefix=prefix.replace('p.z<1.16 and abs(p.x)<.215','p.z<1.18 and abs(p.x)<.255').replace('p.z>1.58','p.z>1.655')
prefix=prefix.replace('p.z>=1.03','p.z>=1.075').replace('smooth(1.035,.855,p.z)','smooth(1.080,.885,p.z)').replace('smooth(.602,.477,p.z)','smooth(.645,.515,p.z)').replace('smooth(.145,.065,p.z)','smooth(.175,.080,p.z)')
suffix=(ROOT/'Tools/FacelessSecurity/garment_recipe.py').read_text(encoding='utf-8')
(ROOT/'Tools/FacelessSecurity/author_character.py').write_text(prefix+'\n'+suffix,encoding='utf-8')
print('Standalone security authoring recipe written')
