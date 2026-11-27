#include "ColdSteelUIAudio.h"

#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/IInputProcessor.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Input/Events.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Layout/WidgetPath.h"
#include "Sound/SoundBase.h"
#include "Widgets/SViewport.h"
#include "Widgets/SWidget.h"
#include "Widgets/SWindow.h"

namespace
{
	constexpr double MinCueIntervalSeconds = 0.045;
	constexpr double LegacyDedupWindowSeconds = 0.12;

	TArray<TWeakObjectPtr<UColdSteelUIAudioSubsystem>> GActiveUIAudioSubsystems;

	bool IsButtonWidgetType(FName Type)
	{
		static const FName NameSButton(TEXT("SButton"));
		static const FName NameSCommonButton(TEXT("SCommonButton"));
		static const FName NameSExpeditionButton(TEXT("SExpeditionButton"));
		static const FName NameSComboButton(TEXT("SComboButton"));
		static const FName NameSComboBox(TEXT("SComboBox"));
		static const FName NameSCheckBox(TEXT("SCheckBox"));
		static const FName NameSMenuEntryBlock(TEXT("SMenuEntryBlock"));
		return Type == NameSButton
			|| Type == NameSCommonButton
			|| Type == NameSExpeditionButton
			|| Type == NameSComboButton
			|| Type == NameSComboBox
			|| Type == NameSCheckBox
			|| Type == NameSMenuEntryBlock;
	}

	bool IsMenuRowWidgetType(FName Type)
	{
		static const FName NameSComboRow(TEXT("SComboRow"));
		static const FName NameSTableRow(TEXT("STableRow"));
		return Type == NameSComboRow || Type == NameSTableRow;
	}

	bool IsSliderWidgetType(FName Type)
	{
		static const FName NameSSlider(TEXT("SSlider"));
		return Type == NameSSlider;
	}

	bool ArePathWidgetsInteractive(const FWidgetPath& Path, int32 StartIndex, int32 EndIndex)
	{
		for (int32 Index = StartIndex; Index <= EndIndex; ++Index)
		{
			const TSharedRef<SWidget>& Widget = Path.Widgets[Index].Widget;
			if (!Widget->IsEnabled() || !Widget->GetVisibility().IsVisible())
			{
				return false;
			}
		}
		return true;
	}

	int32 FindWidgetIndexInPath(const FWidgetPath& Path, const SWidget* Target)
	{
		if (!Target)
		{
			return INDEX_NONE;
		}
		for (int32 Index = 0; Index < Path.Widgets.Num(); ++Index)
		{
			if (&Path.Widgets[Index].Widget.Get() == Target)
			{
				return Index;
			}
		}
		return INDEX_NONE;
	}
}

class FColdSteelUIAudioInputProcessor final : public IInputProcessor
{
public:
	explicit FColdSteelUIAudioInputProcessor(UColdSteelUIAudioSubsystem* InOwner)
		: Owner(InOwner)
	{
	}

	virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override
	{
		if (bGameMenuOpenedFromViewport)
		{
			if (SlateApp.AnyMenusVisible())
			{
				bSawVisibleMenu = true;
			}
			else if (bSawVisibleMenu || !IsPointerInteractiveInGame(Owner.Get(), SlateApp))
			{
				bGameMenuOpenedFromViewport = false;
				bSawVisibleMenu = false;
			}
		}
	}

	virtual bool HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override
	{
		HandlePointerPress(SlateApp, MouseEvent);
		return false;
	}

	virtual bool HandleMouseButtonDoubleClickEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override
	{
		HandlePointerPress(SlateApp, MouseEvent);
		return false;
	}

	virtual bool HandleMouseButtonUpEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override
	{
		if (MouseEvent.GetEffectingButton() == EKeys::LeftMouseButton)
		{
			if (UColdSteelUIAudioSubsystem* Subsystem = Owner.Get())
			{
				Subsystem->NotifyProcessorButtonReleased();
			}
		}
		return false;
	}

	virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override
	{
		if (InKeyEvent.IsRepeat())
		{
			return false;
		}

		const FKey Key = InKeyEvent.GetKey();
		if (Key != EKeys::Enter && Key != EKeys::SpaceBar && Key != EKeys::Virtual_Accept)
		{
			return false;
		}

		UColdSteelUIAudioSubsystem* Subsystem = Owner.Get();
		if (!Subsystem || !IsPointerInteractiveInGame(Subsystem, SlateApp))
		{
			return false;
		}

		TSharedPtr<SWidget> GameViewportWidget = ResolveGameViewportWidget(Subsystem);
		if (!GameViewportWidget.IsValid())
		{
			return false;
		}

		const TSharedPtr<SWidget> Focused = SlateApp.GetUserFocusedWidget(InKeyEvent.GetUserIndex());
		if (!Focused.IsValid() || !IsButtonWidgetType(Focused->GetType())
			|| !Focused->IsEnabled() || !Focused->GetVisibility().IsHitTestVisible())
		{
			return false;
		}

		FWidgetPath FocusPath;
		if (!SlateApp.FindPathToWidget(Focused.ToSharedRef(), FocusPath))
		{
			return false;
		}

		const int32 ViewportIndex = FindWidgetIndexInPath(FocusPath, GameViewportWidget.Get());
		if (ViewportIndex == INDEX_NONE)
		{
			return false;
		}

		if (!ArePathWidgetsInteractive(FocusPath, ViewportIndex, FocusPath.Widgets.Num() - 1))
		{
			return false;
		}

		Subsystem->NotifyProcessorButtonPressed();
		Subsystem->PlayCue(ColdSteelUIAudio::ECue::Button);
		return false;
	}

	virtual const TCHAR* GetDebugName() const override
	{
		return TEXT("ColdSteelUIAudioInputProcessor");
	}

private:
	static bool IsPointerInteractiveInGame(const UColdSteelUIAudioSubsystem* Subsystem, FSlateApplication& SlateApp)
	{
		if (SlateApp.AnyMenusVisible())
		{
			return true;
		}
		const UGameInstance* GameInstance = Subsystem ? Subsystem->GetGameInstance() : nullptr;
		const UWorld* World = GameInstance ? GameInstance->GetWorld() : nullptr;
		if (!World)
		{
			return true;
		}
		const APlayerController* PlayerController = GameInstance->GetFirstLocalPlayerController(World);
		return !PlayerController || PlayerController->ShouldShowMouseCursor();
	}

	static TSharedPtr<SWidget> ResolveGameViewportWidget(const UColdSteelUIAudioSubsystem* Subsystem)
	{
		const UGameInstance* GameInstance = Subsystem ? Subsystem->GetGameInstance() : nullptr;
		const UGameViewportClient* ViewportClient = GameInstance ? GameInstance->GetGameViewportClient() : nullptr;
		if (!ViewportClient)
		{
			return nullptr;
		}
		return ViewportClient->GetGameViewportWidget();
	}

