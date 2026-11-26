#pragma once
class APawn;
namespace BowSkillLifecycle
{
    // Finish confirmed rewards and unlaunched reservations before profile persistence.
    void FinishForRemoval(APawn* Pawn);
}
