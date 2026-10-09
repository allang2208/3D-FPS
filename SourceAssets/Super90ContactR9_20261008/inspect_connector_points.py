from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'fit_actual_connector.py').read_text().split('out=[]')[0],str(O/'fit_actual_connector.py'),'exec'))
for point in [(-.011,0,0),(-.020,.03,0),(0,.042,0),(0,.058,.017),(0,.075,0),(-.011,0,-.03),(-.011,0,.03)]:
    print('CLEAR',point,[round(t.find_nearest(Vector(point))[3]*1000,3) for t in trees])