	void HandlePointerPress(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
	{
		UColdSteelUIAudioSubsystem* Subsystem = Owner.Get();
		if (!Subsystem)
		{
			return;
		}

		const bool bLeftButton = MouseEvent.GetEffectingButton() == EKeys::LeftMouseButton;
		// O(1) fast path during cursor-less FPS combat: avoid Slate widget tree traversal on gunshots/aim clicks.
		if (!bGameMenuOpenedFromViewport)
		{
			if (!bLeftButton || !IsPointerInteractiveInGame(Subsystem, SlateApp))
			{
				return;
			}
		}

		const TSharedPtr<SWidget> GameViewportWidget = ResolveGameViewportWidget(Subsystem);
		if (!GameViewportWidget.IsValid())
		{
			return;
		}

		const FWidgetPath Path = SlateApp.LocateWindowUnderMouse(
			MouseEvent.GetScreenSpacePosition(),
			SlateApp.GetInteractiveTopLevelWindows(),
			/*bIgnoreEnabledStatus=*/ false,
			MouseEvent.GetUserIndex());

		if (!Path.IsValid())
		{
			bGameMenuOpenedFromViewport = false;
			bSawVisibleMenu = false;
			return;
		}

		const int32 ViewportIndex = FindWidgetIndexInPath(Path, GameViewportWidget.Get());
		const bool bInGameViewport = ViewportIndex != INDEX_NONE;
		const bool bIsMenuWindow = Path.GetWindow()->GetType() == EWindowType::Menu;

		if (bInGameViewport)
		{
			// Any pointer press inside the game viewport authorizes subsequent popup dropdown menus
			// (such as UComboBoxString / SComboButton) opened from this viewport.
			bGameMenuOpenedFromViewport = true;
			bSawVisibleMenu = false;
		}
		else if (!bIsMenuWindow)
		{
			// Clicking outside the game viewport (for example, Unreal Editor panels or Editor menus)
			// immediately revokes popup menu authorization so Editor dropdowns never trigger game audio.
			bGameMenuOpenedFromViewport = false;
			bSawVisibleMenu = false;
			return;
		}
		else if (GIsEditor && !bGameMenuOpenedFromViewport)
		{
			return;
		}

		if (!bLeftButton)
		{
			return;
		}

		const int32 RootIndex = bInGameViewport ? ViewportIndex : 0;
		for (int32 Index = Path.Widgets.Num() - 1; Index >= RootIndex; --Index)
		{
			const TSharedRef<SWidget>& Widget = Path.Widgets[Index].Widget;
			const FName WidgetType = Widget->GetType();

			if (IsButtonWidgetType(WidgetType))
			{
				if (!Widget->GetVisibility().IsHitTestVisible())
				{
					continue;
				}
				if (ArePathWidgetsInteractive(Path, RootIndex, Index))
				{
					Subsystem->NotifyProcessorButtonPressed();
					Subsystem->PlayCue(ColdSteelUIAudio::ECue::Button);
				}
				return;
			}

			if (bIsMenuWindow && IsMenuRowWidgetType(WidgetType))
			{
				if (ArePathWidgetsInteractive(Path, RootIndex, Index))
				{
					Subsystem->NotifyProcessorButtonPressed();
					Subsystem->PlayCue(ColdSteelUIAudio::ECue::Button);
				}
				return;
			}

			if (bInGameViewport && IsSliderWidgetType(WidgetType))
			{
				if (ArePathWidgetsInteractive(Path, RootIndex, Index))
				{
					Subsystem->PlayCue(ColdSteelUIAudio::ECue::Slot);
				}
				return;
			}
		}
	}

	TWeakObjectPtr<UColdSteelUIAudioSubsystem> Owner;
	bool bGameMenuOpenedFromViewport = false;
	bool bSawVisibleMenu = false;
};

bool UColdSteelUIAudioSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (IsRunningCommandlet() || IsRunningDedicatedServer())
	{
		return false;
	}
	if (const UGameInstance* GameInstance = Cast<UGameInstance>(Outer))
	{
		if (GameInstance->IsDedicatedServerInstance())
		{
			return false;
		}
	}
	return true;
}

void UColdSteelUIAudioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	GActiveUIAudioSubsystems.RemoveAll([](const TWeakObjectPtr<UColdSteelUIAudioSubsystem>& Entry) { return !Entry.IsValid(); });
	GActiveUIAudioSubsystems.AddUnique(this);

	ResolveClickSound();

	if (FSlateApplication::IsInitialized())
	{
		InputProcessor = MakeShared<FColdSteelUIAudioInputProcessor>(this);
		FSlateApplication::Get().RegisterInputPreProcessor(InputProcessor);
	}
}

void UColdSteelUIAudioSubsystem::Deinitialize()
{
	if (InputProcessor.IsValid())
	{
		if (FSlateApplication::IsInitialized())
		{
			FSlateApplication::Get().UnregisterInputPreProcessor(InputProcessor);
		}
		InputProcessor.Reset();
	}

	GActiveUIAudioSubsystems.RemoveAll([this](const TWeakObjectPtr<UColdSteelUIAudioSubsystem>& Entry)
	{
		return !Entry.IsValid() || Entry.Get() == this;
	});

	ButtonClickSound = nullptr;
	Super::Deinitialize();
}

USoundBase* UColdSteelUIAudioSubsystem::ResolveClickSound()
{
	if (!ButtonClickSound)
	{
		ButtonClickSound = LoadObject<USoundBase>(nullptr, ButtonClickAssetPath);
	}
	return ButtonClickSound;
}

void UColdSteelUIAudioSubsystem::NotifyProcessorButtonPressed()
{
	LastProcessorButtonPressTime = FPlatformTime::Seconds();
	bProcessorButtonHeld = true;
}

void UColdSteelUIAudioSubsystem::NotifyProcessorButtonReleased()
{
	if (bProcessorButtonHeld)
	{
		LastProcessorButtonReleaseTime = FPlatformTime::Seconds();
		bProcessorButtonHeld = false;
	}
}

