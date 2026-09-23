#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelEnhancementWidget.generated.h"

UCLASS()
class FPSGAME_API UColdSteelEnhancementWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SelectItem(const FString& Id);
    void SelectTab(bool Enchant);
    void SelectScroll(const FString& Id);
    bool Confirm();
    void Refresh();
    const FColdSteelEnhanceQuote& CurrentQuote()const{return Preview;}
    const FString& SelectedItem()const{return ItemId;}
    bool IsEnchantTab()const{return bEnchant;}
    const FString& Result()const{return Message;}
    TSharedPtr<class SButton> ConfirmControl;
    TSharedPtr<class SButton> EnchantControl;
    TSharedPtr<class SButton> EnhanceControl;
    UPROPERTY(Transient) TObjectPtr<class UM4GunsmithWidget> WorkbenchPreview;
    TSharedPtr<class SWidget> PreviewSurface;
    TSharedPtr<class SButton> ResetViewControl,AimViewControl;
protected:
    virtual TSharedRef<SWidget> RebuildWidget()override;
    virtual void NativeConstruct()override;
    virtual void NativeDestruct()override;
    virtual void NativeTick(const FGeometry&,float Delta)override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&)override;
private:
    class UColdSteelEnhancementSystem* System()const;
    class UColdSteelStatusModel* Profile()const;
    TSharedRef<class SWidget> Label(const FString&,int32 Size=14,FLinearColor Color=FLinearColor::White,bool Numeric=false)const;
    TSharedRef<class SButton> Button(const FString&,TFunction<void()>,bool Primary=false,bool Selected=false,bool Enabled=true);
    TSharedRef<class SWidget> TableRow(const FString&,const FString&,const FString&,const FString&,int32 Benefit=0)const;
    TSharedRef<class SWidget> GlassPanel(TSharedRef<class SWidget> Content);
    void UpdateResponsiveLayout();
    void RefreshIcons();
    void OnWeaponIconReady(const FString& Recipe);
    const FSlateBrush* MaterialIcon(const FString& Definition);
    TMap<FString,TSharedPtr<FSlateBrush>> MaterialBrushes;
    TMap<FString,TSharedPtr<class SImage>> ItemImages;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class UTexture2D>> MaterialTextures;
    FString ItemId,ScrollId,Message;
    bool bEnchant=false,bCompareBase=false,bLastApplySucceeded=false;
    double LastConfirm=-1;
    FColdSteelEnhanceQuote Preview;
    FDelegateHandle ProfileHandle,IconHandle;
    TSharedPtr<class SVerticalBox> Rail,Inspector,ProjectSummary,Costs;
    TSharedPtr<class SHorizontalBox> Options;
    TSharedPtr<class STextBlock> ItemTitle,ItemLevel,Footer,ConfirmText;
    TSharedPtr<class SBox> BodyHost;
    TSharedPtr<class SWidget> RailContent,CenterContent,InspectorContent;
    TSharedPtr<class SScrollBox> RailScroll,OptionScroll,OverviewScroll,BodyScroll;
    TSharedPtr<class SButton> CurrentCompare,BaseCompare;
    int32 LayoutMode=-1;
    FSlateBrush Background,WeaponBrush,PanelBrush,RowBrush,GlassFallback;
    FButtonStyle Normal,SelectedStyle,PrimaryStyle;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> BackgroundTexture;
};
