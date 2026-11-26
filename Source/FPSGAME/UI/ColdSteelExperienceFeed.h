#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Fonts/SlateFontInfo.h"
#include "ColdSteelExperienceFeed.generated.h"

class UColdSteelStatusModel;

/** Transient character experience feedback in a gold square below the crosshair. */
UCLASS()
class FPSGAME_API UColdSteelExperienceFeed : public UUserWidget
{
    GENERATED_BODY()
public:
    /** Panels own the screen; freeze the queue and hide the text while they are out. */
    void SetPresentationSuppressed(bool Suppressed);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry,float DeltaTime) override;
    virtual int32 NativePaint(const FPaintArgs& Args,const FGeometry& AllottedGeometry,const FSlateRect& MyCullingRect,
        FSlateWindowElementList& OutDrawElements,int32 LayerId,const FWidgetStyle& InWidgetStyle,bool bParentEnabled) const override;
private:
    struct FLine
    {
        int64 Amount=0;
        FString Text;
        float Width=0.f,Age=0.f,Y=0.f;
    };
    void RefreshMetrics();
    void MeasureLine(FLine& Line) const;
    void UpdateVisibility();
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    TArray<FLine> Lines;
    FSlateFontInfo AmountFont,UnitFont;
    FString UnitText;
    float UnitWidth=0.f,UnitHeight=0.f,AmountHeight=0.f,Scale=1.f,AdmissionAge=0.f;
    bool bSuppressed=false;
};
