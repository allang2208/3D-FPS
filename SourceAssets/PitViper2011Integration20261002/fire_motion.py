"""M1911 recoil intent adapted to the native Pit Viper arm/grip chain."""
from mathutils import Matrix

def settings(side, kind):
    aimed = kind.startswith('aim')
    return dict(duration=.30 if aimed else .35,
                source_gain=.32 if aimed else .62 if side == 'single' else .95,
                reference='M1911 native authored fire; local-pose blend before Pit Viper contact fit',
                timing='Whole reference cycle compressed into presentation duration; fire interval unchanged')

def pose(base, fired, parents, gain):
    """Blend LOCAL transforms, preserving native arm lengths and helper chains."""
    output = {}
    def build(name):
        if name in output:
            return output[name]
        parent = parents[name]
        a = base[parent].inverted() @ base[name] if parent else base[name]
        b = fired[parent].inverted() @ fired[name] if parent else fired[name]
        ap, aq, asc = a.decompose()
        bp, bq, bsc = b.decompose()
        if aq.dot(bq) < 0:
            bq.negate()
        local = Matrix.LocRotScale(ap.lerp(bp, gain), aq.slerp(bq, gain), asc.lerp(bsc, gain))
        output[name] = build(parent) @ local if parent else local
        return output[name]
    for name in base:
        build(name)
    return output
