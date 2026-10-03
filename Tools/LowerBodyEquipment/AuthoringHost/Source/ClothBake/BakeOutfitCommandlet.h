#pragma once
#include "Commandlets/Commandlet.h"
#include "BakeOutfitCommandlet.generated.h"
UCLASS()
class UBakeOutfitCommandlet : public UCommandlet {
 GENERATED_BODY()
public:
 UBakeOutfitCommandlet();
 virtual int32 Main(const FString& Params) override;
};
