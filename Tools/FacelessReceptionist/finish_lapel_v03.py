from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist\tailor_details_v03.py')
s=p.read_text(encoding='utf-8')
s=s.replace("if 1.161<q.z<1.526", "if 1.10<q.z<1.526")
s=s.replace("np.interp(q.z,[1.16,1.30,1.42,1.49,1.526],[.002,.038,.072,.080,.065])","np.interp(q.z,[1.10,1.17,1.30,1.42,1.49,1.526],[.0005,.0005,.038,.072,.080,.065])")
s=s.replace("np.linspace(1.162,1.526,rows)","np.linspace(1.161,1.492,rows)")
s=s.replace("np.interp(z,[1.16,1.30,1.42,1.49,1.526],[.002,.038,.072,.080,.065])","np.interp(z,[1.16,1.17,1.30,1.42,1.49,1.526],[.0004,.0005,.038,.072,.080,.065])")
p.write_text(s,encoding='utf-8')
