from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'common','exec'))
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'joint signatures','exec'))
out={}
for family in ('base','skeleton_base','skeleton_mag10_balanced'):
    out[family]=[]
    for t in (.03,.05,.08,.10,.13,.15,.25,.325,.46,.55,.60,.65,.70,.72):
        row,_=compose(entry(family,'quick_melee'),t)
        _,sig=corrective_weights(row,[])
        fore=(row['hand_r'].translation-row['lowerarm_r'].translation).normalized()
        native_axis=(native['hand_r'].translation-native['lowerarm_r'].translation).normalized()
        wanted=row['hand_r'].to_quaternion()@native['hand_r'].to_quaternion().inverted()@native_axis
        record={'time':t,'axis_bend':math.degrees(fore.angle(wanted)),'elbow_flex_wrist_flex_deviation_roll':sig['r'][:4]}
        out[family].append(record)
        print(family,record,flush=True)
(O/'right_before.json').write_text(json.dumps(out,indent=2))
