from pathlib import Path
exec(compile(Path(__file__).with_name('fit_grasp.py').read_text().split('report={}')[0],str(Path(__file__).with_name('fit_grasp.py')),'exec'))
report={}
for side in ['l','r']:
    f=Fit(side);before=f.evaluate(True)
    for digit in f.digits:
        dp=f.digits[digit];best=copy.deepcopy(dp);score=f.evaluate(only=digit)
        for spread in ([-85,-70,-55,-40,-25] if digit=='thumb' else [-10,0,10]):
            for a in ([-5,10,25,40,55] if digit=='thumb' else [25,40,55,70]):
                for b in ([15,30,45] if digit=='thumb' else [30,45,60]):
                    for c in [15,30,40]:
                        dp.update(spread=[spread]*3,flex=[a,a+b,a+b+c])
                        if not f.valid(dp):continue
                        val=f.evaluate(only=digit)
                        if val<score:score=val;best=copy.deepcopy(dp)
        dp.update(best)
        for step in [4,2,1,.5]:
            for _ in range(2):
                for j in range(3):
                    orig=dp['flex'].copy();winner=orig;score=f.evaluate(only=digit)
                    for delta in [-step,step]:
                        dp['flex']=[v+(delta if k>=j else 0) for k,v in enumerate(orig)]
                        if not f.valid(dp):continue
                        val=f.evaluate(only=digit)
                        if val<score:score=val;winner=dp['flex'].copy()
                    dp['flex']=winner
                old=dp['spread'][0];win=old;score=f.evaluate(only=digit)
                for delta in [-step,step]:
                    v=old+delta
                    if not (-90<=v<=-20 if digit=='thumb' else -12<=v<=12):continue
                    dp['spread']=[v]*3;val=f.evaluate(only=digit)
                    if val<score:score=val;win=v
                dp['spread']=[win]*3
        print('DIGIT',side,digit,score,json.dumps(dp),flush=True)
    report[side]={'before':before,'after':f.evaluate(True)}
    (OUT/'fitted.json').write_text(json.dumps(m,indent=2))
(OUT/'digit_search_report.json').write_text(json.dumps(report,indent=2))
