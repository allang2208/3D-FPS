#include "SSmartTurretDrawer.h"

#include "ColdSteelMarketCardStyle.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "SHorseMarketPlate.h"
#include "../WorldGeneration/VillageSiegeUpgrades.h"
#include "../WorldGeneration/VillageSmartTurret.h"
#include "Async/Async.h"
#include "Brushes/SlateNoResource.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
FText TText(const FString& S) { return FText::FromString(S); }
FText TText(const TCHAR* S) { return FText::FromString(S); }

FSlateFontInfo TFont(float Px, ColdSteelUI::ETextWeight Weight = ColdSteelUI::ETextWeight::Regular)
{
	return ColdSteelUI::TextFont(Px * .75f, Weight);
}

const FSlateBrush& PillDarkBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(15, 212), 4, FLinearColor(222.f / 255.f, 222.f / 255.f, 222.f / 255.f, .24f), 1); return B; }
const FSlateBrush& PillGoldBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(26, 21, 14, 228)), 4, ColdSteelUI::HUDGold, 1); return B; }
const FSlateBrush& PillMutedBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(22, 220), 4, ColdSteelUI::Gray(222, 30), 1); return B; }
const FSlateBrush& StatNormalBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255, 9), 6, ColdSteelUI::Gray(222, 24), 1); return B; }
const FSlateBrush& StatSelectedBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .07f), 6, FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .62f), 1.2f); return B; }
const FSlateBrush& StripNormalBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(13, 185), 4, ColdSteelUI::Gray(222, 20), 1); return B; }
const FSlateBrush& StripGoldBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(16, 205), 4, FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .42f), 1); return B; }
const FSlateBrush& StripErrBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(34, 18, 22, 215)), 4, FLinearColor(ColdSteelUI::Danger.R, ColdSteelUI::Danger.G, ColdSteelUI::Danger.B, .55f), 1); return B; }
const FSlateBrush& IconWellBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 5, ColdSteelUI::Gray(222, 26), 1); return B; }
const FSlateBrush& TrackBgBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 2.f, ColdSteelUI::Gray(222, 20), 0.7f); return B; }
const FSlateBrush& TrackGoldBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::HUDGold, 2.f, FLinearColor::Transparent, 0); return B; }
const FSlateBrush& TrackLightGoldBrush() { static const FSlateBrush B = ColdSteelUI::RoundedBrush(ColdSteelUI::HUDGoldLight, 2.f, FLinearColor::Transparent, 0); return B; }

const FButtonStyle& FilterPillStyle(bool bActive)
{
	using namespace ColdSteelUI;
	static const FButtonStyle On = []
	{
		FButtonStyle S = ButtonStyle();
		S.SetNormal(RoundedBrush(FLinearColor::FromSRGBColor(FColor(38, 34, 24, 236)), 4, FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, .78f), 1.1f));
		S.SetHovered(RoundedBrush(FLinearColor::FromSRGBColor(FColor(48, 42, 30, 244)), 4, HUDGoldLight, 1.2f));
		S.SetPressed(RoundedBrush(FLinearColor::FromSRGBColor(FColor(28, 24, 18, 244)), 4, HUDGold, 1.1f));
		return S.SetNormalPadding(0).SetPressedPadding(0);
	}();
	static const FButtonStyle Off = []
	{
		FButtonStyle S = ButtonStyle();
		S.SetNormal(RoundedBrush(Gray(22, 210), 4, Gray(222, 24), 1.f));
		S.SetHovered(RoundedBrush(Gray(36, 230), 4, Gray(222, 48), 1.f));
		S.SetPressed(RoundedBrush(Gray(18, 235), 4, HUDGoldDim, 1.f));
		return S.SetNormalPadding(0).SetPressedPadding(0);
	}();
	return bActive ? On : Off;
}

const TCHAR* FilterLabel(int32 Index)
{
	switch (Index)
	{
	case 0:  return TEXT("全部");
	case 1:  return TEXT("步枪");
	case 2:  return TEXT("机枪");
	case 3:  return TEXT("霰弹");
	default: return TEXT("狙击");
	}
}

bool MatchesArchetypeFilter(const FString& Def, int32 FilterIdx)
{
	if (FilterIdx == 0) return true;
	const FString Label = AVillageSmartTurret::WeaponArchetypeLabel(Def);
	if (FilterIdx == 1) return Label == TEXT("突击步枪") || Label == TEXT("步枪");
	if (FilterIdx == 2) return Label == TEXT("轻机枪");
	if (FilterIdx == 3) return Label == TEXT("霰弹枪") || Label == TEXT("霰弹");
	if (FilterIdx == 4) return Label == TEXT("狙击步枪") || Label == TEXT("狙击");
	return true;
}

FString FormatCandidateStatsLine(const FSmartTurretWeaponStats& Stats)
{
	const FString Dmg = (Stats.bShotgun && Stats.PelletCount > 1)
		? FString::Printf(TEXT("伤 %d×%d"), FMath::RoundToInt(Stats.PerShotDamage), Stats.PelletCount)
		: FString::Printf(TEXT("伤 %d"), FMath::RoundToInt(Stats.PerShotDamage));
	return FString::Printf(TEXT("%s · %.0f RPM · %d发 · 秒伤 %.0f"),
		*Dmg, Stats.RPM, Stats.ExpandedCapacity, Stats.EstimatedDPS);
}

