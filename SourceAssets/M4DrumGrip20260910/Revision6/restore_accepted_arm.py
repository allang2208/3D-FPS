from pathlib import Path
p=Path(__file__).with_name('build_drop_reload.py');text=p.read_text()
text=text.replace("   for side in ['l','r']:\n    un,fn,hn", "   for side in ['r']:\n    un,fn,hn")
start=text.index('   # Preserve the accepted R5 installation')
end=text.index('   if phase:poses.append',start)
text=text[:start]+'''   # Reuse the accepted R5 limb, including all skin helpers and fingers.
   # Only the entire limb rotates at the shoulder for the behind-hip reach.
   # Installation is an exact rigid transform of R5, with no new IK solve.
   if t<=hold:
    si=0;reach=0.0
   elif t<acquire:
    progress=smooth((t-hold)/(acquire-hold));source_start=22 if clip=='reload' else 18
    si=round((source_start+(lock-source_start)*progress)*2);reach=progress
   elif t<lock:
    si=lock*2;reach=1-smooth((t-acquire)/(lock-acquire))
   else:si=k;reach=0.0
   delta=gun[k]@reference[si]['P']['WPN_root'].inverted()
   A=(delta@reference[si]['P']['upperarm_l']).translation
   palm=(delta@reference[si]['P']['hand_l']).translation
   back=Vector((-.40,-.32,-.38))
   backq=(palm-A).normalized().rotation_difference((back-A).normalized())
   q=Quaternion().slerp(backq,reach)
   reach_transform=Matrix.Translation(A)@q.to_matrix().to_4x4()@Matrix.Translation(-A)
   for b in r.pose.bones:
    if b.name.endswith('_l'):
     b.matrix=(delta@reference[si]['P'][b.name] if b.name.startswith('clavicle') else reach_transform@delta@reference[si]['P'][b.name]);update()
   if t>=lock:
    for b in r.pose.bones:
     if b.name.endswith('_r'):b.matrix=trusted[k][b.name];update()
   if release<t<lock:
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=r.pose.bones['hand_l'].matrix@raw[lock*2]['P']['hand_l'].inverted()@raw[lock*2]['P']['WPN_SOCKET_Magazine'];update()
''' +text[end:]
p.write_text(text)
