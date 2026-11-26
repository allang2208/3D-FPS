#pragma once

class AActor;

namespace CombatControl
{
/** Hard control only. Slow, chill stacks, damage and other debuffs keep their own rules. */
bool IsImmune(const AActor* Target);
}
