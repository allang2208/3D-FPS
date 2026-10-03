"""Author one eased approach to the mouth with small, non-looping variations."""

def food_motion(definition):
    def key(time, grip, rotation):
        return {'time': time, 'grip': grip, 'rotation': rotation}

    # Uneven key times/spacing shape acceleration in the existing cubic-Hermite
    # grip track. Tiny lateral/vertical and wrist offsets are deliberately
    # unequal; no sine loop, random per-frame shake, or repeated bite strokes.
    if definition == 'bread':
        times = {'grab': .22, 'uncap': .64, 'drink_start': 1.10, 'drink_end': 1.90,
                 'contact': 1.86, 'release': 2.25, 'recover': 2.25, 'duration': 2.4}
        keys = [
            key(0.00, [23, -23, -35], [0, -8, 0]),
            key(.22, [23, -23, -35], [0, -8, 0]),
            key(.40, [26.6, -21.5, -27], [2, -8, 1.5]),
            key(.66, [29, -16, -16], [18, -7.3, 3.0]),
            key(.90, [18, -8, -13], [61, -6, 2]),
            key(1.10, [15.5, -6.38, -11.96], [63, -5.8, 2.2]),
            key(1.29, [13.6, -5.05, -11.51], [64.2, -6.25, 1.6]),
            key(1.50, [12.0, -4.39, -10.80], [64.7, -5.95, 2.45]),
            key(1.70, [10.85, -3.82, -10.39], [65.35, -6.2, 1.88]),
            key(1.86, [10, -3.5, -10], [65, -6, 2]),
            key(1.96, [11.3, -4.4, -12.5], [62, -6, 2]),
            key(2.12, [20, -14, -24], [25, -7, 1.4]),
            key(2.25, [23, -23, -35], [0, -8, 0]),
            key(2.40, [23, -23, -35], [0, -8, 0]),
        ]
    elif definition == 'baguette_bread':
        times = {'grab': .24, 'uncap': .78, 'drink_start': 1.31, 'drink_end': 2.16,
                 'contact': 2.12, 'release': 2.55, 'recover': 2.55, 'duration': 2.7}
        keys = [
            key(0.00, [23, -23, -35], [0, -8, 0]),
            key(.24, [23, -23, -35], [0, -8, 0]),
            key(.46, [26.2, -21.2, -27], [2, -8, 1.5]),
            key(.78, [29, -16, -16], [18, -7.3, 3.0]),
            key(1.00, [22, -7.5, -13.8], [61, -6, 2]),
            key(1.21, [20.2, -6.78, -13.06], [63, -5.8, 2.2]),
            key(1.41, [18.8, -5.70, -12.69], [64.2, -6.25, 1.55]),
            key(1.65, [17.4, -5.46, -12.10], [64.7, -5.95, 2.4]),
            key(1.91, [16.5, -4.62, -11.80], [65.35, -6.2, 1.88]),
            key(2.12, [16, -4.5, -11.5], [65, -6, 2]),
            key(2.24, [17.5, -5.4, -14], [62, -6, 2]),
            key(2.42, [21, -16, -26], [23, -7, 1.4]),
            key(2.55, [23, -23, -35], [0, -8, 0]),
            key(2.70, [23, -23, -35], [0, -8, 0]),
        ]
    else:
        raise ValueError('No authored food motion for ' + definition)
    return {'times': times, 'keys': keys}
