from pathlib import Path
exec(compile((Path(__file__).parent/'fit_digits.py').read_text().rsplit('\nfit=least_squares',1)[0],__file__,'exec'))
import itertools
original=np.array(json.loads((r/'hold_fit_digits.json').read_text())['parameters'])
offsets=sorted(itertools.product((0.,-.05,.05,-.1,.1,-.15,.15),repeat=3),key=lambda a:np.linalg.norm(a))
for offset in offsets:
    x=original.copy();x[:3]+=offset;q,w=pose(x);hits=collisions(q)
    if sum(hits.values())==0:
        result=dict(parameters=x.tolist(),digit_names=digitnames,hits=hits,surface_settle_cm=list(offset),hand_world={n:a.tolist() for n,a in w.items()})
        (r/'hold_fit.json').write_text(json.dumps(result,indent=2));print('CONTACT_SETTLED',offset,hits,flush=True);break
else:raise RuntimeError('No contact-safe settling within 1.5 mm')
