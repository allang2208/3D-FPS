#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelQuickBarTypes.h"
#include "ColdSteelQuickSlot.generated.h"

UCLASS()
class UColdSteelQuickSlot : public UUserWidget
{
    GENERATED_BODY()
public:
    /** FixedSkill 非空时为只读专属槽（如快速进战的 F 键）：显示固定技能，不参与混放拖放。 */
    void Configure(class UColdSteelHUDWidget* Owner,int32 Slot,FName InFixedSkill=NAME_None);
    void Refresh();
protected:
    virtual void NativeTick(const FGeometry&,float DeltaTime) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&) override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
private:
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    int32 Index=INDEX_NONE;
    FName FixedSkill=NAME_None;
    FString FixedKeyLabel;
    bool bLoaded=false;
    FColdSteelQuickBinding Displayed;
    float BlinkElapsed=0.f;
    float FlashElapsed=.6f;
    float CooldownFraction=0.f;
    float DisplayedCooldownFraction=0.f;
    float CooldownTransitionFrom=0.f;
    float CooldownTransitionElapsed=.05f;
    TSharedPtr<class SColdSteelCooldownMask> CooldownMask;
    UPROPERTY(Transient) TObjectPtr<class UImage> Icon;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> IconFrame;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> FallbackIcon;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> State;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> Count;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> Key;
    UPROPERTY(Transient) TObjectPtr<class UImage> ReadyFlash;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> Texture;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTexture2D>> Textures;
};