FString FormatMountedStatsLine(const FSmartTurretWeaponStats& Stats)
{
	const FString Dmg = (Stats.bShotgun && Stats.PelletCount > 1)
		? FString::Printf(TEXT("伤 %d×%d"), FMath::RoundToInt(Stats.PerShotDamage), Stats.PelletCount)
		: FString::Printf(TEXT("伤 %d"), FMath::RoundToInt(Stats.PerShotDamage));
	return FString::Printf(TEXT("%s · %.0f RPM · 秒伤 %.0f · %.0fm"),
		*Dmg, Stats.RPM, Stats.EstimatedDPS, Stats.EffectiveScanRangeCm / 100.f);
}
}

SSmartTurretDrawer::~SSmartTurretDrawer()
{
	if (UColdSteelStatusModel* M = Model.Get(); M && ChangedHandle.IsValid())
	{
		M->OnChanged.Remove(ChangedHandle);
		ChangedHandle.Reset();
	}
	LoadedIconBrushes.Reset();
	LoadedIconTextures.Reset();
	HeroTexture.Reset();
}

void SSmartTurretDrawer::Construct(const FArguments& Args)
{
	using namespace ColdSteelUI;
	Turret = Args._Turret;
	Model = Args._Model;
	OnMount = Args._OnMount;
	OnUnmount = Args._OnUnmount;
	OnClose = Args._OnClose;

	if (UColdSteelStatusModel* M = Model.Get())
	{
		ChangedHandle = M->OnChanged.AddSP(this, &SSmartTurretDrawer::RefreshAll);
	}

	HeroTexture.Reset(FImageUtils::ImportFileAsTexture2D(
		FPaths::ProjectContentDir() / TEXT("ColdSteelUI/SiegeWorkshop/SmartTurret.jpg")));
	if (HeroTexture.IsValid())
	{
		HeroBrush.SetResourceObject(HeroTexture.Get());
		HeroBrush.DrawAs = ESlateBrushDrawType::Image;
		HeroBrush.SetImageSize(FVector2D(672.f, 322.f));
		HeroBrush.SetUVRegion(FBox2f(FVector2f::ZeroVector, FVector2f(1.f, 1.f)));
	}

	static const FSlateBrush Panel = RoundedBrush(GlassFallback, PanelRadius, Border, 1.f);
	static const FSlateBrush HeaderBg = RoundedBrushCorners(HeaderTint, FVector4(PanelRadius, PanelRadius, 0, 0));
	static const FSlateBrush Rule = RoundedBrush(Gray(222, 22), 0, FLinearColor::Transparent, 0);
	static const FSlateBrush GoldBar = RoundedBrush(HUDGold, 1, FLinearColor::Transparent, 0);
	static const FScrollBoxStyle ScrollStyle = FScrollBoxStyle()
		.SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource())
		.SetLeftShadowBrush(FSlateNoResource()).SetRightShadowBrush(FSlateNoResource());

	auto SummaryRow = SNew(SHorizontalBox);
	static const TCHAR* SumLabels[4] = { TEXT("火力"), TEXT("装/速"), TEXT("射程"), TEXT("锁/穿") };
	for (int32 I = 0; I < 4; ++I)
	{
		if (I > 0)
		{
			SummaryRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(2, 0)
			[
				SNew(SBox).WidthOverride(1.f).HeightOverride(11.f)[SNew(SImage).Image(&Rule)]
			];
		}
		SummaryRow->AddSlot().FillWidth(1).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 4, 0)
			[
				SNew(STextBlock).Text(TText(SumLabels[I])).Font(TFont(11.f)).ColorAndOpacity(TextTertiary)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SAssignNew(SummaryValues[I], STextBlock).Font(TFont(11.5f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
			]
		];
	}

	auto FilterRow = SNew(SHorizontalBox);
	for (int32 FIdx = 0; FIdx < 5; ++FIdx)
	{
		FilterRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(FIdx == 0 ? 0.f : 4.f, 0, 0, 0)
		[
			SNew(SBox).HeightOverride(24.f)
			[
				SAssignNew(FilterButtons[FIdx], SButton)
				.ButtonStyle(&FilterPillStyle(FIdx == 0))
				.ContentPadding(FMargin(8, 2))
				.OnClicked_Lambda([this, FIdx]()
				{
					ActiveFilter = static_cast<ETurretFilter>(FIdx);
					UpdateFilterButtons();
					RebuildCandidateList();
					return FReply::Handled();
				})
				[
					SAssignNew(FilterLabels[FIdx], STextBlock)
					.Text(TText(FilterLabel(FIdx)))
					.Font(TFont(11.f, ETextWeight::SemiBold))
					.ColorAndOpacity(FIdx == 0 ? HUDGoldLight : TextSecondary)
				]
			]
		];
	}

	SetClipping(EWidgetClipping::ClipToBounds);
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Fill).Padding(0, 8, 0, 8)
		[
			SAssignNew(Drawer, SBox).WidthOverride_Lambda([this]() { return FOptionalSize(DrawerWidth); })
			[
				SNew(SBorder).BorderImage(&Panel).Padding(0)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SBorder).BorderImage(&HeaderBg).Padding(FMargin(16, 11, 16, 10))
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
							[
								SNew(SHorizontalBox)
								+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
								[
									SNew(SBox).WidthOverride(2.5f).HeightOverride(16.f)[SNew(SImage).Image(&GoldBar)]
								]
								+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
								[
									SNew(STextBlock).Text(TText(TEXT("智能机枪塔"))).Font(TFont(20.f, ETextWeight::Bold)).ColorAndOpacity(TextPrimary)
								]
								+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 1, 0, 0)
								[
									SAssignNew(ShareTag, STextBlock).Text(TText(TEXT("长枪挂载 · 智控索敌"))).Font(TFont(12.f)).ColorAndOpacity(TextTertiary)
								]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
							[
								SAssignNew(StateBadge, SBorder).BorderImage(&PillMutedBrush()).Padding(FMargin(8, 3))
								[
									SAssignNew(StateBadgeText, STextBlock).Font(TFont(11.5f, ETextWeight::SemiBold)).ColorAndOpacity(TextSecondary)
								]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
							[
								SNew(SButton).ButtonStyle(&ColdSteelMarketCard::SecondaryActionStyle()).ContentPadding(FMargin(10, 5))
								.ToolTip(ColdSteelToolTip::Make(TText(TEXT("收起枪械挂载台"))))
								.OnClicked_Lambda([this]() { RequestClose(); return FReply::Handled(); })
								[
									SNew(SHorizontalBox)
									+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
									[
										SNew(STextBlock).Text(TText(TEXT("收起"))).Font(TFont(13.f)).ColorAndOpacity(TextPrimary)
									]
									+ SHorizontalBox::Slot().AutoWidth().Padding(6, 0, 0, 0).VAlign(VAlign_Center)
									[
										SNew(STextBlock).Text(TText(TEXT("Esc"))).Font(TFont(11.f)).ColorAndOpacity(HUDGoldLight)
									]
								]
							]
						]
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]
					]
					+ SVerticalBox::Slot().FillHeight(1).Padding(16, 10, 16, 11)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()
						[
							SAssignNew(HeroHost, SBox)
							[
								SNew(SBorder).BorderImage(&StatNormalBrush()).Padding(1)
								[
									SNew(SBox).HeightOverride(76.f).Clipping(EWidgetClipping::ClipToBounds)
									[
										SNew(SOverlay)
										+ SOverlay::Slot()
										[
											SAssignNew(HeroPlate, SHorseMarketPlate)
											.Sharp(HeroTexture.IsValid() ? &HeroBrush : nullptr)
											.PreferredHeight(76.f)
											.CornerRadius(5.f)
											.ShowScrim(true)
											.CornerBrackets(false)
											.PortraitFocus(FVector2f(.50f, .36f))
										]
										+ SOverlay::Slot().VAlign(VAlign_Bottom).Padding(10, 0, 10, 7)
										[
											SNew(SHorizontalBox)
											+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
											[
												SAssignNew(HeroMetaText, STextBlock)
												.Font(TFont(11.5f, ETextWeight::SemiBold))
												.ColorAndOpacity(TextPrimary)
												.ShadowOffset(FVector2D(0, 1.f)).ShadowColorAndOpacity(FLinearColor(0, 0, 0, .90f))
												.OverflowPolicy(ETextOverflowPolicy::Ellipsis)
											]
											+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
											[
												SNew(STextBlock)
												.Text(TText(TEXT("无限备弹 · 仅16款长枪")))
												.Font(TFont(11.f))
												.ColorAndOpacity(HUDGoldLight)
												.ShadowOffset(FVector2D(0, 1.f)).ShadowColorAndOpacity(FLinearColor(0, 0, 0, .90f))
											]
										]
									]
								]
							]
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
						[
							SNew(SBorder).BorderImage(&StripNormalBrush()).Padding(FMargin(8, 6))[SummaryRow]
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 6)
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 7, 0)
							[
								SNew(SBox).WidthOverride(2.5f).HeightOverride(12.f)[SNew(SImage).Image(&GoldBar)]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
							[
								SNew(STextBlock).Text(TText(TEXT("当前挂载"))).Font(TFont(14.f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)
							]
							+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(10, 0, 10, 0)
							[
								SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
							[
								SNew(STextBlock).Text(TText(TEXT("共享工坊即时强化"))).Font(TFont(11.5f)).ColorAndOpacity(TextTertiary)
							]
						]
						+ SVerticalBox::Slot().AutoHeight()
						[
							SAssignNew(MountedHost, SVerticalBox)
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 6)
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 7, 0)
							[
								SNew(SBox).WidthOverride(2.5f).HeightOverride(12.f)[SNew(SImage).Image(&GoldBar)]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
							[
								SAssignNew(CandidateHeaderText, STextBlock)
								.Text(TText(TEXT("可装载长枪")))
								.Font(TFont(14.f, ETextWeight::SemiBold))
								.ColorAndOpacity(HUDGoldLight)
							]
							+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8, 0, 8, 0)
							[
								SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]
							]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
							[
								FilterRow
							]
						]
						+ SVerticalBox::Slot().FillHeight(1)
						[
							ColdSteelUI::ApplyGoldScroll(
								SAssignNew(CandidateScroll, SScrollBox).Style(&ScrollStyle)
								.AllowOverscroll(EAllowOverscroll::No)
								.ConsumeMouseWheel(EConsumeMouseWheel::Always).AnimateWheelScrolling(true),
								FVector2D(5.5f, 5.5f), FMargin(6, 0, 0, 0), true)
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
						[
							SAssignNew(FeedbackFrame, SBorder).BorderImage(&StripNormalBrush()).Padding(FMargin(10, 6))
							[
								SAssignNew(FeedbackText, STextBlock).Font(TFont(12.5f)).AutoWrapText(true)
								.Text(TText(TEXT("点击装载将主战长枪部署到机枪塔；炮塔损毁或拆除时枪械自动退回。")))
								.ColorAndOpacity(TextSecondary)
							]
						]
					]
				]
			]
		]
	];

	if (HeroPlate.IsValid())
	{
		HeroPlate->SetSelected(true);
		HeroPlate->SetReveal(0.65f);
	}
	Drawer->SetRenderOpacity(0.f);
	Drawer->SetVisibility(EVisibility::HitTestInvisible);
	RefreshAll();
}

