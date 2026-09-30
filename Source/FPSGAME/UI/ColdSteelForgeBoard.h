#pragma once
#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "ColdSteelForgeBoard.generated.h"
class UColdSteelForgingSystem;
class UTexture2D;
class SColdSteelForgeBoard;

UCLASS()
class FPSGAME_API UColdSteelForgeBoard : public UWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelForgingSystem* InSystem,UTexture2D* InTexture);
    void RefreshPaint();
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgingSystem> System;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> Texture;
    TSharedPtr<SColdSteelForgeBoard> Board;
};
