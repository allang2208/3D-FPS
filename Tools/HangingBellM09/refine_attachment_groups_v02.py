from pathlib import Path
p=Path(r"D:\FPS3D\FPSGAME\Tools\HangingBellM09\author_semantic_parts.py")
s=p.read_text(encoding="utf8")
s=s.replace("deltas=np.zeros((N,3),np.float64)\nroot_weight=np.ones(N,np.float32)", "deltas=np.zeros((7,N,3),np.float32)\nroot_weight=np.ones((7,N),np.float32)")
s=s.replace('boundary=verts[incidence[verts].sum(1)>1]', '''boundary=verts[incidence[verts,0]]
        # Only the upper posterior attached strip is a fixed biological root.
        # Inter-leaf cuts are independent free margins, never pinned to body.
        anatomical=boundary[(wp[boundary,1]>.08)&(np.abs(wp[boundary,0])<.235)]
        if len(anatomical)==0:
            anatomical=boundary[wp[boundary,1]>=np.quantile(wp[boundary,1],.9)] if len(boundary) else np.array([verts[np.argmax(wp[verts,1])]])
        boundary=anatomical'''.replace("\n        ","\n    "))
s=s.replace("weight=smooth(dist[verts]/.06)*smooth((.29-wp[verts,1])/.30)","weight=smooth((dist[verts]-.015)/.12)")
s=s.replace("deltas[verts]+=weight[:,None]*offset","deltas[label,verts]=weight[:,None]*offset")
s=s.replace("root_weight[verts]=1-smooth(dist[verts]/.065)","root_weight[label,verts]=1-smooth((dist[verts]-.015)/.06)")
s=s.replace('"root_invariant":"shared source boundary vertices not displaced"', '"root_invariant":"anatomical root strip fixed; inter-leaf cut edges free and independently closed"')
s=s.replace("_v01","_v02").replace("M09_SourceSeparation_V01","M09_SourceSeparation_V02")
p.write_text(s,encoding="utf8")

p=Path(r"D:\FPS3D\FPSGAME\Tools\HangingBellM09\build_adjusted_parts_blender.py")
s=p.read_text(encoding="utf8")
s=s.replace('_v01','_v02').replace('_V01','_V02')
s=s.replace('r["membrane_delta"][ww]','r["membrane_delta"][label,ww]')
s=s.replace('r["root_weight"][ww]','r["root_weight"][label,ww]')
s=s.replace('guides.hide_render=True','guides.hide_render=True;guides.hide_viewport=True')
s=s.replace('pos=pp.tolist();norms=nn.tolist();tex=uu.tolist();triangles=lf.tolist();srcverts=ids.tolist();srcfaces=faceids.tolist()','pos=pp.tolist();norms=nn.tolist();tex=uu.tolist();triangles=lf.tolist();srcverts=ids.tolist();srcfaces=faceids.tolist();root_values=rootmask.tolist()')
s=s.replace('srcverts.extend([-1]*len(loop))','srcverts.extend([-1]*len(loop));root_values.extend((rootmask[loop]*shrink+rootmask[loop].mean()*(1-shrink)).tolist())')
s=s.replace('srcverts.append(-1)','srcverts.append(-1);root_values.append(float(rootmask[loop].mean()))')
s=s.replace('rw=np.zeros(len(pos));rw[:len(ids)]=rootmask\n if len(pos)>len(ids):rw[len(ids):]=1 if 1<=label<=6 else 0','rw=np.asarray(root_values)')
s=s.replace('25 named parts;','25 named parts;')
p.write_text(s,encoding="utf8")
