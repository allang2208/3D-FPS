#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelItemTooltip.generated.h"
class USizeBox;
class UScrollBox;
class UHorizontalBox;
class UButton;
class UTextBlock;
class UVerticalBox;
class UColdSteelStatusModel;
/** One read-only inspector shared by inventory, equipment and warehouse. */
UCLASS()
class FPSGAME_API UColdSteelItemTooltip : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowItem(const FString& Id,FVector2D Anchor,bool Pin,UWidget* Source);
    void Hide(bool Force=false);
    bool IsPinned()const{return bPinned&&IsVisible();}
    const FString& ItemId()const{return InstanceId;}
    const FColdSteelTooltipContent& Content()const{return Presentation;}
    FVector2D Extent()const{return Size;}
    bool HasHorizontalOverflow()const{return bHorizontalOverflow;}
    bool HasVerticalOverflow()const{return bVerticalOverflow;}
    void ScrollToSideCards();
protected:
    virtual void NativeOnInitialized()override;
    virtual void NativeConstruct()override;
    virtual void NativeDestruct()override;
    virtual void NativeTick(const FGeometry&,float)override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&)override;
private:
    friend class UColdSteelHUDWidget;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<USizeBox> Frame;
    UPROPERTY() TObjectPtr<class UBorder> Surface;
    UPROPERTY() TObjectPtr<class UBorder> Shadow;
    UPROPERTY() TObjectPtr<UVerticalBox> RootColumn;
    UPROPERTY() TObjectPtr<UVerticalBox> Header;
    UPROPERTY() TObjectPtr<USizeBox> BodyHeight;
    UPROPERTY() TObjectPtr<UScrollBox> Vertical;
    UPROPERTY() TObjectPtr<UHorizontalBox> Cards;
    UPROPERTY() TObjectPtr<UButton> Close;
    UPROPERTY() TObjectPtr<UTextBlock> TitleText;
    UPROPERTY() TObjectPtr<UTextBlock> MetaText;
    UPROPERTY() TObjectPtr<UTextBlock> LocationText;
    UPROPERTY() TObjectPtr<UTextBlock> ScopeText;
    UPROPERTY() TObjectPtr<UTextBlock> FooterText;
    UPROPERTY() TObjectPtr<class UBorder> FooterFrame;
    UPROPERTY() TObjectPtr<UTextBlock> ComparisonText;
    UPROPERTY() TObjectPtr<UTextBlock> MissingIcon;
    UPROPERTY() TObjectPtr<class UImage> Icon;
    UPROPERTY() TObjectPtr<class UColdSteelWeaponIcons> WeaponIcons;
    UPROPERTY() TMap<FString,TObjectPtr<class UTexture2D>> TextureCache;
    UPROPERTY() TMap<FString,TObjectPtr<class UExpandableArea>> Sections;
    UPROPERTY() TMap<FString,TObjectPtr<class UColdSteelDisclosureIndicator>> Disclosures;
    TWeakObjectPtr<UWidget> ReturnFocus;
    FDelegateHandle ChangedHandle,IconHandle;
    FColdSteelTooltipContent Presentation;
    FString InstanceId,Signature,IconKey;
    FVector2D At,Size,LastViewport,PlacedAt;
    float Scale=1;
    float WidthPixels=520,SettleSeconds=0;
    TMap<FString,bool> Expanded;
    struct FRowView
    {
        int32 Card=0,Row=0,Tone=0;
        TWeakObjectPtr<UTextBlock> Label,Value;
        float Pixels=14.f;
        bool bCompact=false,bMetric=false;
    };
    TArray<FRowView> RowViews;
    bool bPinned=false,bHorizontalOverflow=false,bVerticalOverflow=false;
    bool bPlacementLocked=false,bStartDisclosureIntro=false;
    void Refresh();
    void BuildCards();
    void FitAndPlace(bool RevealMain);
    UTextBlock* Text(const FString&,float,const FLinearColor&,bool Numeric=false);
    void AddRow(UVerticalBox*,const FColdSteelTooltipRow&,int32 Card,int32 Row,bool Compact=false);
    void AddRule(UVerticalBox*,float Top=10.f,float Bottom=10.f,bool Dashed=false);
    void AddCoreGrid(UVerticalBox*);
    void AddDetails(UVerticalBox*);
    class UExpandableArea* AddSection(UVerticalBox*,const FString& Key,const FString& Title,bool Open);
    void UpdateRows();
    void RefreshIcon();
    void OnWeaponIconReady(const FString& Recipe);
    FString StructureSignature()const;
    float InnerWidth()const;
    const FColdSteelTooltipRow& RowData(const FRowView&)const;
    UFUNCTION() void ExpansionChanged(class UExpandableArea* Area,bool Open);
    UFUNCTION() void CloseClicked();
};
