#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Fonts/SlateFontInfo.h"
#include "ColdSteelDamageNumbers.generated.h"

class AActor;
class UColdSteelDamageNumberSubsystem;

/** Pooled screen-space damage numbers anchored to accepted hit points. */
UCLASS()
class FPSGAME_API UColdSteelDamageNumbers : public UUserWidget
{
    GENERATED_BODY()
public:
    /** Panels/menus clear pending numbers instead of replaying them on close. */
    void SetPresentationSuppressed(bool Suppressed);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry,float DeltaTime) override;
    virtual int32 NativePaint(const FPaintArgs& Args,const FGeometry& AllottedGeometry,const FSlateRect& MyCullingRect,
        FSlateWindowElementList& OutDrawElements,int32 LayerId,const FWidgetStyle& InWidgetStyle,bool bParentEnabled) const override;
private:
    struct FEntry
    {
        TWeakObjectPtr<AActor> Target;
        FVector WorldPoint=FVector::ZeroVector;
        FString PhysicalText,MagicText,CountText;
        float Physical=0.f,Magic=0.f,Age=0.f,Life=1.15f;
        float PhysicalWidth=0.f,MagicWidth=0.f,CountWidth=0.f;
        int32 Count=1;
        bool bCritical=false,bKilled=false,bBig=false,bTrackTarget=false;
    };
    void RefreshMetrics();
    void MeasureEntry(FEntry& Entry) const;
    void UpdateVisibility();
    UPROPERTY(Transient) TObjectPtr<UColdSteelDamageNumberSubsystem> Numbers;
    TArray<FEntry> Entries;
    FSlateFontInfo AmountFont,LabelFont,CountFont;
    float Scale=1.f,AmountHeight=0.f,LabelHeight=0.f,CritWidth=0.f,KillWidth=0.f;
    bool bSuppressed=false;
};
