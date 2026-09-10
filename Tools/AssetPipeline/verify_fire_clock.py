"""Pure-math acceptance for the bounded automatic-fire event clock.

Run: python Tools/AssetPipeline/verify_fire_clock.py
Checks event scheduling and input/blocker boundaries against elapsed-time oracles.
No Unreal imports, engine launch, rendering, or C++ compilation are performed.
"""

from dataclasses import dataclass, field
from math import floor, fmod
from pathlib import Path
import re


INTERVAL = 0.12
MAX_CATCH_UP = 4
EPSILON = 1e-6
checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


@dataclass
class FireClock:
    now: float = 0.0
    held: bool = False
    sprint: bool = False
    sliding: bool = False
    ammo: int = 100
    reserve: int = 0
    next_shot: float = 0.0
    sprint_unlock: float = 0.0
    sprint_started: float = 0.0
    action_start: float = 0.0
    action_duration: float = 0.0
    action: str = "idle"
    first_actual: float = -1.0
    last_actual: float = -1.0
    shots: list = field(default_factory=list)
    reload_settlements: int = 0

    def lock(self, start):
        self.sprint_unlock = max(self.sprint_unlock, start + 0.18)
        self.next_shot = max(self.next_shot, self.sprint_unlock)

    def press(self, now):
        self.now = now
        if not self.held:
            self.next_shot = max(self.next_shot, now)
            self.first_actual = -1.0
        self.held = True
        if self.sprint:
            self.lock(now)
            self.sprint = False
        self.service()

    def release(self):
        self.held = False

    def start_action(self, action, duration):
        if self.action != "idle":
            return False
        self.action = action
        self.action_start = self.now
        self.action_duration = duration
        return True

    def tick(self, now):
        self.now = now
        if self.action != "idle" and now >= self.action_start + self.action_duration:
            completion = self.action_start + self.action_duration
            self.next_shot = max(self.next_shot, completion)
            if self.action == "reload":
                loaded = min(30 - self.ammo, self.reserve)
                self.ammo += loaded
                self.reserve -= loaded
                self.reload_settlements += 1
            self.action = "idle"
            if self.held and self.sprint:
                self.lock(max(completion, self.sprint_started))
                self.sprint = False
        return self.service()

    def stop_slide(self):
        self.sliding = False
        self.next_shot = max(self.next_shot, self.now)

    def service(self):
        before = len(self.shots)
        if not self.held:
            return 0
        if self.action != "idle" or self.sliding or self.sprint:
            self.next_shot = max(self.next_shot, self.now)
            return 0
        self.next_shot = max(self.next_shot, self.sprint_unlock)
        if self.now < self.sprint_unlock:
            return 0
        for _ in range(MAX_CATCH_UP):
            if not self.held or self.now + EPSILON < self.next_shot:
                break
            previous = self.next_shot
            if self.ammo <= 0:
                if self.reserve > 0:
                    self.start_action("reload", 3.466667)
                else:
                    self.release()
            else:
                self.ammo -= 1
                self.shots.append((self.next_shot, self.now))
                self.last_actual = self.now
                if self.first_actual < 0:
                    self.first_actual = self.now
                self.next_shot += INTERVAL
            if self.action != "idle" or self.sliding or self.sprint or not self.held or self.next_shot <= previous:
                break
        if self.held and self.action == "idle" and not self.sliding and not self.sprint and self.now + EPSILON >= self.next_shot:
            remainder = fmod(max(0.0, self.now - self.next_shot), INTERVAL)
            self.next_shot = self.now + INTERVAL - remainder
        return len(self.shots) - before


def schedule(step, duration=1.0, hitch=False):
    now = 0.0
    inserted = False
    while now < duration - 1e-12:
        if hitch and not inserted and now >= 0.54 - 1e-12:
            dt = min(0.2, duration - now)
            inserted = True
        else:
            dt = min(step, duration - now)
            if hitch and not inserted:
                dt = min(dt, 0.54 - now)
        now += dt
        yield now


