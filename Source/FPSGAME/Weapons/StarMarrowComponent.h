#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Skills/FlameArmorAttachments.h"
#include "StarMarrowComponent.generated.h"
class UColdSteelStatusModel;
class UNiagaraSystem;
class UNiagaraComponent;
class UMaterialInstanceDynamic;
class UTexture2D;
struct FStreamableHandle;

/** Equipped-only G ability; the server owns payment and duration. */
UCLASS()
class FPSGAME_API UStarMarrowComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStarMarrowComponent();
    static constexpr float Duration=30.f;
    static constexpr float ManaFraction=.2f;
    static constexpr double DamageMultiplier=1.3;
    void Configure(const UColdSteelStatusModel* Model);
    static bool Equipped(const UColdSteelStatusModel* Model);
    bool IsEquipped() const;
    bool CanActivate() const;
    bool IsActivationPending() const {return PendingSequence!=0||Clock()<AcceptedRetryAfter;}
    UTexture2D* ShortcutIcon() const;
    void Trigger();
    bool ActivateCharge(UColdSteelStatusModel* Model);
    void NetCastResult(uint32 Sequence,uint8 Code);
    float Remaining() const;
    static bool ChargesDamage(const AActor* Source);
    bool HUDVisible() const;
    float HUDAlpha() const;
    UMaterialInstanceDynamic* HUDMaterial() const {return ChargeHUDMaterial;}
    FString HUDLabel() const;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class URuneSwordAuditCommandlet;
    UPROPERTY(ReplicatedUsing=OnRep_State) double ChargedUntil=0.;
    UPROPERTY(ReplicatedUsing=OnRep_State) FString ChargedInstance;
    UFUNCTION() void OnRep_State();
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquippedInstance,EquippedData;
    uint32 PendingSequence=0;
    double AcceptedRetryAfter=0.;
    double PresentedChargeUntil=0.;
    bool bPredictedChargeMotion=false;
    double FeedbackUntil=0.;
    FString Feedback;
    double HUDVisibleUntil=0.;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChargeHUDMaterial;
    TSharedPtr<FStreamableHandle> HUDLoad;
    void LoadHUD();
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> FlameSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> FlameFX;
    TSharedPtr<FStreamableHandle> FlameLoad;
    struct FBladeFireHistory : FFlameArmorHistory
    {
        FVector BaseFlow = FVector::ZeroVector;
        FVector TipFlow = FVector::ZeroVector;
    };
    FBladeFireHistory FlameHistory[FlameArmorAttachments::MaxLayers];
    double Clock() const;
    void Clear();
    void PresentChargeMotion();
    void LoadFlames();
    void UpdateFlames(float Delta);
    void StopFlames();
};
