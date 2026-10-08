#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "HumanoidRagdollBudget.generated.h"
class USkinnedMeshComponent;

/** Only active simulations occupy slots; frozen poses keep no solver budget. */
UCLASS()
class FPSGAME_API UHumanoidRagdollBudget : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool Acquire(UObject* Candidate, int32 BodyCount, bool bCorpse);
    void Release(UObject* Candidate);
    // Meshes with frame tick disabled share one LOD timer. Skeletal corpses
    // reevaluate their snapshot; poseable soft corpses retain the full bone pose.
    void RegisterFrozenMesh(USkinnedMeshComponent* Mesh);
    virtual void Deinitialize() override;
private:
    TArray<TWeakObjectPtr<UObject>> Active;
    void UpdateFrozenLODs();
    TArray<TWeakObjectPtr<USkinnedMeshComponent>> FrozenMeshes;
    FTimerHandle FrozenLODTimer;
};
