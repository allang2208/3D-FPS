#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "HumanoidRagdollBudget.generated.h"
class USkeletalMeshComponent;

/** Only active simulations occupy slots; frozen poses keep no solver budget. */
UCLASS()
class FPSGAME_API UHumanoidRagdollBudget : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool Acquire(UObject* Candidate, int32 BodyCount, bool bCorpse);
    void Release(UObject* Candidate);
    // Frozen meshes have no frame tick. Only a renderer-requested LOD change
    // evaluates their immutable snapshot again, through one shared timer.
    void RegisterFrozenMesh(USkeletalMeshComponent* Mesh);
    virtual void Deinitialize() override;
private:
    TArray<TWeakObjectPtr<UObject>> Active;
    void UpdateFrozenLODs();
    TArray<TWeakObjectPtr<USkeletalMeshComponent>> FrozenMeshes;
    FTimerHandle FrozenLODTimer;
};
