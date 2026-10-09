from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist')
s=(p/'render_reference_v02.py').read_text(encoding='utf-8')
s=s.replace("ROOT/'Authoring'/'FacelessReceptionist_V02.blend'","ROOT.parent/'Authoring'/'Inputs.blend'")
s=s.replace("if o.type=='MESH' and not o.hide_render","if o.type=='MESH' and o.name=='Receptionist_SourceBody'")
s=s.replace('FacelessReceptionist_V02_ThreeView.png','Meshy_Source_ThreeView.png')
(p/'render_source_reference.py').write_text(s,encoding='utf-8')
