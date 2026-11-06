"""Key indices at 120 Hz, relative to release. See HighlandRidgeThrust.h."""
FPS = 120
SOURCE_EXTENSION = 16  # Furthest forward tip on both installed grips.
EXTENSION = SOURCE_EXTENSION // 2
HOLD = 36
CONTACT = 2
LEAD = 40


def retime_release(poses):
    extension = poses[SOURCE_EXTENSION]
    return poses[:SOURCE_EXTENSION+1:2] + [extension]*HOLD + poses[SOURCE_EXTENSION+1:]
