from pathlib import Path
p=Path(r"D:\FPS3D\FPSGAME\Tools\HangingBellM09\author_semantic_parts.py")
s=p.read_text(encoding="utf8")
a=s.index(" boundary=verts[incidence[verts,0]]")
b=s.index(" localedges=",a)
s=s[:a]+""" boundary=verts[incidence[verts,0]]
 # Keep only the anatomical attached upper strip fixed; inter-leaf margins remain free.
 anatomical=boundary[(wp[boundary,1]>.08)&(np.abs(wp[boundary,0])<.235)]
 if len(anatomical)==0:
  anatomical=boundary[wp[boundary,1]>=np.quantile(wp[boundary,1],.9)] if len(boundary) else np.array([verts[np.argmax(wp[verts,1])]])
 boundary=anatomical
"""+s[b:]
p.write_text(s,encoding="utf8")
