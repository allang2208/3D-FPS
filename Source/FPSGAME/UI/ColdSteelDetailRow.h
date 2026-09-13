#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelDetailRow.generated.h"

class UBorder;
class UTextBlock;
class UButton;
class UProgressBar;
class UHorizontalBox;

/** One full-width, focusable status row. Hover and keyboard focus share one detail path. */
UCLASS()
class FPSGAME_API UColdSteelDetailRow : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(const FString& Label, float Scale, bool bNumeric = true);
    void UpdateScale(float Scale);
    void SetValue(const FString& Value, bool bAvailable = true);
    FString GetValue() const;
    FSimpleDelegate ShowDetail;
    FSimpleDelegate HideDetail;
    FSimpleDelegate Allocate;
    void SetCanAllocate(bool bCanAllocate);
    UProgressBar* AddMeter(const FLinearColor& Color, float Scale);
protected:
    virtual void NativeOnMouseEnter(const FGeometry&, const FPointerEvent&) override;
    virtual void NativeOnMouseLeave(const FPointerEvent&) override;
    virtual FReply NativeOnFocusReceived(const FGeometry&, const FFocusEvent&) override;
    virtual void NativeOnFocusLost(const FFocusEvent&) override;
private:
    void RefreshHighlight();
    UPROPERTY(Transient) TObjectPtr<UBorder> Surface;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> NameText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ValueText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PlusText;
    UPROPERTY(Transient) TObjectPtr<UButton> PlusButton;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> PlusSize;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> MeterTrack;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> Meter;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> Line;
    UFUNCTION() void HandleAllocate();
    bool bPointerInside = false;
    bool bNumericValue = true;
    float VisualScale = 1.f;
};
