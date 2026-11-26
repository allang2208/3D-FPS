#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "Framework/SlateDelegates.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelExpeditionWidget.generated.h"

struct FColdSteelExpeditionSection
{
    FString Title,Text;
};

struct FColdSteelExpeditionReward
{
    FColdSteelTooltipContent Content;
    FString Availability;
    FString IconPath;
    int32 Group=0;
    TSharedPtr<FSlateBrush> Brush;
    TWeakPtr<class SImage> Image;
};

/** Presentation only. The caller owns eligibility, costs and any departure transaction. */
struct FColdSteelExpeditionDestination
{
    FName Id;
    FString Name, Category, Description;
    FString ArtworkFile; // Optional path relative to Content; unset destinations use the neutral engraving.
    FString RecommendedLevel, Scale, Threat, EntryCost, Completion;
    // Route text is a reward-category summary; monster intel is deliberately approximate.
    TArray<FColdSteelExpeditionSection> Routes, Rules, MonsterIntel;
    bool bDungeonLoot=false;
    bool bCanDepart = false;
    FString BlockReason;
};

DECLARE_DELEGATE_RetVal_OneParam(FText, FColdSteelExpeditionRequested, FName);

UCLASS()
class FPSGAME_API UColdSteelExpeditionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetDestinations(TArray<FColdSteelExpeditionDestination> Entries);
    void RefreshCarriedEquipment() { RefreshPreparationData(); }
    FColdSteelExpeditionRequested OnDepartureRequested;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float Delta) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    enum class EActionRole { Quiet, Secondary, Primary };
    const FColdSteelExpeditionDestination* Selection() const;
    class UColdSteelStatusModel* Profile() const;
    void RefreshList();
    void RefreshDestinationArtwork();
    void RefreshDetail();
    void RefreshPreparation();
    void RefreshPreparationData();
    void BuildRewardPreview();
    void LoadNextRewardIcon();
    void AddRewards();
    TSharedRef<class SWidget> RewardCard(FColdSteelExpeditionReward& Reward);
    TSharedRef<class SWidget> Section(const FString& Title,const FString& Text);
    void UpdateLayout();
    void SelectDestination(FName Id);
    void ConfirmDeparture();
    void UpdateSelectionStyles();
    void Close();
    bool CanConfirm() const;
    FText BlockMessage() const;
    TSharedRef<class SWidget> Label(const FString& Text, int32 Size = 14, FLinearColor Color = FLinearColor::White, bool Numeric = false, bool Wrap = true) const;
    TSharedRef<class SWidget> Card(TSharedRef<class SWidget> Content, float Inset = 14);
    TSharedRef<class SWidget> Divider(EOrientation Orientation = Orient_Horizontal) const;
    TSharedRef<class SWidget> Row(const FString& Name, const FString& Value, bool Numeric = false) const;
    TSharedRef<class SButton> Action(const FString& Text, TFunction<void()> Callback, EActionRole Role = EActionRole::Quiet);
    TSharedRef<class SButton> NavigationTab(const FString& Text, TAttribute<bool> Current, FOnClicked OnClicked);
    TSharedRef<class SWidget> BuildCatalog();
    TSharedRef<class SWidget> BuildDestinationSelector();
    TSharedRef<class SWidget> BuildDetail();
    TSharedRef<class SWidget> BuildPreparation();
    TArray<FColdSteelExpeditionDestination> Destinations;
    TArray<FName> VisibleIds;
    FName SelectedId;
    FString Query;
    FText Feedback;
    bool bAvailableOnly = false;
    bool bSingleColumnFacts = false;
    bool bStackOverview = false;
    bool bRewardsLoaded=false;
    bool bRewardIconLoading=false,bClosing=false;
    int32 NextRewardIcon=0;
    int32 CardColumns=1;
    FString PreparationKey;
    FString LoadedArtworkFile;
    TArray<FColdSteelExpeditionReward> RewardPreview;
    int32 DetailTab = 0, LayoutMode = -1;
    FDelegateHandle ProfileHandle;
    TSharedPtr<class SBox> BodyHost;
    TSharedPtr<class SVerticalBox> CatalogRows, DetailRows, PreparationRows;
    TSharedPtr<class SScrollBox> DetailScroll, PreparationScroll;
    TSharedPtr<class SComboButton> DestinationPicker;
    TSharedPtr<class SEditableTextBox> Search;
    TMap<FName, TSharedPtr<class SButton>> CatalogButtons;
    TArray<TSharedPtr<class SButton>> FilterButtons;
    FSlateBrush PanelBrush, FallbackBrush, CardBrush, HeroBrush, RewardTooltipBrush;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> DestinationArtwork;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture2D>> RewardTextures;
    FSlateBrush DestinationArtBrush;
    FButtonStyle NormalStyle, SelectedStyle, PrimaryStyle, QuietStyle, MutedStyle;
    FEditableTextBoxStyle SearchStyle;
    FComboButtonStyle DestinationStyle;
};
