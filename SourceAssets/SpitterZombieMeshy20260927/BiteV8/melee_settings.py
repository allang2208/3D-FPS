"""Shared saved defaults for the bite installer and full asset rebuild."""

def apply_melee_defaults(cdo, attack):
    values = {
        'attack_range': attack['attack_range_base_cm'],
        'attack_damage': attack['attack_damage'],
        'contact_time': attack['contact_seconds'],
        'contact_end': attack['contact_end_seconds'],
        'recovery_time': attack['recovery_seconds'],
    }
    for name,value in values.items(): cdo.set_editor_property(name,value)
    # User is retaining an editor with the previous native DLL. Its attack clock
    # clamps to clip length: a later release time disables the old projectile
    # branch while the inherited melee window above remains active. These legacy
    # fields disappear after the new native class is built, so never add them back.
    try: cdo.get_editor_property('release_time')
    except Exception: return dict(values=values,legacy_projectile_gate=False)
    cdo.set_editor_property('release_time',attack['seconds']+1.)
    cdo.set_editor_property('spit_sound',None)
    cdo.set_editor_property('spit_cooldown',attack['seconds']+attack['recovery_seconds'])
    return dict(values=values,legacy_projectile_gate=True,
        legacy_release_seconds=attack['seconds']+1.,
        native_build='pending_editor_close_per_user_request')
