#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include <initializer_list>
#include "MonsterIdleBreathingMeshComponent.generated.h"

class ACharacter;
class UMonsterCombatComponent;

struct FMonsterBreathingBone
{
    TArray<FName> Candidates;
    TArray<int32> Descendants;
    int32 Index = INDEX_NONE;
    float PitchDegrees = 0.f;
    float Expansion = 0.f;
    float Delay = 0.f;
    float SwayDegrees = 0.f;
    bool bKeepChildren = true;
};

/** Idle-only pose additions. Keeps the monster's original animation and post-process graph. */
UCLASS()
class FPSGAME_API UMonsterIdleBreathingMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    virtual void FinalizeBoneTransform() override;
private:
    void ConfigureBreathing(ACharacter* Character);
    void CacheBones();
    void AddBone(std::initializer_list<const TCHAR*> Names, float Pitch, float Expansion,
        float Delay = 0.f, float Sway = .05f, bool bKeepChildren = true);
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TWeakObjectPtr<UMonsterCombatComponent> Combat;
    TArray<FMonsterBreathingBone> BreathingBones;
    uint8 Body = 0;
    bool bConfigured = false;
    float Period = 4.f, Seed = 0.f, IdleWeight = 0.f;
    double PreviousTime = -1.0;
};
