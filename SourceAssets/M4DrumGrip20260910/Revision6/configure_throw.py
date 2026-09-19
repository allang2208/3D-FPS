from pathlib import Path
p=Path(__file__).with_name('build_drop_reload.py');s=p.read_text()
s=s.replace("[('reload',126,18,42,50),('reload_empty',162,14,29,35)]", "[('reload',126,18,44,50),('reload_empty',162,14,38,43)]")
s=s.replace('hold=release+4','hold=release+2;acquire=36 if clip==\'reload\' else 31')
start=s.index(' def weapon(t,old):');end=s.index(' gun=[weapon(',start)
s=s[:start]+''' # Rotation landmarks reference the ordinary-magazine cant, but keep the
 # right grip at one depth instead of moving the entire viewmodel forward/back.
 tiltkeys=[(0,Matrix.Translation(Vector((0,0,0)))),(release-7,Matrix.Translation(Vector((5,-3,1)))),(release,Matrix.Translation(Vector((10,18,-4)))),(hold+8,Matrix.Translation(Vector((14,11,-3)))),(end-20,Matrix.Translation(Vector((14,11,-3)))),(end,Matrix.Translation(Vector((0,0,0))))]
 pivot=reference[0]['P']['hand_r'].translation.copy()
 def weapon(t,old):
  e=motion_curve(swaykeys,t).translation
  angles=motion_curve(tiltkeys,t).translation+e
  q=Euler(tuple(math.radians(v) for v in angles),'XYZ').to_quaternion()
  lift=.018*smooth(t/max(1,release-4))*smooth((end-t)/20)
  move=Vector((e.z*.0015,0,lift+e.x*.0015))
  return Matrix.Translation(pivot+move)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)@W0
''' + s[end:]
start=s.index(' away=mix(hand_hold,grasp,.62)');end=s.index(' raw=[]',start)
s=s[:start]+''' side=mix(hand_hold,grasp,.35);side.translation=Vector((-.30,.025,-.31))
 behind=grasp.copy();behind.translation=Vector((-.40,-.32,-.38))
 rest_dir=(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized()
 desired=(grasp.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@rest_dir).normalized()
 behind_dir=Vector((.15,-.22,.07)).normalized()
 behind=Matrix.LocRotScale(behind.translation,desired.rotation_difference(behind_dir)@grasp.to_quaternion(),Vector((1,1,1)))
 fetch=grasp.copy();fetch.translation+=Vector((-.075,-.10,-.06))
 handkeys=[(hold,hand_hold),(hold+5,side),(acquire-2,behind),(acquire,behind),(pickup,fetch),(lock,grasp)]
''' + s[end:]
s=s.replace("[(0,B),(hold,B),(hold+5,openB),(pickup,openB),(lock,C)]", "[(0,B),(hold,B),(hold+5,openB),(acquire-5,openB),(acquire,C),(lock,C)]")
old="if t<=release:r.pose.bones['WPN_SOCKET_Magazine'].matrix=gun[k]@W0.inverted()@reference[0]['P']['WPN_SOCKET_Magazine'];update()"
new='''if t<=release:
    mounted=gun[k]@W0.inverted()@reference[0]['P']['WPN_SOCKET_Magazine']
    unseat=smooth((t-(release-5))/4)
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=Matrix.Translation(gun[k].to_quaternion()@W0.to_quaternion().inverted()@Vector((0,0,-.06*unseat)))@mounted;update()
   elif t<lock:
    # Once acquired behind the left hip, carry the new drum rigidly with the palm.
    r.pose.bones['WPN_SOCKET_Magazine'].matrix=goals['l']@raw[lock*2]['P']['hand_l'].inverted()@raw[lock*2]['P']['WPN_SOCKET_Magazine'];update()'''
assert old in s;s=s.replace(old,new)
s=s.replace("'support_release_frame':hold,", "'support_release_frame':hold,'new_drum_acquire_frame':acquire,'behind_hip_position':list(behind.translation),")
p.write_text(s)
