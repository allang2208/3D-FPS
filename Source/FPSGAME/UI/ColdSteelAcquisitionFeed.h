#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAcquisitionTimeline.h"
#include "ColdSteelAcquisitionFeed.generated.h"

class UColdSteelStatusModel;

/** Text-only recent gains above the soul HUD. Does not own input or inventory. */
UCLASS()
class FPSGAME_API UColdSteelAcquisitionFeed : public UUserWidget
{
    GENERATED_BODY()
public:
    static constexpr float PreferredHeight=164.f;
    void SetLayout(float PixelScale,float PixelWidth,float PixelHeight);
    void SetPresentationSuppressed(bool Suppressed);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float DeltaTime) override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool)const override;
private:
    using FLine=FColdSteelAcquisitionTimeline::FLine;
    void PrepareLine(FLine& Line);
    void UpdateVisibility();
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    FColdSteelAcquisitionTimeline Timeline;
    FSlateFontInfo TextFont,NumberFont;
    float Scale=1,Width=360,Height=PreferredHeight;
    int32 MaxLines=5;
    uint32 Epoch=0;
    bool bSuppressed=false;
};
