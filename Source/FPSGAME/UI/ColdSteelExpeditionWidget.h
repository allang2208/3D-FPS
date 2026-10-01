#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
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
    FString RecommendedLevel, Scale, Threat, EntryCost, Completion;
    TArray<FColdSteelExpeditionSection> Routes, Rules;
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
    FColdSteelExpeditionRequested OnDepartureRequested;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float Delta) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    const FColdSteelExpeditionDestination* Selection() const;
    class UColdSteelStatusModel* Profile() const;
    void RefreshList();
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
    TSharedRef<class SWidget> Row(const FString& Name, const FString& Value, bool Numeric = false) const;
    TSharedRef<class SButton> Action(const FString& Text, TFunction<void()> Callback, bool Primary = false);
    TSharedRef<class SWidget> BuildCatalog();
    TSharedRef<class SWidget> BuildDetail();
    TSharedRef<class SWidget> BuildPreparation();
    TArray<FColdSteelExpeditionDestination> Destinations;
    TArray<FName> VisibleIds;
    FName SelectedId;
    FString Query;
    FText Feedback;
    bool bAvailableOnly = false;
    bool bSingleColumnFacts = false;
    bool bRewardsLoaded=false;
    bool bRewardIconLoading=false,bClosing=false;
    int32 NextRewardIcon=0;
    int32 RewardColumns=1;
    FString PreparationKey;
    TArray<FColdSteelExpeditionReward> RewardPreview;
    float PreparedMaxMana=0.f;
    int32 DetailTab = 0, CompactPage = 0, LayoutMode = -1;
    FDelegateHandle ProfileHandle;
    TSharedPtr<class SBox> BodyHost;
    TSharedPtr<class SVerticalBox> CatalogRows, DetailRows, PreparationRows;
    TSharedPtr<class SScrollBox> DetailScroll;
    TSharedPtr<class SEditableTextBox> Search;
    TMap<FName, TSharedPtr<class SButton>> CatalogButtons;
    TArray<TSharedPtr<class SButton>> FilterButtons, DetailButtons, CompactButtons;
    FSlateBrush PanelBrush, FallbackBrush, CardBrush, HeroBrush, RewardTooltipBrush;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> DestinationArtwork;
    UPROPERTY(Transient) TArray<TObjectPtr<class UTexture2D>> RewardTextures;
    TWeakObjectPtr<class UFPSCombatHealthComponent> PlayerHealth;
    FSlateBrush DestinationArtBrush;
    FButtonStyle NormalStyle, SelectedStyle, PrimaryStyle;
    FProgressBarStyle ResourceStyle;
    FEditableTextBoxStyle SearchStyle;
};
