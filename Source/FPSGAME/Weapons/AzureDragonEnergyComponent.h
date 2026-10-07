#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AzureDragonEnergyComponent.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class ULocalPlayer;
class SAzureDragonEnergyHud;
struct FStreamableHandle;

/** Owner-only screen-space energy vessel (HUD V10). Gameplay owns charge; this component presents it. */
UCLASS()
class FPSGAME_API UAzureDragonEnergyComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAzureDragonEnergyComponent();
    void Configure(bool Enabled);
    void SetEnergy(float NormalizedEnergy,bool Summoned=false,bool ContactPulse=true);
    void ClearEnergy();
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RequestAssets();
    void CreateDisplay();
    void HideDisplay();
    void RemoveDisplay();
    bool bEnabled=false,bRequested=false,bHaveYaw=false;
    float TargetEnergy=0.f,DisplayEnergy=0.f,Age=0.f,EntryAge=0.f;
    float HitAge=10.f,FlareAge=10.f,LastYaw=0.f,Sway=0.f;
    TSharedPtr<FStreamableHandle> AssetLoad;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> HudMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HudMID;
    TSharedPtr<SAzureDragonEnergyHud> HudWidget;
    TWeakObjectPtr<ULocalPlayer> HudPlayer;
};
