#pragma once

#include "CoreMinimal.h"
#include "VillageArtisanMerchant.h"
#include "VillageCarpenterResident.generated.h"

class USkeletalMeshComponent;
struct FStreamableHandle;

UCLASS()
class FPSGAME_API AVillageCarpenterResident : public AVillageArtisanMerchant
{
    GENERATED_BODY()

public:
    AVillageCarpenterResident();
    static TArray<FSoftObjectPath> AppearancePaths();
    static bool IsAppearanceCompilationPending();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Head;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Workwear;
    TSharedPtr<FStreamableHandle> AppearanceLoad;
    FTimerHandle AppearanceRetryTimer;

    void AssembleAppearance();
};
