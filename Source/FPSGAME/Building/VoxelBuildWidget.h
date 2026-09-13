#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "VoxelBuildWidget.generated.h"

class UBorder;
class UTextBlock;
class UCanvasPanelSlot;

UCLASS()
class FPSGAME_API UVoxelBuildWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowState(const FString& Material,const FString& Brush,const FString& Message,bool bValid,int32 Count,bool bSnapEnabled);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
private:
    UPROPERTY() TObjectPtr<UBorder> Surface;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> PanelSlot;
    UPROPERTY() TObjectPtr<UTextBlock> Title;
    UPROPERTY() TObjectPtr<UTextBlock> Selection;
    UPROPERTY() TObjectPtr<UTextBlock> Status;
    UPROPERTY() TObjectPtr<UTextBlock> Controls;
    FString LastState;
    FVector2D LastViewport=FVector2D::ZeroVector;
    float LastScale=0;
    void RefreshLayout();
};