void UColdSteelUIAudioSubsystem::PlayCue(ColdSteelUIAudio::ECue Cue)
{
	UGameInstance* GameInstance = GetGameInstance();
	UWorld* World = GameInstance ? GameInstance->GetWorld() : nullptr;
	if (!World || World->GetNetMode() == NM_DedicatedServer)
	{
		return;
	}

	const double Now = FPlatformTime::Seconds();
	if (Now - LastPlayTime < MinCueIntervalSeconds)
	{
		return;
	}

	USoundBase* Sound = ResolveClickSound();
	if (!Sound)
	{
		return;
	}

	float Volume = 1.0f;
	float Pitch = 1.0f;
	switch (Cue)
	{
	case ColdSteelUIAudio::ECue::Button:
		Volume = 1.0f;
		Pitch = 1.0f;
		break;
	case ColdSteelUIAudio::ECue::Slot:
		Volume = 0.78f;
		Pitch = FMath::FRandRange(1.06f, 1.12f);
		break;
	case ColdSteelUIAudio::ECue::SlotDrop:
		Volume = 0.85f;
		Pitch = FMath::FRandRange(0.92f, 0.97f);
		break;
	}

	LastPlayTime = Now;
	UGameplayStatics::PlaySound2D(World, Sound, Volume, Pitch, 0.0f, nullptr, nullptr, /*bIsUISound=*/ true);
}

void UColdSteelUIAudioSubsystem::PlayLegacyButtonClick()
{
	const double Now = FPlatformTime::Seconds();
	if (bProcessorButtonHeld
		|| (Now - LastProcessorButtonPressTime) < LegacyDedupWindowSeconds
		|| (Now - LastProcessorButtonReleaseTime) < LegacyDedupWindowSeconds)
	{
		return;
	}
	PlayCue(ColdSteelUIAudio::ECue::Button);
}

UColdSteelUIAudioSubsystem* UColdSteelUIAudioSubsystem::FindForContext(const UObject* WorldContext)
{
	if (WorldContext && GEngine)
	{
		if (UWorld* World = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull))
		{
			if (UGameInstance* GameInstance = World->GetGameInstance())
			{
				return GameInstance->GetSubsystem<UColdSteelUIAudioSubsystem>();
			}
		}
	}
	return FindForSlate();
}

UColdSteelUIAudioSubsystem* UColdSteelUIAudioSubsystem::FindForSlate()
{
	UColdSteelUIAudioSubsystem* Fallback = nullptr;
	const bool bHasSlate = FSlateApplication::IsInitialized();
	const FVector2D CursorPos = bHasSlate ? FSlateApplication::Get().GetCursorPos() : FVector2D::ZeroVector;

	for (int32 Index = GActiveUIAudioSubsystems.Num() - 1; Index >= 0; --Index)
	{
		UColdSteelUIAudioSubsystem* Candidate = GActiveUIAudioSubsystems[Index].Get();
		if (!Candidate)
		{
			GActiveUIAudioSubsystems.RemoveAtSwap(Index);
			continue;
		}

		const UGameInstance* GameInstance = Candidate->GetGameInstance();
		const UWorld* World = GameInstance ? GameInstance->GetWorld() : nullptr;
		if (!World || World->GetNetMode() == NM_DedicatedServer)
		{
			continue;
		}

		if (!Fallback)
		{
			Fallback = Candidate;
		}

		if (bHasSlate)
		{
			if (const UGameViewportClient* ViewportClient = GameInstance->GetGameViewportClient())
			{
				if (const TSharedPtr<SWidget> ViewportWidget = ViewportClient->GetGameViewportWidget();
					ViewportWidget.IsValid() && ViewportWidget->GetCachedGeometry().IsUnderLocation(CursorPos))
				{
					return Candidate;
				}
			}
		}
	}

	return Fallback;
}

namespace ColdSteelUIAudio
{
	void Play(const UObject* WorldContext, ECue Cue)
	{
		if (UColdSteelUIAudioSubsystem* Subsystem = UColdSteelUIAudioSubsystem::FindForContext(WorldContext))
		{
			Subsystem->PlayCue(Cue);
		}
	}

	void PlayFromSlate(ECue Cue)
	{
		if (UColdSteelUIAudioSubsystem* Subsystem = UColdSteelUIAudioSubsystem::FindForSlate())
		{
			Subsystem->PlayCue(Cue);
		}
	}

	void PlayLegacyButtonClick(const UObject* WorldContext)
	{
		if (UColdSteelUIAudioSubsystem* Subsystem = UColdSteelUIAudioSubsystem::FindForContext(WorldContext))
		{
			Subsystem->PlayLegacyButtonClick();
		}
	}
}
