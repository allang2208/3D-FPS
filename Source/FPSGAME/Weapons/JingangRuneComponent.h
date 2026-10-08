#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GunsmithSystem.h"
#include "JingangRuneComponent.generated.h"

class UColdSteelStatusModel;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class ULocalPlayer;
class SJingangSutraHud;
struct FStreamableHandle;

enum class EJingangState : uint8 { None, High, Middle, Low };

/** Equipped-only rune. The health component remains the source of truth; no saved stat mutation. */
UCLASS()
class FPSGAME_API UJingangRuneComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UJingangRuneComponent();
    void Configure(const UColdSteelStatusModel* InProfile);
    EJingangState State() const;
    float DefenseMultiplier() const;
    float DamageMultiplier() const;
    float AttackSpeedMultiplier() const;
    float CooldownMultiplier() const;
    float LeechRemaining() const;
    float LeechDuration() const {return Modifiers.JingangLeechSeconds;}
    void ConfirmAttack(AActor* Target,float AppliedDamage);
    void ObserveHealth();
    static const UJingangRuneComponent* From(const UColdSteelStatusModel* Model);
    static float OutgoingMultiplier(const AActor* Source);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class URuneSwordAuditCommandlet;
    bool Equipped() const;
    double Clock() const;
    void Clear();
    void RequestAssets();
    void CreateDisplay();
    void RemoveDisplay();
    UFUNCTION() void OnRep_Leech();
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquippedInstance,EquippedData;
    FMeleeModifiers Modifiers;
    EJingangState LastState=EJingangState::None;
    int32 DisplayState=-1,PreviousDisplayState=-1;
    float Age=0.f,TransitionAge=0.f,EntryAge=0.f;
    bool bRequested=false,bHadLeech=false;
    TSharedPtr<FStreamableHandle> AssetLoad;
    TSharedPtr<SJingangSutraHud> HudWidget;
    TWeakObjectPtr<ULocalPlayer> HudPlayer;
    UPROPERTY(ReplicatedUsing=OnRep_Leech) double LeechEndsAt=0.;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> HudMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HudMID;
};
