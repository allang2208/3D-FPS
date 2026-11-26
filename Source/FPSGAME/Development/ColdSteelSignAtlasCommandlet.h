#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelSignAtlasCommandlet.generated.h"

/** Re-typeset existing sign textures into staging while retaining their UE asset settings. */
UCLASS()
class UColdSteelSignAtlasCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
