#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include <initializer_list>
#include "MonsterIdleBreathingMeshComponent.generated.h"

class ACharacter;
class UMonsterCombatComponent;
class UPhysicsAsset;

struct FMonsterGunHitBone
{
    int32 Index = INDEX_NONE;
    TArray<int32> Descendants;
    float Degrees = 3.f;
    bool bPinChildren = false;
};

struct FMonsterGunHitPulse
{
    int32 Track = INDEX_NONE;
    FVector AxisWorld = FVector::RightVector;
    float Radians = 0.f;
    double StartTime = 0.0;
    float Duration = .26f;
};

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

/** Procedural breathing and gunshot pose additions; retains the original animation graph. */
UCLASS()
class FPSGAME_API UMonsterIdleBreathingMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    virtual void FinalizeBoneTransform() override;
    /** Presentation only: never enters a reaction state or changes an animation clock. */
    void AddGunHitFeedback(const FHitResult& Hit, const FVector& ShotDirection, float Damage);
private:
    void CacheGunHitBones();
    bool ApplyGunHitFeedback();
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
    TWeakObjectPtr<USkeletalMesh> GunHitMesh;
    TWeakObjectPtr<UPhysicsAsset> GunHitPhysicsAsset;
    TArray<FMonsterGunHitBone> GunHitBones;
    TArray<int32> GunHitBoneLookup;
    TArray<FMonsterGunHitPulse, TInlineAllocator<4>> GunHitPulses;
    TArray<int32> PreviousGunHitTracks;
};
