#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ColdSteelSkillPage.generated.h"
class UColdSteelStatusModel;
class UTexture2D;
class SBox;
class SScrollBox;
class SButton;

/** Passive skills live in the existing drawer; their effects are owned by the profile model. */
UCLASS()
class FPSGAME_API UColdSteelSkillPage : public UUserWidget
{
    GENERATED_BODY()
public:
    bool GoBack();
    void SetHUD(class UColdSteelHUDWidget* Owner);
    void SetLayoutWidth(float Pixels);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
    virtual FReply NativeOnPreviewMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&) override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&) override;
private:
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    FName PendingDragSkill;
    FSlateRect PressedSkillBounds;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> IconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> DodgeIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> DexterousHandsIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> PistolIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> CriticalIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> FireballIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> IceSpikeIconTexture;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> QuickCombatIconTexture;
    TSharedPtr<SButton> IceSpikeDetailButton;
    FSlateBrush IceSpikeIconBrush;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> HeavyIconTexture;
    TSharedPtr<SBox> Root;
    TSharedPtr<SScrollBox> Scroll;
    TSharedPtr<SButton> DetailButton,PistolDetailButton,CriticalDetailButton,FireballDetailButton,HeavyDetailButton,DodgeDetailButton,DexterousHandsDetailButton,QuickCombatDetailButton,BackButton;
    TArray<TSharedPtr<SButton>> FilterButtons;
    FSlateBrush IconBrush,PistolIconBrush,CriticalIconBrush,FireballIconBrush,HeavyIconBrush,DodgeIconBrush,DexterousHandsIconBrush,QuickCombatIconBrush,CardBrush;
    FName SelectedSkill=TEXT("rifleMastery");
    const FColdSteelSkillDefinition& Definition(FName Id) const;
    FColdSteelSkillProgress Progress(FName Id) const;
    FButtonStyle ActionStyle;
    float Scale=1;
    float PageWidth=720;
    int32 Category=0;
    bool bDetail=false;
    TSharedRef<SWidget> BuildPage();
    TSharedRef<SWidget> Overview(bool bCompact,FName Id);
    TSharedRef<SWidget> EffectRow(const FString& Caption,int32 Index);
    TSharedRef<SWidget> TrainingCard();
    TSharedRef<SWidget> Paragraph(const FString& Value,float Pixels,const FLinearColor& Color,float Width) const;
    TSharedRef<SWidget> Label(const FString& Value,float Pixels,const FLinearColor& Color,bool bNumeric=false) const;
    FString EffectValue(int32 Index,bool bNext) const;
    FReply SelectCategory(int32 Index);
    FReply OpenDetail(FName Id);
    void RefreshLayout();
};
