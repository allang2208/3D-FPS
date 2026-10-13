#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelPreviewScene.h"
#include "Containers/Ticker.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelPickupStudio.generated.h"

/** Reuses two isolated visual rigs; releasing an item never destroys a preview world. */
UCLASS()
class UColdSteelPickupStudio : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    class AFPSGAMECharacter* Acquire(const FString& Definition,bool& Created);
    FString Key(const FColdSteelItem& Item) const;
    void Warm(const FColdSteelItem& Item, const FBox* PreparedBounds = nullptr);
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    void ReleaseIdleRigs(bool bEnteringDungeon = false);
    virtual void Deinitialize() override;
    TMap<FString,FBox> Bounds;
private:
    TUniquePtr<FColdSteelPreviewScene> Studio;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class AFPSGAMECharacter>> Rigs;
    // The source rig is used synchronously; pickups copy its pose/materials.
    // Retain the two most recently used families, not one character per gun forever.
    TArray<FString> RigUseOrder;
    TMap<FString,double> LastUseSeconds;
    FTSTicker::FDelegateHandle IdleTicker;
};
