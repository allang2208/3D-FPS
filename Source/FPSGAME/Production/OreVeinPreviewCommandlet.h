#pragma once
#include "Commandlets/Commandlet.h"
#include "OreVeinPreviewCommandlet.generated.h"

/** Renders the four ore vein rock variants next to the plain rock into PNGs so
 *  the vein material can be judged without a live editor session. Uses the same
 *  manual frame-pump loop as UColdSteelWeaponIcons::ExportCatalogIcon, which is
 *  the only render path proven to work under a commandlet here. */
UCLASS()
class UOreVeinPreviewCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
