"""Keep gameplay costs when exporting meshes; normalize new firearm recipes to selected-metal costs."""
import copy

METALS = {'ironIngot', 'copperIngot', 'silverIngot', 'goldIngot'}


def preserve_gameplay_recipe(recipe, previous=None):
    result = copy.deepcopy(recipe)
    # Five 5-second follow rounds, one second ready and four two-second intervals.
    result['calibration_seconds'] = 34.0
    source = previous if previous and previous.get('metal_count', 0) > 0 else result
    if source.get('metal_count', 0) > 0:
        for key in ('inputs', 'legacy_inputs', 'metal_count'):
            if key in source:
                result[key] = copy.deepcopy(source[key])
    else:
        original = copy.deepcopy(source['inputs'])
        result['legacy_inputs'] = original
        result['inputs'] = [entry for entry in original if entry['item'] not in METALS]
        # First tuning pass preserves each firearm's former iron requirement.
        result['metal_count'] = next((entry['count'] for entry in original if entry['item'] == 'ironIngot'),
                                    sum(entry['count'] for entry in original if entry['item'] in METALS))
    if not result['inputs'] or result['metal_count'] <= 0:
        raise ValueError('Assembly needs fixed base inputs and a positive selected-metal count: ' + result['id'])
    return result
