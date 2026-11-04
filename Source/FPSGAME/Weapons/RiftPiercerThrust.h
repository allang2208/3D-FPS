#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "RiftPiercerThrust.generated.h"

class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;

USTRUCT()
struct FRiftPiercerThrustState
{
    GENERATED_BODY()
    UPROPERTY() FTransform HiltFrame;
    UPROPERTY() FSoftObjectPath Blade;
    UPROPERTY() FSoftObjectPath HitSound;
    UPROPERTY() FLinearColor Tint=FLinearColor(.12f,.72f,1.f);
    UPROPERTY() float Reach=0.f;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() bool bOwnerPredicted=false;
    UPROPERTY() TArray<FVector_NetQuantize> ImpactPoints;
};

/** A full-length thrust appears at once, strikes once, then leaves a stationary sword imprint. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API ARiftPiercerThrust : public AActor
{
    GENERATED_BODY()
public:
    ARiftPiercerThrust();
    void Activate(const FRiftPiercerThrustState& State,float ThirdDamage,const FColdSteelSkillShot& Snapshot,bool CosmeticOnly=false);
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Motes;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BladeMID;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> MoteMID;
    UPROPERTY(ReplicatedUsing=OnRep_State) FRiftPiercerThrustState NetState;
    UFUNCTION() void OnRep_State();
    TSharedPtr<struct FStreamableHandle> VisualLoad;
    struct FMote { float Delay=0,Station=0,Spread=0,Spin=0,Depth=0; int32 Side=1; };
    TArray<FMote> Seeds;
    FVector BladeScale=FVector::OneVector;
    float Age=0,Length=0,HitGlow=0;
    bool bInitialized=false,bImpactCuesPlayed=false;
    double Clock() const;
    void LoadVisuals();
    void SetupVisuals();
    void ResolveThrust(float Damage,const FColdSteelSkillShot& Shot,bool ApplyDamage);
    void UpdateVisuals();
};
