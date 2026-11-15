"""Restore collection fields by their published IDs after refreshing PN_GrassLibrary."""
import unreal as u


COLLECTION = '/Game/PN_GrassLibrary/Materials/PN_WindParameters'
# Material expressions serialize the field ID. A new field with the same name
# and a random ID still resolves to None when the existing packages load.
SCALARS = (
    ('WindowSize', 4800., '4C85816F48EBFA1A14A34FB822BFB518'),
    ('WorldTime', 0., 'CC95C1C44BD2D7F72F8AE8B58B5A6EF2'),
    ('RegrowthSeconds', 2.4, '37E2368044F0211232749681CDE7150A'),
    ('bEnabled', 0., '172D7B4941AB9246E42984AC8495255E'),
    ('WaveSpeed', 1800., '5194AFA24844438462325E8AD3EDB980'),
    ('ReadIsB', 0., '43AFB2B94BA61A380EE041BE9D89F397'),
    ('GrassWaveStartTime', 0., '4D2D16A44BF8D05D4B5B028AD2FAE797'),
    ('GrassWaveRadius', 0., '04D46C554D6BEAFDFE876488DFFDF158'),
    ('GrassWaveStrength', 0., 'B4941CC74820E95B340DEB83BB83899D'),
    ('GrassHoldSeconds', .6, 'DFEEFCFD467F80A4C1D5F9869C33E559'),
    ('GrassRecoverSeconds', 1.8, 'E4C2080B48908545D8FEE698F458103B'),
    ('GrassCoreFraction', .68, '8A6C0A2F420DC5C5DA3B1BB662E07FE1'),
    ('GrassBendAngle', 74., '1126974C4D4E486F5D9DBBA515672A59'),
    ('GrassFlatWindScale', .03, 'AD5873874A41E2E61D847992CFF85F5E'),
    ('GrassForwardBias', .97, '3DBF6CCC42EDFE69B3FB298942151A2C'),
)
VECTORS = (
    ('Center', (0, 0, 0, 0), 'C4B5B6FF4D36E08A3D6AE48D7D21366E'),
    ('WaveOrigin', (.5, .5, 0, 0), '5E4CB3DC4400930DCD510F85A84CADB8'),
    ('GrassBodyContact', (0, 0, 0, 0), '805EF8824EE2D75A603C8A98F9D1E8C7'),
    ('GrassBodyMotion', (0, 0, 0, 0), 'AB5607BF46E348B25D006B820F2D26E5'),
    ('RainforestRegion', (-12000, 10000, 11000, 8500), '049F7CC544F6CEE400EC43A69BD67083'),
    ('RainforestControl', (0, .35, 0, 0), 'BF7D18D44F12D04C4ACEDEBAA21C437B'),
    ('RainforestWeather', (0, 0, 0, 0), '4E1C0C6E43538BA02B6D269DD3111E10'),
)


def restore():
    collection = u.load_asset(COLLECTION)
    if not collection:
        raise RuntimeError('Missing ' + COLLECTION)
    added = []
    for field, spec, row_type in (
        ('scalar_parameters', SCALARS, u.CollectionScalarParameter),
        ('vector_parameters', VECTORS, u.CollectionVectorParameter),
    ):
        rows = list(collection.get_editor_property(field))
        previous_count = len(rows)
        existing = {str(row.get_editor_property('parameter_name')) for row in rows}
        for name, default, guid in spec:
            if name in existing:
                continue
            value = u.LinearColor(*default).export_text() if isinstance(default, tuple) else str(default)
            row = row_type()
            row.import_text(f'(ParameterName="{name}",DefaultValue={value},Id={guid})')
            if 'Id=' + guid not in row.export_text():
                raise RuntimeError('Could not restore original field ID for ' + name)
            rows.append(row)
            added.append(name)
        if len(rows) != previous_count:
            collection.set_editor_property(field, rows)
    if added:
        if not u.EditorAssetLibrary.save_loaded_asset(collection, False):
            raise RuntimeError('Could not save ' + COLLECTION)
        u.log('Restored hills grass fields: ' + ', '.join(added))
    return collection


if __name__ == '__main__':
    restore()
