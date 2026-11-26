#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "WarhammerShockwave.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class USoundBase;
class UColdSteelStatusModel;

/** One authoritative, expanding ground pulse; clients render the same radius clock. */
UCLASS()
class FPSGAME_API AWarhammerShockwave : public AActor
{
    GENERATED_BODY()
public:
    AWarhammerShockwave();
    void Setup(const FColdSteelSkillShot& InShot,float Radius,float StunSeconds,float ThunderMagic=-1.f,bool ThunderCall=false);
    // A contact owner can emit immediately; the normal tick remains the remote fallback.
    void PresentImpact();
    void SetLeapTraining(UColdSteelStatusModel* Profile);
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Ring;
private:
    friend class UWarhammerModificationAuditCommandlet;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material;
    UPROPERTY(Replicated) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Replicated) float MaxRadius=300.f;
    UPROPERTY(Replicated) double StartedAt=-1.;
    UPROPERTY(Replicated) bool bThunder=false;
    UPROPERTY(Replicated) bool bThunderCall=false;
    UPROPERTY(Replicated) float ThunderHeight=2400.f;
    UPROPERTY(Replicated) int32 ThunderSeed=0;
    FColdSteelSkillShot Shot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    bool bConfigured=false,bSoundPlayed=false;
    bool bThunderVisualPlayed=false;
    float PreviousRadius=0.f;
    int32 MasteryHits=0;
    TWeakObjectPtr<UColdSteelStatusModel> LeapRewardModel;
    int32 LeapKills=0;
    float HeavyStunSeconds=0.f;
    // Keep native lightning separate from physical and non-electric rune damage.
    float NativeThunderMagic=0.f;
    FWeaponDamageParts DamageWithElectricMultiplier(float Multiplier) const;
    void ApplyWave(float Radius);
    double Clock() const;
};

/** Raised wavefront shared by leap landings and charged ground slams. */
UCLASS()
class FPSGAME_API ALeapStrikeShockwave : public AWarhammerShockwave
{
    GENERATED_BODY()
public:
    ALeapStrikeShockwave();
};
