#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "PreviewScene.h"
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
    void Warm(const FColdSteelItem& Item);
    virtual void Deinitialize() override;
    TMap<FString,FBox> Bounds;
private:
    TUniquePtr<FPreviewScene> Studio;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class AFPSGAMECharacter>> Rigs;
};
