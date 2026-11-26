#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "MonsterPresentationBudget.generated.h"
class UMonsterCombatComponent;
class USkeletalMeshComponent;

/** Distance tiers for visual-only skeletons; authoritative bone queries retain their policy. */
UCLASS()
class FPSGAME_API UMonsterPresentationBudget : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void Register(UMonsterCombatComponent* Combat);
    void Unregister(UMonsterCombatComponent* Combat);
    void Promote(UMonsterCombatComponent* Combat);
    virtual void Deinitialize() override;
private:
    struct FEntry
    {
        TWeakObjectPtr<UMonsterCombatComponent> Combat;
        TWeakObjectPtr<USkeletalMeshComponent> Mesh;
        float OriginalInterval=0,AppliedInterval=0;
        uint8 Tier=0;
    };
    TArray<FEntry> Entries;
    FTimerHandle Timer;
    int32 Cursor=0;
    void Update();
    static void Restore(FEntry& Entry);
};
