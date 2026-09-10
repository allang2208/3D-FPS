#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelPickup.generated.h"
UCLASS()
class FPSGAME_API AColdSteelPickup : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelPickup();
    FString ItemId;
    void InitializeItem(const FColdSteelItem& Item);
private:
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Mesh;
    UPROPERTY() TObjectPtr<class UTextRenderComponent> Label;
};
