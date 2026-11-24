"""Boundary between the exposed blade steel and the raised shield, in fitted mesh cm."""

HALF_WIDTH = 2.98
EDGE_HEIGHT = -0.61
CENTER_RISE = 2.12
CURVE_POWER = 1.85


def contains(x, z):
    lateral = abs(x)
    ridge = EDGE_HEIGHT + CENTER_RISE * max(0.0, 1.0 - lateral / HALF_WIDTH) ** CURVE_POWER
    return lateral <= HALF_WIDTH and z >= ridge


def mode_shader():
    return f"""if (GuardRoot < 0.5) return Mode;
float x = abs(P.x);
float ridge = {EDGE_HEIGHT} + {CENTER_RISE} * pow(saturate(1.0 - x/{HALF_WIDTH}), {CURVE_POWER});
return (x <= {HALF_WIDTH} && P.z >= ridge) ? Mode : 0.0;"""


def damascus_shader():
    # Both steel sections use the original fitted sword's pivot. At their join
    # the source blade spans X = -2.82747 .. 2.83379 cm at Z = 3.696886 cm.
    # Fade back to each blade's established field above the seat.
    return """float blade = smoothstep(4.0, 24.0, P.z);
float center = lerp(0.00316, (Lo.x + Hi.x) * 0.5, blade);
float width = lerp(5.66126, max(Hi.x - Lo.x, 0.02), blade);
float root = lerp(3.696886, Lo.z, blade);
float across = P.x - center;
return float4(across, P.z - root, 0.5 + across / width, 0.0);"""
