"""Pure-math regression for the gun FX clock and motion equations (no Unreal required).

Run: python Tools/AssetPipeline/verify_fx_time_invariance.py
This checks the mathematical model against closed-form event/trajectory oracles.
It does not compile C++, render materials, or validate world collision responses.
"""

from dataclasses import dataclass
from math import ceil, exp, floor, sqrt
from pathlib import Path
import re


PERIOD = 0.11
MAX_LIFE = 1.25
THRESHOLD = 0.10
COOLING = 0.28
DRAG = 1.3
POOL_LIMIT = 64
checks = 0


def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def scale(a, s):
    return tuple(x * s for x in a)


def distance(a, b):
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def integrate(position, velocity, acceleration, dt, drag):
    if drag:
        decay = exp(-drag * dt)
        travel = (1.0 - decay) / drag
        position = add(position, add(scale(velocity, travel), scale(acceleration, (dt - travel) / drag)))
        velocity = add(scale(velocity, decay), scale(acceleration, travel))
    else:
        position = add(position, add(scale(velocity, dt), scale(acceleration, 0.5 * dt * dt)))
        velocity = add(velocity, scale(acceleration, dt))
    return position, velocity


def trajectory_oracle(position, velocity, acceleration, elapsed, drag):
    # Independent form using terminal velocity and the initial velocity difference.
    if drag:
        terminal = scale(acceleration, 1.0 / drag)
        difference = add(velocity, scale(terminal, -1.0))
        decay = exp(-drag * elapsed)
        return (
            add(position, add(scale(terminal, elapsed), scale(difference, (1.0 - decay) / drag))),
            add(terminal, scale(difference, decay)),
        )
    return (
        tuple(p + v * elapsed + a * elapsed**2 / 2 for p, v, a in zip(position, velocity, acceleration)),
        tuple(v + a * elapsed for v, a in zip(velocity, acceleration)),
    )


def emission_step(heat, phase, dt, pending_heat=0.0):
    hot_dt = min(max((heat - THRESHOLD) / COOLING, 0.0), dt)
    offsets = []
    due = 0
    if hot_dt > 0:
        total = phase + hot_dt
        due = floor((total + 1e-9) / PERIOD)
        first = PERIOD - phase
        first_visible = min(max(ceil((dt - MAX_LIFE - first) / PERIOD), 0), due)
        offsets = [first + i * PERIOD for i in range(first_visible, due)]
        phase = max(0.0, total - due * PERIOD)
    cooled = max(0.0, heat - dt * COOLING)
    if cooled <= THRESHOLD:
        phase = 0.0
    return min(1.0, cooled + pending_heat), phase, offsets, due


def frames(fps, duration, hitch=False):
    elapsed = 0.0
    inserted = False
    while elapsed < duration - 1e-12:
        # Place the same 200 ms hitch at t=.7 in every schedule.
        if hitch and not inserted and elapsed >= 0.7 - 1e-12:
            dt = min(0.2, duration - elapsed)
            inserted = True
        else:
            dt = min(1.0 / fps, duration - elapsed)
            if hitch and not inserted:
                dt = min(dt, 0.7 - elapsed)
        elapsed += dt
        yield dt


def muzzle(t):
    # Linear world motion is exactly reconstructible from the two socket samples.
    return (12.0 * t, -3.0 * t, 160.0 + 4.0 * t)


@dataclass
class Particle:
    birth: float
    position: tuple
    velocity: tuple
    age: float
    rotation: float


def simulate(fps, duration, hitch=False):
    heat, phase, now = 1.0, 0.0, 0.0
    particles = []
    event_count = 0
    peak = 0
    acceleration = (0.8, 0.0, 7.0)
    initial_velocity = (13.5, -2.0, 22.0)
    for dt in frames(fps, duration, hitch):
        start, now = now, now + dt
        alive = []
        for p in particles:
            p.age += dt
            if p.age < MAX_LIFE - 1e-10:
                p.position, p.velocity = integrate(p.position, p.velocity, acceleration, dt, DRAG)
                p.rotation += 17.0 * dt
                alive.append(p)
        particles = alive
        heat, phase, offsets, due = emission_step(heat, phase, dt)
        event_count += due
        for offset in offsets:
            birth = start + offset
            age = max(0.0, dt - offset)
            if age >= MAX_LIFE - 1e-10:
                continue
            fraction = offset / dt
            origin = add(scale(muzzle(start), 1.0 - fraction), scale(muzzle(now), fraction))
            origin = add(origin, (2.0, 0.0, 0.0))
            position, velocity = integrate(origin, initial_velocity, acceleration, age, DRAG)
            particles.append(Particle(birth, position, velocity, age, 17.0 * age))
        peak = max(peak, len(particles))

    last_birth = min(duration, (1.0 - THRESHOLD) / COOLING)
    expected_count = floor((last_birth + 1e-9) / PERIOD)
    expected_births = [i * PERIOD for i in range(1, expected_count + 1) if duration - i * PERIOD < MAX_LIFE - 1e-10]
    check(event_count == expected_count, f"{fps} Hz hitch={hitch}: event count")
    check(len(particles) == len(expected_births), f"{fps} Hz hitch={hitch}: live count")
    max_error = 0.0
    for p, birth in zip(particles, expected_births):
        age = duration - birth
        origin = add(muzzle(birth), (2.0, 0.0, 0.0))
        position, velocity = trajectory_oracle(origin, initial_velocity, acceleration, age, DRAG)
        error = max(distance(p.position, position), distance(p.velocity, velocity), abs(p.age - age), abs(p.rotation - 17 * age))
        max_error = max(max_error, error)
    check(max_error < 1e-8, f"{fps} Hz hitch={hitch}: event age, world trajectory, velocity and rotation")
    check(peak <= POOL_LIMIT, f"{fps} Hz hitch={hitch}: pool bound")
    return event_count, len(particles), peak, max_error


