# -*- coding: utf-8 -*-
"""Verify gunsmith.json: structural integrity + effects/stats numeric consistency.

Usage: py Tools/Weapons/check_attachment_consistency.py
Exits 1 when a mismatch is found. Qualitative wording ("装填耗时更长",
"开镜时间不变") is reported as INFO, not a failure, because the catalog standard
allows descriptive text there.
"""
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'Content' / 'ColdSteelData' / 'gunsmith.json'

d = json.load(open(SRC, encoding='utf-8'))
slots = d['slots']
common = d.get('common_options', {})
problems, infos = [], []

# ---- structural ----
for w in d['weapons']:
    own = w.get('options', {}) or {}
    for s, arr in own.items():
        if s not in slots:
            problems.append('%s: slot %s not in slots list' % (w['id'], s))
        ids = [o['id'] for o in arr]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            problems.append('%s/%s: duplicate ids %s' % (w['id'], s, dup))
        if s not in w.get('allowed', []):
            problems.append('%s: slot %s listed but not allowed' % (w['id'], s))
        for o in arr:
            for req in ('id', 'name', 'description', 'effects', 'stats'):
                if req not in o:
                    problems.append('%s/%s/%s: missing %s' % (w['id'], s, o.get('id'), req))
            if re.search(r'\d', o.get('description', '')) and '%' not in o.get('description', ''):
                infos.append('%s/%s/%s: description contains digits: %s'
                             % (w['id'], s, o['id'], o['description']))

# ---- effects vs stats ----
PAT = {
    'ads': (r'(?:开镜耗时|ADS瞄准耗时|开镜速度)(增加|减少|降低|提高)(\d+)%',
            {'增加': +1, '减少': -1, '降低': -1, '提高': +1}),
    'recoil': (r'后坐力(降低|增加|减少|提高)(\d+)%',
               {'降低': -1, '减少': -1, '增加': +1, '提高': +1}),
    'stability': (r'(?:枪械稳定性|稳定性)(提高|降低|增加|减少)(\d+)%',
                  {'提高': +1, '增加': +1, '降低': -1, '减少': -1}),
    'spread': (r'腰射随机散布(减少|增加)(\d+)%', {'减少': -1, '增加': +1}),
    'speed': (r'子弹速度(降低|提高|增加|减少)(\d+)%', {'降低': -1, '减少': -1, '提高': +1, '增加': +1}),
    'range': (r'有效射程(减少|增加)(\d+)%', {'减少': -1, '增加': +1}),
    'mag': (r'弹匣容量增加(\d+)发', None),
}
QUAL = ['开镜时间不变', '缩短开镜耗时', '装填耗时更长', '装填耗时增加', '无额外数值修正',
        '提供前向照明', '换弹更快', '普通与空仓换弹均为', '弹仓内全部余弹',
        '不返还背包', '弓手与配件换弹加成']


def normalize(text):
    """"后坐力控制提高10%" means recoil index drops 10%; fold it into the plain wording."""
    return (text.replace('后坐力控制提高', '后坐力降低').replace('后坐力控制增加', '后坐力降低')
                .replace('后坐力控制降低', '后坐力增加').replace('后坐力控制减少', '后坐力增加'))


def pct(mult):
    return round((mult - 1) * 100)


def check(where, o, slot):
    st = o.get('stats') or {}
    text = normalize('；'.join(e['text'] for e in o.get('effects', [])))
    if not st:
        if text and not any(q in text for q in QUAL) and '提供前向照明' not in text:
            infos.append('%s: stats empty but effects say: %s' % (where, text))
        return
    # ads
    if 'ads_percent' in st:
        m = re.search(PAT['ads'][0], text)
        want = round(st['ads_percent'] * 100)
        if m:
            got = PAT['ads'][1][m.group(1)] * int(m.group(2))
            if got != want:
                problems.append('%s: ads_percent=%s (%+d%%) but effect says %s'
                                % (where, st['ads_percent'], want, m.group(0)))
        elif '开镜时间不变' not in text and '缩短开镜耗时' not in text:
            infos.append('%s: ads_percent=%s has no numeric ADS effect (text: %s)' % (where, st['ads_percent'], text))
    # mag_delta (absolute)
    if st.get('mag_delta'):
        m = re.search(r'弹匣容量增加(\d+)发', text)
        if m:
            if int(m.group(1)) != st['mag_delta']:
                problems.append('%s: mag_delta=%s but effect says %s' % (where, st['mag_delta'], m.group(0)))
        else:
            problems.append('%s: mag_delta=%s missing 弹匣容量增加N发' % (where, st['mag_delta']))
    # multipliers
    for key, statkey in (('recoil', 'recoil_mult'), ('stability', 'stability_mult'),
                         ('spread', 'hip_spread_mult'), ('speed', 'bullet_speed_mult'),
                         ('range', 'range_mult')):
        if statkey not in st:
            continue
        want = pct(st[statkey])
        m = re.search(PAT[key][0], text)
        if not m:
            infos.append('%s: %s=%s (%+d%%) has no matching effect (text: %s)'
                         % (where, statkey, st[statkey], want, text))
            continue
        got = PAT[key][1][m.group(1)] * int(m.group(2))
        if got != want:
            problems.append('%s: %s=%s (%+d%%) but effect says %s "%s"'
                            % (where, statkey, st[statkey], want, PAT[key][0], m.group(0)))


for w in d['weapons']:
    for s, arr in (w.get('options', {}) or {}).items():
        for o in arr:
            check('%s/%s/%s' % (w['id'], s, o['id']), o, s)
for s, arr in common.items():
    for o in arr:
        check('common/%s/%s' % (s, o['id']), o, s)

print('=== PROBLEMS (%d) ===' % len(problems))
for p in problems:
    print('  ! ' + p)
print('=== INFO (%d) ===' % len(infos))
for i in infos:
    print('  - ' + i)

report = ROOT / 'Saved' / 'Weapons' / 'consistency-report.txt'
report.parent.mkdir(parents=True, exist_ok=True)
with open(report, 'w', encoding='utf-8') as f:
    f.write('# %s 生成，由 Tools/Weapons/check_attachment_consistency.py 覆盖写入\n' % datetime.now().strftime('%Y-%m-%d %H:%M'))
    f.write('=== PROBLEMS (%d) ===\n' % len(problems))
    for p in problems:
        f.write('  ! %s\n' % p)
    f.write('=== INFO (%d) ===\n' % len(infos))
    for i in infos:
        f.write('  - %s\n' % i)
print(report)
sys.exit(1 if problems else 0)