void SSmartTurretDrawer::SetFeedback(bool bSuccess, const FString& Message)
{
	bHasFeedback = !Message.IsEmpty();
	bLastFeedbackSuccess = bSuccess;
	FeedbackMessage = Message;
	if (!FeedbackFrame.IsValid() || !FeedbackText.IsValid()) return;

	if (!bHasFeedback)
	{
		FeedbackFrame->SetBorderImage(&StripNormalBrush());
		FeedbackText->SetText(TText(TEXT("点击装载将主战长枪部署到机枪塔；炮塔损毁或拆除时枪械自动退回。")));
		FeedbackText->SetColorAndOpacity(ColdSteelUI::TextSecondary);
		return;
	}
	FeedbackFrame->SetBorderImage(bSuccess ? &StripGoldBrush() : &StripErrBrush());
	FeedbackText->SetText(TText(Message));
	FeedbackText->SetColorAndOpacity(bSuccess ? ColdSteelUI::Success : ColdSteelUI::Danger);
}

void SSmartTurretDrawer::RequestClose()
{
	if (bClosing) return;
	bClosing = true;
	if (Drawer.IsValid()) Drawer->SetVisibility(EVisibility::HitTestInvisible);
}

void SSmartTurretDrawer::RefreshAll()
{
	CachedLiveHealth = -1.f;
	CachedLiveRanksLow = MAX_uint64;
	CachedLiveRanksHigh = MAX_uint64;
	CachedLiveHasWeapon = -1;
	CachedLiveReloading = -1;
	CachedLiveAmmo = -1;
	CachedLiveMaxAmmo = -1;
	CachedLiveReloadTenths = -1;
	RebuildMountedCard();
	RebuildCandidateList();
	RefreshLiveStatus();
}