def main():
    source = Path(__file__).resolve().parents[2] / "Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp"
    header = source.with_suffix(".h").read_text(encoding="utf-8-sig")
    code = source.read_text(encoding="utf-8-sig")
    for name, expected in [("SmokePeriod", PERIOD), ("SmokeMaxLifetime", MAX_LIFE), ("HeatThreshold", THRESHOLD), ("HeatCoolingRate", COOLING), ("SmokeDrag", DRAG)]:
        match = re.search(rf"\b{name}\s*=\s*([\d.]+)", code)
        check(match is not None and float(match[1]) == expected, f"source constant {name}")
    check("MaxParticles = 64" in header, "source pool remains 64")
    print("Pure mathematics; matching C++ constants checked. UE runtime/collision not exercised.")
    for duration in (2.0, 4.0):
        for fps in (30, 60, 144):
            for hitch in (False, True):
                count, live, peak, error = simulate(fps, duration, hitch)
                print(f"PASS {fps:3} Hz hitch200ms={str(hitch):5} t={duration:.1f}s events={count:2} live={live:2} peak={peak:2} max_error={error:.3g}")

    heat, phase, offsets, _ = emission_step(1.0, 0.08, 0.2)
    ages = [0.2 - offset for offset in offsets]
    check(len(ages) == 2 and abs(ages[0] - 0.17) < 1e-12 and abs(ages[1] - 0.06) < 1e-12, "hitch births age 170/60 ms")
    check(abs(phase - 0.06) < 1e-12, "hitch keeps 60 ms remainder")
    heat, phase, offsets, _ = emission_step(0.13, 0.08, 0.2)
    check(len(offsets) == 1 and abs(0.2 - offsets[0] - 0.17) < 1e-12 and phase == 0.0, "threshold crossing keeps cold-tail age and resets phase")

    heat, phase, offsets, _ = emission_step(0.0, 0.0, 100.0, pending_heat=0.18)
    check(heat == 0.18 and phase == 0.0 and not offsets, "idle then shot does not backdate new heat or emit debt")
    heat, phase, offsets, _ = emission_step(heat, phase, 0.11)
    check(len(offsets) == 1 and abs(offsets[0] - 0.11) < 1e-12, "new heat emits only after its first complete period")
    _, phase, offsets, due = emission_step(1.0, 0.08, 100.0)
    check(not offsets and due == 29 and phase == 0.0, "long hitch instantiates no expired history")

    # Uncollided casings retain exact ballistic motion across every substep schedule.
    origin, initial_velocity, gravity = (0.0, 0.0, 160.0), (150.0, 100.0, 85.0), (0.0, 0.0, -650.0)
    expected_p, expected_v = trajectory_oracle(origin, initial_velocity, gravity, 1.0, 0.0)
    for fps in (30, 60, 144):
        for hitch in (False, True):
            position, velocity = origin, initial_velocity
            for dt in frames(fps, 1.0, hitch):
                steps = min(max(ceil(dt / 0.025), 1), 64)
                for _ in range(steps):
                    position, velocity = integrate(position, velocity, gravity, dt / steps, 0.0)
            check(max(distance(position, expected_p), distance(velocity, expected_v)) < 1e-8, f"ballistic full delta {fps} Hz hitch={hitch}")

    print("PASS hitch ages=170/60ms remainder=60ms; cold threshold; no idle debt; expired catch-up skipped; ballistic substeps")
    print(f"FX_TIME_INVARIANCE_COMPLETE checks={checks} failures=0")


if __name__ == "__main__":
    main()
