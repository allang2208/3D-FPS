#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/SCompoundWidget.h"

class AVillageSmartTurret;
class SHorseMarketPlate;
class SBorder;
class SBox;
class SButton;
class SScrollBox;
class STextBlock;
class SVerticalBox;
class UColdSteelStatusModel;
class UTexture2D;
struct FColdSteelItem;

DECLARE_DELEGATE_OneParam(FOnSmartTurretMount, const FString& /*ItemInstanceId*/);

/**
 * Cold Steel right-side slide-in drawer opened via [E] on AVillageSmartTurret to mount,
 * swap, or reclaim one of the 16 primary long guns. Matches SSiegeWorkshopMarket styling.
 */
class FPSGAME_API SSmartTurretDrawer final : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SSmartTurretDrawer)
		: _Turret(nullptr)
		, _Model(nullptr)
	{}
		SLATE_ARGUMENT(AVillageSmartTurret*, Turret)
		SLATE_ARGUMENT(UColdSteelStatusModel*, Model)
		SLATE_EVENT(FOnSmartTurretMount, OnMount)
		SLATE_EVENT(FSimpleDelegate, OnUnmount)
		SLATE_EVENT(FSimpleDelegate, OnClose)
	SLATE_END_ARGS()

	virtual ~SSmartTurretDrawer() override;

	void Construct(const FArguments& Args);
	void SetFeedback(bool bSuccess, const FString& Message);
	void RefreshAll();
	void RequestClose();

	virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime) override;

private:
	friend struct FSiegeDrawerReview;

	enum class ETurretFilter : uint8 { All = 0, Rifle, LMG, Shotgun, Sniper };

	void RefreshLiveStatus();
	void RebuildMountedCard();
	void RebuildCandidateList();
	void UpdateFilterButtons();
	const FSlateBrush* ResolveWeaponIconBrush(const FColdSteelItem& Item);

	TWeakObjectPtr<AVillageSmartTurret> Turret;
	TWeakObjectPtr<UColdSteelStatusModel> Model;
	FDelegateHandle ChangedHandle;

	FOnSmartTurretMount OnMount;
	FSimpleDelegate OnUnmount;
	FSimpleDelegate OnClose;

	TStrongObjectPtr<UTexture2D> HeroTexture;
	FSlateBrush HeroBrush;
	TMap<FString, TStrongObjectPtr<UTexture2D>> LoadedIconTextures;
	TMap<FString, TSharedPtr<FSlateBrush>> LoadedIconBrushes;

	TSharedPtr<SBox> Drawer;
	TSharedPtr<SHorseMarketPlate> HeroPlate;
	TSharedPtr<SBox> HeroHost;
	TSharedPtr<STextBlock> ShareTag;
	TSharedPtr<SBorder> StateBadge;
	TSharedPtr<STextBlock> StateBadgeText;
	TSharedPtr<STextBlock> HeroMetaText;
	TSharedPtr<STextBlock> SummaryValues[4];

	TSharedPtr<SVerticalBox> MountedHost;
	TSharedPtr<STextBlock> MountedAmmoText;
	TSharedPtr<SBorder> MountedAmmoFill;
	TSharedPtr<SBox> MountedAmmoFillBox;
	TSharedPtr<SBox> MountedAmmoEmptyBox;

	TSharedPtr<STextBlock> CandidateHeaderText;
	TSharedPtr<SButton> FilterButtons[5];
	TSharedPtr<STextBlock> FilterLabels[5];
	TSharedPtr<SScrollBox> CandidateScroll;

	TSharedPtr<SBorder> FeedbackFrame;
	TSharedPtr<STextBlock> FeedbackText;

	ETurretFilter ActiveFilter = ETurretFilter::All;
	FString FeedbackMessage;
	bool bHasFeedback = false;
	bool bLastFeedbackSuccess = true;

	FString CachedMountedInstanceId;
	FString CachedMountedDef;
	float CachedLiveHealth = -1.f;
	float CachedLiveMaxHealth = -1.f;
	uint64 CachedLiveRanksLow = MAX_uint64;
	uint64 CachedLiveRanksHigh = MAX_uint64;
	int32 CachedLiveHasWeapon = -1;
	int32 CachedLiveReloading = -1;
	int32 CachedLiveAmmo = -1;
	int32 CachedLiveMaxAmmo = -1;
	int32 CachedLiveReloadTenths = -1;

	float DrawerWidth = 540.f;
	float OpenFraction = 0.f;
	bool bCompactHeader = false;
	bool bClosing = false;
	bool bCloseQueued = false;
};
