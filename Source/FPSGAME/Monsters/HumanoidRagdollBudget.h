#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "HumanoidRagdollBudget.generated.h"
class UHumanoidKnockdownComponent;

/** Only active simulations occupy slots; frozen poses keep no solver budget. */
UCLASS()
class FPSGAME_API UHumanoidRagdollBudget : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool Acquire(UHumanoidKnockdownComponent* Candidate, int32 BodyCount, bool bCorpse);
    void Release(UHumanoidKnockdownComponent* Candidate);
private:
    TArray<TWeakObjectPtr<UHumanoidKnockdownComponent>> Active;
};
