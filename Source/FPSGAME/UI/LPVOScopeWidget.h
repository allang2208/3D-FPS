#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LPVOScopeWidget.generated.h"

// Owner-only optical layer: housing/engraving over the magnified main camera.
// The controller independently hides/restores gameplay HUD during scoped ADS.
UCLASS()
class FPSGAME_API ULPVOScopeWidget : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual int32 NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
        const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,
        const FWidgetStyle& Style,bool Enabled) const override;
};
