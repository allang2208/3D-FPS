"""Authored coal positions in the hearth mesh's local centimetre frame."""
def grate_coals(rng):
    for row in range(4):
        for col in range(7):
            x = -29 + 9.5*col + rng.uniform(-1.6,1.6)
            y = -21 + 10*row + rng.uniform(-1.3,1.3)
            yield (800+7*row+col, x, y, 90.1, 5.7, 6.3, rng.uniform(3.2,6.1))
