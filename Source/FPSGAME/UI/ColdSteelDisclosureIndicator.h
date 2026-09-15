#pragma once

#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "ColdSteelDisclosureIndicator.generated.h"

/** Decorative triangle; the enclosing expandable header retains all input. */
UCLASS()
class UColdSteelDisclosureIndicator : public UWidget
{
    GENERATED_BODY()
public:
    void Configure(float PixelScale,bool Expanded,class UExpandableArea* Header=nullptr,bool Intro=false);
    void SetExpanded(bool Expanded);
    virtual void ReleaseSlateResources(bool ReleaseChildren)override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget()override;
private:
    TSharedPtr<class SColdSteelDisclosureIndicator> Indicator;
    float Scale=1.f;
    TWeakObjectPtr<class UExpandableArea> Header;
    bool bExpanded=false,bIntro=false;
};
