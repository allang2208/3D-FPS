#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelWarehouseSortOption.generated.h"

// SObjectWidget keeps the generated option and its text alive while Slate owns it.
UCLASS()
class UColdSteelWarehouseSortOption : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetCaption(const FString& Caption);
};
