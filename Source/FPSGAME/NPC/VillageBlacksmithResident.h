#pragma once

#include "CoreMinimal.h"
#include "VillageArtisanMerchant.h"
#include "VillageBlacksmithResident.generated.h"

class USkeletalMeshComponent;

UCLASS()
class FPSGAME_API AVillageBlacksmithResident : public AVillageArtisanMerchant
{
    GENERATED_BODY()

public:
    AVillageBlacksmithResident();
    static TArray<FSoftObjectPath> AppearancePaths();
    static bool IsAppearanceCompilationPending();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Head;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Outfit;
    FTimerHandle AppearanceRetryTimer;
    void AssembleAppearance();
};
