from pathlib import Path
import json, hashlib, datetime
P=Path(__file__).resolve().parent;R=P.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
native=[]
names=['jilei-intent','heavy-formula','thor-assets-mods','zhenting','recall','switch','preview','storm-lifecycle']
receipts={r['case']:r for r in read(P/'native-receipts-initial.json')}
receipts.update({r['case']:r for r in read(P/'native-receipts.json')})
for name in names:
    report=read(P/(name+'.json'))
    native.append(dict(name=name,count=len(report['checks']),passed=receipts[name]['exit_code']==0,report=name+'.json'))
wire=[]
for mode in ['Listen','Dedicated']:
    runs=sorted(p for p in P.glob(mode+'-*') if (p/'receipt.json').exists())
    if not runs:continue
    run=runs[-1];receipt=read(run/'receipt.json');host=read(run/'host.json')
    wire.append(dict(mode=mode,passed=receipt['passed'],cases=len(host['cases']),report=str(run.relative_to(P)/'host.json'),
        receipt=str(run.relative_to(P)/'receipt.json'),lag_ms=60,packet_loss_percent=3,peers=len(receipt['peer_exits'])))
assets=read(P/'assets.json');build=read(P/'build_receipt.json')
report=dict(at=datetime.datetime.now().isoformat(),passed=build['complete'] and all(n['passed'] for n in native) and assets['passed'] and len(wire)==2 and all(w['passed'] for w in wire),
    native=native,native_count=sum(n['count'] for n in native),asset_count=len(assets['checks']),assets_passed=assets['passed'],wire=wire,build=build,
    saved_asset_repairs=read(P/'seat_tangent_receipt.json'),audio_metadata=read(P/'audio_metadata_receipt.json'),
    limitations=['No rendered hand animation or visual acceptance','No audio audition','No real inventory upload/UI integration in the isolated network fixture','No reconnect or map travel test'],
    editor_dll_sha256=hashlib.sha256((R/'Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest())
(P/'review_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['passed','native_count','asset_count','wire']},ensure_ascii=False))
