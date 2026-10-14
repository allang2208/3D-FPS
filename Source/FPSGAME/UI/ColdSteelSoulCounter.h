#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelSoulCounter.generated.h"

class UCanvasPanel;
class UTextBlock;
class UBorder;
class UImage;

/** A reusable wallet display; never mutates the profile or rebuilds on a currency change. */
UCLASS()
class FPSGAME_API UColdSteelSoulCounter : public UUserWidget
{
    GENERATED_BODY()
public:
    static constexpr float PixelHeight=80.f;
    void SetBalance(int64 Value,bool Animate=true);
    void SetDisplayScale(float Value);

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry&,float DeltaTime) override;

private:
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Root;
    UPROPERTY(Transient) TObjectPtr<UBorder> Background;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Caption;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Number;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> DeltaLabels;
    struct FDelta { int64 Amount=0;float Age=0; };
    TArray<FDelta> Deltas;
    FSlateBrush Surface;
    int64 Target=0,LastDrawn=-1;
    double Display=0,From=0;
    float Elapsed=.55f,Scale=1.f;
    bool Initialized=false;
    void RefreshNumber();
    void RefreshDeltas();
    UPROPERTY(Transient) TObjectPtr<UImage> SoulIcon;
    void LoadSoulIcon();
};
