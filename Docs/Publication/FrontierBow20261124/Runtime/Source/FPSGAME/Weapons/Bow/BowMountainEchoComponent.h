#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BowMountainEchoComponent.generated.h"

class ABowArrow;
class UColdSteelStatusModel;
class UMaterialInterface;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

/** Equipped-instance state; authority owns stacks, clients only display them. */
UCLASS()
class FPSGAME_API UBowMountainEchoComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UBowMountainEchoComponent();
    void RefreshEquipment(UColdSteelStatusModel* Model);
    void CommitArrow(ABowArrow* Arrow,const FString& Instance,float Charge,const FVector& Eye);
    void ConfirmHit(uint32 ReleasedEpoch);
    bool CanEcho(uint32 ReleasedEpoch) const;
    int32 ChargesFor(const FString& Instance) const;
    bool IsEquippedFor(const FString& Instance) const{return !Instance.IsEmpty()&&Instance==EquippedInstance;}
    float GainAge() const;
    float ReadyAge() const;
    UMaterialInterface* EchoMaterial() const{return ArrowMaterial;}
    UMaterialInstanceDynamic* ResonanceHUDMaterial();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class UBowSkillTrainingAuditCommandlet;
    friend class AShotgunWireAuditGameMode;
    UPROPERTY(ReplicatedUsing=OnRep_Resonance) FString EquippedInstance;
    UPROPERTY(ReplicatedUsing=OnRep_Resonance) int32 Stacks=0;
    UFUNCTION() void OnRep_Resonance();
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ArrowMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HUDMaterial;
    TSharedPtr<FStreamableHandle> MaterialLoad;
    TSharedPtr<FStreamableHandle> HUDLoad;
    uint32 Epoch=1;
    UPROPERTY(ReplicatedUsing=OnRep_Resonance) double ExpiresAt=0;
    FString PresentedInstance;
    int32 PresentedStacks=0;
    double PresentedExpiresAt=0.;
    double LastGainAt=-1000.,LastReadyAt=-1000.;
    bool bWasDead=false;
    void ClearStacks();
    double ServerTime() const;
};