def main():
    root = Path(__file__).resolve().parents[2]
    header = (root / "Source/FPSGAME/FPSGAMECharacter.h").read_text(encoding="utf-8-sig")
    interval = re.search(r"float FireInterval\s*=\s*([\d.]+)", header)
    budget = re.search(r"MaxFireCatchUpShots\s*=\s*(\d+)", header)
    check(interval is not None and float(interval[1]) == INTERVAL, "C++ interval matches mathematical fixture")
    check(budget is not None and int(budget[1]) == MAX_CATCH_UP, "C++ batch budget matches fixture")

    for label, step in [("30 Hz", 1/30), ("60 Hz", 1/60), ("144 Hz", 1/144), ("180 ms frames", 0.18), ("400 ms frames", 0.4)]:
        for hitch in (False, True):
            clock = FireClock()
            clock.press(0.0)
            peak = 0
            for now in schedule(step, hitch=hitch):
                peak = max(peak, clock.tick(now))
            expected = [i * INTERVAL for i in range(floor(1.0 / INTERVAL) + 1)]
            check(len(clock.shots) == len(expected), f"{label} hitch={hitch}: elapsed event count")
            check(all(abs(actual[0] - target) < 1e-10 for actual, target in zip(clock.shots, expected)), f"{label}: phase retained")
            check(all(actual + EPSILON >= due for due, actual in clock.shots), f"{label}: no early execution")
            check(peak <= MAX_CATCH_UP, f"{label}: batch bound")
            print(f"PASS {label:14} hitch200ms={str(hitch):5} elapsed=1s first_press=1 subsequent={len(clock.shots)-1} peak_batch={peak}")

    # Worst legal 400 ms alignment contains four due events.
    clock = FireClock(held=True, next_shot=0.001)
    check(clock.tick(0.4) == 4, "400 ms worst alignment catches all four due shots")
    check(clock.next_shot > 0.4, "400 ms batch leaves no debt")

    # Input arrives before Actor::Tick with a large previous frame delta.
    clock = FireClock(sprint=True)
    clock.press(0.4)
    check(not clock.shots and abs(clock.sprint_unlock - 0.58) < 1e-12, "sprint press starts absolute 180 ms gate")
    clock.tick(0.4)
    clock.tick(0.579)
    check(not clock.shots, "same-frame old delta cannot consume a newly started lock")
    clock.tick(0.76)
    check(len(clock.shots) == 2 and clock.first_actual >= 0.58, "catch-up occurs only after sprint gate")
    first = clock.first_actual
    clock.tick(0.95)
    check(clock.first_actual == first and clock.last_actual == 0.95, "first actual shot timestamp is retained independently of last")

    clock = FireClock()
    clock.press(0.0)
    clock.release()
    clock.press(0.13)
    check(len(clock.shots) == 2 and abs(clock.next_shot - 0.25) < 1e-12, "repress after 130 ms starts a fresh cadence without idle debt")
    clock.tick(0.249)
    check(len(clock.shots) == 2, "repress cannot cause a second shot inside 120 ms")
    clock.release()
    clock.press(100.0)
    check(len(clock.shots) == 3 and clock.first_actual == 100.0, "long-idle press emits one shot and resets first diagnostic")
    clock = FireClock()
    clock.press(0.0)
    clock.release()
    clock.press(0.04)
    check(len(clock.shots) == 1, "early repress retains previous round cooldown")
    clock.tick(0.12)
    check(len(clock.shots) == 2 and clock.first_actual == 0.12, "early repress fires at original cooldown boundary")

    clock = FireClock()
    clock.start_action("equip", 2.0)
    clock.press(0.0)
    clock.tick(1.98)
    check(not clock.shots, "equip interval accrues no shots")
    clock.tick(2.37)
    check(len(clock.shots) == 4 and all(due >= 2.0 for due, _ in clock.shots), "completion inside frame only catches its eligible tail")
    clock = FireClock()
    clock.start_action("equip", 2.0)
    clock.press(2.37)
    clock.tick(2.37)
    check(len(clock.shots) == 1 and clock.shots[0][0] == 2.37, "late new press is not rewound to earlier completion")

    clock = FireClock(ammo=1, reserve=2)
    clock.press(0.0)
    clock.tick(0.18)
    check(clock.action == "reload" and clock.held and len(clock.shots) == 1, "held last round enters empty reload")
    start = clock.action_start
    check(not clock.start_action("reload", 3.466667) and clock.action_start == start, "repeated reload cannot restart its clock")
    clock.tick(3.64)
    clock.tick(3.90)
    check(len(clock.shots) == 3 and clock.ammo == 0 and clock.reserve == 0 and clock.reload_settlements == 1, "held empty reload settles once and fires exactly two replenished rounds")
    check(not clock.held, "dry fire ends held loop without phantom shots")

    clock = FireClock(ammo=0, reserve=3, held=True, sprint=True)
    clock.start_action("reload", 2.0)
    clock.tick(1.99)
    clock.tick(2.10)
    check(not clock.shots and not clock.sprint and abs(clock.sprint_unlock - 2.18) < 1e-12, "reload completion exits sprint once and starts exact completion gate")
    clock.tick(2.37)
    check(len(clock.shots) == 2 and all(due >= 2.18 for due, _ in clock.shots), "reload plus sprint only catches post-unlock time")
    clock = FireClock(ammo=0, reserve=3, sprint=True)
    clock.start_action("reload", 2.0)
    clock.press(2.37)
    clock.tick(2.37)
    check(not clock.shots and abs(clock.sprint_unlock - 2.55) < 1e-12, "new press sprint gate wins over earlier reload completion")
    clock = FireClock(ammo=0, reserve=3, held=True)
    clock.start_action("reload", 2.0)
    clock.tick(1.99)
    clock.sprint = True
    clock.sprint_started = 2.37
    clock.tick(2.37)
    check(not clock.shots and abs(clock.sprint_unlock - 2.55) < 1e-12, "new same-frame sprint cannot exit retroactively at an older reload completion")

    clock = FireClock(ammo=0, reserve=3, held=True, sliding=True)
    clock.start_action("reload", 2.0)
    clock.tick(2.37)
    check(not clock.shots and clock.action == "idle", "reload completion does not bypass slide")
    clock.now = 2.55
    clock.stop_slide()
    clock.service()
    check(len(clock.shots) == 1 and clock.shots[0][0] == 2.55, "slide exit drops blocked time")

    clock = FireClock()
    clock.press(0.0)
    check(clock.tick(10.0) == MAX_CATCH_UP, "custom enormous hitch stays bounded")
    check(clock.next_shot > 10.0 and abs(clock.next_shot / INTERVAL - round(clock.next_shot / INTERVAL)) < 1e-10, "over-budget hitch drops debt and retains cadence phase")
    check(clock.tick(10.0) == 0, "same-time repeat cannot consume another catch-up batch")
    print("PASS sprint lock; first/last timestamps; rapid repress; equip/reload/slide blocker boundaries; automatic empty reload; over-budget hitch")
    print(f"FIRE_CLOCK_COMPLETE checks={checks} failures=0")


if __name__ == "__main__":
    main()