void SSmartTurretDrawer::Tick(const FGeometry& G, const double Time, const float Delta)
{
	SCompoundWidget::Tick(G, Time, Delta);
	const FVector2D Size = G.GetLocalSize();
	const float PrevWidth = DrawerWidth;
	const float PrevFrac = OpenFraction;
	DrawerWidth = FMath::Max(1.f, FMath::Min(float(Size.X), FMath::Clamp(float(Size.X) * .40f, 436.f, 596.f)));
	bCompactHeader = Size.Y < 620.f;
	if (ShareTag.IsValid()) ShareTag->SetVisibility(bCompactHeader ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
	if (HeroHost.IsValid()) HeroHost->SetVisibility(bCompactHeader ? EVisibility::Collapsed : EVisibility::SelfHitTestInvisible);

	const float Step = Delta * (bClosing ? 5.6f : 4.5f);
	OpenFraction = FMath::Clamp(OpenFraction + (bClosing ? -Step : Step), 0.f, 1.f);
	if (PrevFrac != OpenFraction || PrevWidth != DrawerWidth)
	{
		const float Ease = ColdSteelUI::EaseSmooth(OpenFraction);
		if (Drawer.IsValid())
		{
			Drawer->SetRenderTransform(FSlateRenderTransform(FVector2D((1.f - Ease) * DrawerWidth, 0.f)));
			Drawer->SetRenderOpacity(Ease);
			Drawer->SetVisibility(!bClosing && OpenFraction >= 1.f ? EVisibility::SelfHitTestInvisible : EVisibility::HitTestInvisible);
		}
	}
	if (bClosing && OpenFraction <= 0.f && !bCloseQueued)
	{
		bCloseQueued = true;
		const TWeakPtr<SSmartTurretDrawer> Weak = SharedThis(this);
		AsyncTask(ENamedThreads::GameThread, [Weak]()
		{
			if (TSharedPtr<SSmartTurretDrawer> Self = Weak.Pin())
			{
				Self->OnClose.ExecuteIfBound();
			}
		});
		return;
	}

	const AVillageSmartTurret* T = Turret.Get();
	if (!T) return;
	const FColdSteelItem& Mounted = T->GetMountedWeapon();
	if (Mounted.InstanceId != CachedMountedInstanceId || Mounted.Definition != CachedMountedDef)
	{
		RefreshAll();
		return;
	}
	RefreshLiveStatus();
}

const FSlateBrush* SSmartTurretDrawer::ResolveWeaponIconBrush(const FColdSteelItem& Item)
{
	if (Item.Definition.IsEmpty()) return nullptr;
	if (const TSharedPtr<FSlateBrush>* Found = LoadedIconBrushes.Find(Item.Definition))
	{
		return Found->Get();
	}

	FString RelFile = ColdSteelInventory::Text(Item, TEXT("ue_icon"));
	if (RelFile.IsEmpty()) RelFile = TEXT("Icons/") + Item.Definition + TEXT(".png");

	FString DiskPath = FPaths::ProjectContentDir() / TEXT("ColdSteelData") / RelFile;
	if (!FPaths::FileExists(DiskPath))
	{
		const FString FallbackPath = FPaths::ProjectContentDir() / TEXT("ColdSteelData/Icons") / (Item.Definition + TEXT(".png"));
		if (FPaths::FileExists(FallbackPath)) DiskPath = FallbackPath;
		else return nullptr;
	}

	UTexture2D* Tex = FImageUtils::ImportFileAsTexture2D(DiskPath);
	if (!Tex) return nullptr;

	LoadedIconTextures.Add(Item.Definition, TStrongObjectPtr<UTexture2D>(Tex));
	TSharedPtr<FSlateBrush> Brush = MakeShared<FSlateBrush>();
	Brush->SetResourceObject(Tex);
	Brush->DrawAs = ESlateBrushDrawType::Image;
	Brush->SetImageSize(FVector2D(Tex->GetSizeX(), Tex->GetSizeY()));
	LoadedIconBrushes.Add(Item.Definition, Brush);
	return Brush.Get();
}

void SSmartTurretDrawer::UpdateFilterButtons()
{
	using namespace ColdSteelUI;
	const int32 ActiveIdx = static_cast<int32>(ActiveFilter);
	for (int32 I = 0; I < 5; ++I)
	{
		const bool bAct = (I == ActiveIdx);
		if (FilterButtons[I].IsValid()) FilterButtons[I]->SetButtonStyle(&FilterPillStyle(bAct));
		if (FilterLabels[I].IsValid()) FilterLabels[I]->SetColorAndOpacity(bAct ? HUDGoldLight : TextSecondary);
	}
}

void SSmartTurretDrawer::RefreshLiveStatus()
{
	using namespace VillageSiegeUpgrades;
	using namespace ColdSteelUI;
	const AVillageSmartTurret* T = Turret.Get();
	if (!T) return;

	const FRanks R = T->CurrentAllRanks();
	const float CurHealth = T->GetHealth();
	const float MaxHealth = T->GetMaximumHealth();
	const int32 HasWeapon = T->HasMountedWeapon() ? 1 : 0;
	const int32 IsReload = (HasWeapon && T->IsReloading()) ? 1 : 0;
	const int32 CurAmmo = HasWeapon ? T->GetCurrentAmmo() : 0;
	const int32 MaxAmmoVal = HasWeapon ? FMath::Max(1, T->GetMaxAmmo()) : 0;
	const int32 ReloadTenths = IsReload ? FMath::Max(0, FMath::RoundToInt(T->GetReloadRemainingSeconds() * 10.f)) : -1;

	const bool bHeaderDirty = !FMath::IsNearlyEqual(CurHealth, CachedLiveHealth, 0.25f)
		|| !FMath::IsNearlyEqual(MaxHealth, CachedLiveMaxHealth, 0.25f)
		|| R.Low != CachedLiveRanksLow || R.High != CachedLiveRanksHigh;
	const bool bStateDirty = HasWeapon != CachedLiveHasWeapon || IsReload != CachedLiveReloading;
	const bool bAmmoDirty = bStateDirty || CurAmmo != CachedLiveAmmo || MaxAmmoVal != CachedLiveMaxAmmo || ReloadTenths != CachedLiveReloadTenths;
	if (!bHeaderDirty && !bStateDirty && !bAmmoDirty) return;

	if (bHeaderDirty)
	{
		CachedLiveHealth = CurHealth;
		CachedLiveMaxHealth = MaxHealth;
		CachedLiveRanksLow = R.Low;
		CachedLiveRanksHigh = R.High;

		const int32 DmgLv = Rank(R, FacilityStatIndex(SmartTurret, TurretDamage));
		const int32 FeedLv = Rank(R, FacilityStatIndex(SmartTurret, TurretFeed));
		const int32 OptLv = Rank(R, FacilityStatIndex(SmartTurret, TurretOptics));
		const int32 WkLv = Rank(R, FacilityStatIndex(SmartTurret, TurretWeakpoint));
		const int32 MagLv = Rank(R, FacilityStatIndex(SmartTurret, TurretMagExpand));
		const int32 PrcLv = Rank(R, FacilityStatIndex(SmartTurret, TurretPierce));

		if (HeroMetaText.IsValid())
		{
			HeroMetaText->SetText(TText(FString::Printf(
				TEXT("耐久 %.0f/%.0f · 火控%d · 供弹%d · 锁敌%d · 弱点%d · 弹链%d · 穿甲%d"),
				FMath::Max(0.f, CurHealth), MaxHealth,
				DmgLv, FeedLv, OptLv, WkLv, MagLv, PrcLv)));
		}

		if (SummaryValues[0].IsValid()) SummaryValues[0]->SetText(TText(FString::Printf(TEXT("%d%%"), FMath::RoundToInt(TurretDamageMultiplier(DmgLv) * 100.))));
		if (SummaryValues[1].IsValid()) SummaryValues[1]->SetText(TText(FString::Printf(TEXT("-%d%%/+%d%%"), FeedLv * 3, FeedLv * 2)));
		if (SummaryValues[2].IsValid()) SummaryValues[2]->SetText(TText(FString::SanitizeFloat(TurretRangeCm(OptLv) / 100., 0) + TEXT("米")));
		if (SummaryValues[3].IsValid()) SummaryValues[3]->SetText(TText(FString::Printf(TEXT("%d%%/+%d"), WkLv * 10, PrcLv)));
	}

	if (bStateDirty)
	{
		CachedLiveHasWeapon = HasWeapon;
		CachedLiveReloading = IsReload;
		if (StateBadge.IsValid() && StateBadgeText.IsValid())
		{
			if (!HasWeapon)
			{
				StateBadge->SetBorderImage(&PillMutedBrush());
				StateBadgeText->SetText(TText(TEXT("待机中")));
				StateBadgeText->SetColorAndOpacity(TextSecondary);
			}
			else if (IsReload)
			{
				StateBadge->SetBorderImage(&PillGoldBrush());
				StateBadgeText->SetText(TText(TEXT("换弹中")));
				StateBadgeText->SetColorAndOpacity(HUDGoldLight);
			}
			else
			{
				StateBadge->SetBorderImage(&PillGoldBrush());
				StateBadgeText->SetText(TText(TEXT("★ 执勤中")));
				StateBadgeText->SetColorAndOpacity(HUDGoldLight);
			}
		}
	}

	if (bAmmoDirty)
	{
		CachedLiveAmmo = CurAmmo;
		CachedLiveMaxAmmo = MaxAmmoVal;
		CachedLiveReloadTenths = ReloadTenths;
		if (HasWeapon && MountedAmmoText.IsValid() && MountedAmmoFillBox.IsValid() && MountedAmmoEmptyBox.IsValid())
		{
			const float Frac = IsReload
				? FMath::Clamp(T->GetReloadProgressFraction(), 0.f, 1.f)
				: FMath::Clamp(float(CurAmmo) / float(MaxAmmoVal), 0.f, 1.f);
			if (IsReload)
			{
				MountedAmmoText->SetText(TText(FString::Printf(TEXT("换弹 %.1fs · %d/%d"), FMath::Max(0.f, T->GetReloadRemainingSeconds()), CurAmmo, MaxAmmoVal)));
				MountedAmmoText->SetColorAndOpacity(HUDGoldLight);
				if (MountedAmmoFill.IsValid()) MountedAmmoFill->SetBorderImage(&TrackLightGoldBrush());
			}
			else
			{
				MountedAmmoText->SetText(TText(FString::Printf(TEXT("弹匣 %d/%d · 无限备弹"), CurAmmo, MaxAmmoVal)));
				MountedAmmoText->SetColorAndOpacity(TextPrimary);
				if (MountedAmmoFill.IsValid()) MountedAmmoFill->SetBorderImage(&TrackGoldBrush());
			}
			MountedAmmoFillBox->SetRenderTransform(FSlateRenderTransform(FScale2D(FMath::Max(0.001f, Frac), 1.f)));
		}
	}
}

void SSmartTurretDrawer::RebuildMountedCard()
{
	using namespace ColdSteelUI;
	if (!MountedHost.IsValid()) return;
	MountedHost->ClearChildren();
	MountedAmmoText.Reset();
	MountedAmmoFill.Reset();
	MountedAmmoFillBox.Reset();
	MountedAmmoEmptyBox.Reset();

	const AVillageSmartTurret* T = Turret.Get();
	if (!T) return;

	const FColdSteelItem& Mounted = T->GetMountedWeapon();
	CachedMountedInstanceId = Mounted.InstanceId;
	CachedMountedDef = Mounted.Definition;

	if (!T->HasMountedWeapon())
	{
		MountedHost->AddSlot().AutoHeight()
		[
			SNew(SBorder).BorderImage(&StatNormalBrush()).Padding(FMargin(12, 10))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
				[
					SNew(SBox).WidthOverride(82.f).HeightOverride(46.f)
					[
						SNew(SBorder).BorderImage(&IconWellBrush()).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[
							SNew(STextBlock).Text(TText(TEXT("+"))).Font(TFont(18.f, ETextWeight::SemiBold)).ColorAndOpacity(TextTertiary)
						]
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(STextBlock).Text(TText(TEXT("尚未装载枪械（待机中）")))
						.Font(TFont(14.5f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 3, 0, 0)
					[
						SNew(STextBlock).Text(TText(TEXT("请从下方背包或夹层选择 16 款主战长枪之一装载，机枪塔将自动索敌开火。")))
						.Font(TFont(11.5f)).ColorAndOpacity(TextSecondary).AutoWrapText(true)
					]
				]
			]
		];
		return;
	}

	const FSmartTurretWeaponStats Stats = T->GetCurrentWeaponStats();
	const FString Name = ColdSteelInventory::Text(Mounted, TEXT("name"));
	const int32 Enhance = FMath::Max(0, int32(ColdSteelInventory::Number(Mounted, TEXT("enhanceLevel"), 0.0)));
	const FString Archetype = AVillageSmartTurret::WeaponArchetypeLabel(Mounted.Definition);
	const FSlateBrush* IconBrush = ResolveWeaponIconBrush(Mounted);

	TSharedRef<SWidget> IconVisual = IconBrush
		? StaticCastSharedRef<SWidget>(SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(IconBrush)])
		: StaticCastSharedRef<SWidget>(SNew(STextBlock).Text(TText(*Archetype)).Font(TFont(11.f)).ColorAndOpacity(TextSecondary));

	MountedHost->AddSlot().AutoHeight()
	[
		SNew(SBorder).BorderImage(&StatSelectedBrush()).Padding(FMargin(12, 10))
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 12, 0)
			[
				SNew(SBox).WidthOverride(88.f).HeightOverride(50.f)
				[
					SNew(SBorder).BorderImage(&IconWellBrush()).Padding(FMargin(4))
					.HAlign(HAlign_Center).VAlign(VAlign_Center)
					[IconVisual]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 0, 10, 0)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						SNew(STextBlock).Text(TText(Name)).Font(TFont(15.f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
						.OverflowPolicy(ETextOverflowPolicy::Ellipsis)
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6, 0, 0, 0)
					[
						SNew(SBorder).BorderImage(&PillGoldBrush()).Padding(FMargin(5, 1))
						.Visibility(Enhance > 0 ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
						[
							SNew(STextBlock).Text(TText(FString::Printf(TEXT("+%d"), Enhance))).Font(TFont(10.5f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)
						]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6, 0, 0, 0)
					[
						SNew(SBorder).BorderImage(&PillDarkBrush()).Padding(FMargin(6, 1))
						[
							SNew(STextBlock).Text(TText(Archetype)).Font(TFont(10.5f)).ColorAndOpacity(TextSecondary)
						]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(5, 0, 0, 0)
					[
						SNew(SBorder).BorderImage(&PillMutedBrush()).Padding(FMargin(5, 1))
						.Visibility(Stats.bSuppressed ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
						[
							SNew(STextBlock).Text(TText(TEXT("消音"))).Font(TFont(10.5f)).ColorAndOpacity(Success)
						]
					]
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
				[
					SNew(STextBlock).Text(TText(FormatMountedStatsLine(Stats)))
					.Font(TFont(12.f)).ColorAndOpacity(TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 0, 10, 0)
					[
						SNew(SBox).HeightOverride(4.f)
						[
							SNew(SBorder).BorderImage(&TrackBgBrush()).Padding(0)
							[
								SAssignNew(MountedAmmoFillBox, SBox).RenderTransformPivot(FVector2D(0.f, 0.5f))
								[
									SAssignNew(MountedAmmoFill, SBorder).BorderImage(&TrackGoldBrush())
								]
							]
						]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						SAssignNew(MountedAmmoText, STextBlock).Font(TFont(11.f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
					]
				]
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SBox).MinDesiredWidth(76.f).HeightOverride(28.f)
				[
					SNew(SButton).ButtonStyle(&ColdSteelMarketCard::SecondaryActionStyle())
					.HAlign(HAlign_Center).VAlign(VAlign_Center).ContentPadding(FMargin(10, 0))
					.OnClicked_Lambda([this]() { OnUnmount.ExecuteIfBound(); return FReply::Handled(); })
					[
						SNew(STextBlock).Text(TText(TEXT("卸下"))).Font(TFont(12.5f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
					]
				]
			]
		]
	];
	// Satisfy header slot handle cleanly
	MountedAmmoEmptyBox = MountedAmmoFillBox;
}

void SSmartTurretDrawer::RebuildCandidateList()
{
	using namespace ColdSteelUI;
	if (!CandidateScroll.IsValid()) return;
	CandidateScroll->ClearChildren();

	const AVillageSmartTurret* T = Turret.Get();
	const UColdSteelStatusModel* M = Model.Get();
	if (!T || !M) return;

	const VillageSiegeUpgrades::FRanks Ranks = T->CurrentAllRanks();
	UGameInstance* GI = T->GetGameInstance();
	const bool bHasMounted = T->HasMountedWeapon();
	const FSmartTurretWeaponStats MountedStats = bHasMounted ? T->GetCurrentWeaponStats() : FSmartTurretWeaponStats{};
	const int32 FilterIdx = static_cast<int32>(ActiveFilter);

	TArray<const FColdSteelItem*> TotalEligible;
	TArray<const FColdSteelItem*> Filtered;
	for (const FColdSteelItem& Item : M->ProfileView().Items)
	{
		if ((Item.Place == 0 || Item.Place == ColdSteelInventory::ColdSteelCompartment::Place)
			&& AVillageSmartTurret::IsMountableFirearm(Item.Definition))
		{
			TotalEligible.Add(&Item);
			if (MatchesArchetypeFilter(Item.Definition, FilterIdx))
			{
				Filtered.Add(&Item);
			}
		}
	}

	if (CandidateHeaderText.IsValid())
	{
		CandidateHeaderText->SetText(TText(FString::Printf(TEXT("可装载长枪 (%d)"), TotalEligible.Num())));
	}

	if (Filtered.IsEmpty())
	{
		const FString EmptyMsg = TotalEligible.IsEmpty()
			? FString(TEXT("背包及夹层中暂无可装载的主战长枪；仅开放步枪、轻机枪、霰弹与狙击（不含手枪）。"))
			: FString(TEXT("当前筛选分类下暂无长枪，请切换上方分类标签。"));
		CandidateScroll->AddSlot().Padding(0, 4, 0, 0)
		[
			SNew(SBorder).BorderImage(&StatNormalBrush()).Padding(FMargin(14, 14))
			[
				SNew(STextBlock).Text(TText(EmptyMsg)).Font(TFont(12.f)).ColorAndOpacity(TextTertiary).AutoWrapText(true)
			]
		];
		return;
	}

	for (int32 Idx = 0; Idx < Filtered.Num(); ++Idx)
	{
		const FColdSteelItem& Item = *Filtered[Idx];
		const FString InstanceId = Item.InstanceId;
		const FSmartTurretWeaponStats PreviewStats = AVillageSmartTurret::ComputeWeaponStats(Item, GI, Ranks);
		const FString Name = ColdSteelInventory::Text(Item, TEXT("name"));
		const int32 Enhance = FMath::Max(0, int32(ColdSteelInventory::Number(Item, TEXT("enhanceLevel"), 0.0)));
		const FString Archetype = AVillageSmartTurret::WeaponArchetypeLabel(Item.Definition);
		const bool bCompartment = (Item.Place == ColdSteelInventory::ColdSteelCompartment::Place);
		const FSlateBrush* IconBrush = ResolveWeaponIconBrush(Item);
		const float DpsDelta = bHasMounted ? (PreviewStats.EstimatedDPS - MountedStats.EstimatedDPS) : 0.f;

		TSharedRef<SWidget> Thumb = IconBrush
			? StaticCastSharedRef<SWidget>(SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SImage).Image(IconBrush)])
			: StaticCastSharedRef<SWidget>(SNew(STextBlock).Text(TText(*Archetype)).Font(TFont(10.5f)).ColorAndOpacity(TextTertiary));

		CandidateScroll->AddSlot().Padding(0, Idx == 0 ? 0.f : 7.f, 0, 0)
		[
			SNew(SBorder).BorderImage(&StatNormalBrush()).Padding(FMargin(11, 8))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 10, 0)
				[
					SNew(SBox).WidthOverride(72.f).HeightOverride(42.f)
					[
						SNew(SBorder).BorderImage(&IconWellBrush()).Padding(FMargin(3))
						.HAlign(HAlign_Center).VAlign(VAlign_Center)
						[Thumb]
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 0, 10, 0)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
						[
							SNew(STextBlock).Text(TText(Name)).Font(TFont(14.f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)
							.OverflowPolicy(ETextOverflowPolicy::Ellipsis)
						]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6, 0, 0, 0)
						[
							SNew(SBorder).BorderImage(&PillGoldBrush()).Padding(FMargin(5, 1))
							.Visibility(Enhance > 0 ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
							[
								SNew(STextBlock).Text(TText(FString::Printf(TEXT("+%d"), Enhance))).Font(TFont(10.f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)
							]
						]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6, 0, 0, 0)
						[
							SNew(SBorder).BorderImage(&PillDarkBrush()).Padding(FMargin(5, 1))
							[
								SNew(STextBlock).Text(TText(Archetype)).Font(TFont(10.f)).ColorAndOpacity(TextSecondary)
							]
						]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(5, 0, 0, 0)
						[
							SNew(SBorder).BorderImage(&PillMutedBrush()).Padding(FMargin(5, 1))
							.Visibility(bCompartment ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
							[
								SNew(STextBlock).Text(TText(TEXT("夹层"))).Font(TFont(10.f)).ColorAndOpacity(TextSecondary)
							]
						]
						+ SHorizontalBox::Slot().FillWidth(1)[SNew(SSpacer)]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6, 0, 0, 0)
						[
							SNew(STextBlock)
							.Visibility(bHasMounted && FMath::Abs(DpsDelta) >= 1.f ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
							.Text(TText(DpsDelta > 0.f ? FString::Printf(TEXT("+%.0f DPS"), DpsDelta) : FString::Printf(TEXT("%.0f DPS"), DpsDelta)))
							.Font(TFont(11.f, ETextWeight::SemiBold))
							.ColorAndOpacity(DpsDelta >= 0.f ? Success : Danger)
						]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 3, 0, 0)
					[
						SNew(STextBlock).Text(TText(FormatCandidateStatsLine(PreviewStats)))
						.Font(TFont(11.5f)).ColorAndOpacity(TextSecondary)
						.OverflowPolicy(ETextOverflowPolicy::Ellipsis)
					]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(SBox).MinDesiredWidth(72.f).HeightOverride(28.f)
					[
						SNew(SButton).ButtonStyle(&ColdSteelMarketCard::PurchaseStyle())
						.HAlign(HAlign_Center).VAlign(VAlign_Center).ContentPadding(FMargin(10, 0))
						.OnClicked_Lambda([this, InstanceId]()
						{
							if (!bClosing) OnMount.ExecuteIfBound(InstanceId);
							return FReply::Handled();
						})
						[
							SNew(STextBlock).Text(TText(bHasMounted ? TEXT("替换") : TEXT("装载"))).Font(TFont(12.5f)).ColorAndOpacity(HUDGoldLight)
						]
					]
				]
			]
		];
	}
}
