#pragma once
#include "Commandlets/Commandlet.h"
#include "ExportProductionIconsCommandlet.generated.h"

/** Export existing donor art only; never renders or saves donor packages. */
UCLASS()
class UExportProductionIconsCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
