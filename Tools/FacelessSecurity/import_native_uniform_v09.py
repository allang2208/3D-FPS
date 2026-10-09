"""Save native-rest V09 body, independent clothing and render assembly."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_uniform_v04.py').read_text(encoding='utf-8').replace('V04','V09')
src=src.replace("[('outfit','SK_FacelessSecurity_V09'),('clothing','SK_FacelessSecurity_Clothing_V09')]",
    "[('outfit','SK_FacelessSecurity_V09'),('clothing','SK_FacelessSecurity_Clothing_V09'),('body','SK_FacelessSecurity_Body_V09')]")
src=src.replace('torso-only belt; no side pouches; front-only collar panels; continuous garment and trim weights',
    'Native-rest continuous uniform; complete-body shoulder field; final geometry normals; matched inner walls; full visible forearm overlap')
src=src.replace('waist protrusion and garment spike repair; V03 zombie motions retained',
    'Native bind-frame shoulder/sleeve rebuild; intact hands and forearms; V06 zombie motions retained')
src=src.replace('Preserved existing V03 references and values','Preserved existing V06 references and values')
src=src.replace("complete_body='Existing intact V03 body asset retained'","complete_body=report['meshes']['body']")
exec(compile(src,__file__,'exec'))
