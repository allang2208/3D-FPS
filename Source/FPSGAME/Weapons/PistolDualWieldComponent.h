#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "GunsmithSystem.h"
#include "PistolDualWieldComponent.generated.h"

class AFPSGAMECharacter;
class UColdSteelStatusModel;
class UFPSGunplayAnimInstance;
class UFPSWeaponFXComponent;
class UFPSBallisticsComponent;
class USkeletalMeshComponent;
class UAnimSequence;
class USoundBase;
class UAudioComponent;

USTRUCT()
struct FDualPistolHand
{
    GENERATED_BODY()
    UPROPERTY(Transient) FColdSteelItem Item;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Mesh;
    UPROPERTY(Transient) TObjectPtr<UFPSWeaponFXComponent> FX;
    UPROPERTY(Transient) TObjectPtr<UFPSBallisticsComponent> Ballistics;
    UPROPERTY(Transient) TObjectPtr<class UTacticalDeviceComponent> Tactical;
    UPROPERTY(Transient) TObjectPtr<UFPSGunplayAnimInstance> Anim;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UAnimSequence>> Clips;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<USoundBase>> Sounds;
    UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Voices;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Action;
    FGunsmithStats Stats;
    FString Recipe;
    int32 Rounds=0, Cases=0, ReloadStart=0, ReloadCount=0, Seated=0, Pattern=0;
    bool Revolver=false, Speedloader=false, ReloadSpeedloader=false, Suppressed=false;
    bool Held=false, Pending=false, Reloading=false, ReloadQueued=false, CasesCleared=false;
    float ActionTime=0, ActionRate=1, SourceLength=0, Sprint=0, SprintBlend=0, Bloom=0;
    double NextShot=0, LastShot=-10;
    double ActionStarted=0;
    TSet<FString> PlayedCues;
};

/** Two inventory instances, two trigger edges and reload clocks; one player camera. */
UCLASS()
class FPSGAME_API UPistolDualWieldComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPistolDualWieldComponent();
    bool IsActive() const { return bActive; }
    bool IsReloading() const { return bActive && (Hands[0].Reloading || Hands[1].Reloading); }
    bool LeftBusy() const;
    const FDualPistolHand& Hand(int32 Index) const { return Hands[Index]; }
    void RefreshEquipment(UColdSteelStatusModel* Model);
    void Advance(float Delta);
    void Trigger(int32 Index,bool Pressed);
    void Reload();
    void CancelInputs();
    void SyncInventory(TArray<FColdSteelItem>& Items) const;
    int32 Reserve(int32 Index) const;
private:
    UPROPERTY(Transient) TArray<FDualPistolHand> Hands;
    UPROPERTY(Transient) TObjectPtr<AFPSGAMECharacter> Player;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Profile;
    UPROPERTY(Transient) TArray<TObjectPtr<class USceneComponent>> LeftAttachments;
    bool bActive=false;
    float Clock=0, Phase=0, SprintPhase=0;
    float AimInverseDistance=1.f/1200.f;
    FVector AimTargetWorld=FVector::ZeroVector;
    void UpdateAimTarget(float Delta);
    FVector SightDirection() const;
    void LoadHand(int32 Index,const FColdSteelItem& Item);
    void CopyLeftAttachments(const FColdSteelItem& Item,const FGunsmithParts& Parts);
    void StartAction(int32 Index,const FString& Name,float Rate=1.f);
    void BeginReload(int32 Index);
    void AdvanceReload(int32 Index,float PreviousSource);
    void TryFire(int32 Index);
    void StopAction(int32 Index);
    void Cue(int32 Index,const FString& Name,float At,float Previous,float Now);
    void Pose(int32 Index,float Delta);
    bool InputAvailable() const;
};
