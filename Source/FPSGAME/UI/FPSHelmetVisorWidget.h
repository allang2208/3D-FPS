#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "FPSHelmetVisorWidget.generated.h"

/** Owner-local optical obstruction, below HUD panels and above scope imagery. */
UCLASS()
class FPSGAME_API UFPSHelmetVisorWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(class UFPSPlayerBodyComponent* Body, class UTexture2D* Texture);
protected:
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,
        FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
private:
    TWeakObjectPtr<class UFPSPlayerBodyComponent> Source;
    UPROPERTY(Transient) FSlateBrush Visor;
};
