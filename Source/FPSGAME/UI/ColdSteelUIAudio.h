#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelUIAudio.generated.h"

class USoundBase;
class IInputProcessor;

namespace ColdSteelUIAudio
{
	/**
	 * Unified UI interaction feedback cues derived from the migrated gamedev button click asset
	 * (/Game/Audio/GamedevUI20261002/S_Button_Click).
	 */
	enum class ECue : uint8
	{
		/** Standard button / tab / dropdown / confirm click (1.0 volume, 1.0 pitch). */
		Button,
		/** Lighter crisp tick for selecting/picking slots, cards, map markers, wheel sectors, or sliders. */
		Slot,
		/** Slightly lower grounded confirmation when dropping/seating an item or skill into a slot. */
		SlotDrop
	};

	/** Plays a UI cue using the preloaded sound from UColdSteelUIAudioSubsystem (debounced). */
	FPSGAME_API void Play(const UObject* WorldContext, ECue Cue = ECue::Button);

	/** Plays a UI cue from pure Slate widgets that do not hold a UObject world context. */
	FPSGAME_API void PlayFromSlate(ECue Cue = ECue::Button);

	/**
	 * Entry point for legacy OnClicked PlayButtonClick() call sites: suppresses duplicate audio
	 * when the click was already played by the global Slate button input processor on press.
	 */
	FPSGAME_API void PlayLegacyButtonClick(const UObject* WorldContext);
}

/**
 * Preloads the migrated gamedev UI button click sound and registers a game-viewport-scoped Slate
 * input processor so every enabled SButton/UButton/SComboButton/UComboBoxString/SCheckBox/menu entry
 * across all Cold Steel, Workbench, Gunsmith, Map, Dialogue, Mount, Voxel, and Menu screens receives
 * consistent click feedback without leaking into Unreal Editor UI or double-playing.
 */
UCLASS()
class FPSGAME_API UColdSteelUIAudioSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	static constexpr const TCHAR* ButtonClickAssetPath = TEXT("/Game/Audio/GamedevUI20261002/S_Button_Click.S_Button_Click");

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	void PlayCue(ColdSteelUIAudio::ECue Cue);
	void PlayLegacyButtonClick();

	/** Returns the active subsystem matching the given world context, or nullptr. */
	static UColdSteelUIAudioSubsystem* FindForContext(const UObject* WorldContext);

	/** Returns the best active game-viewport subsystem for pure Slate widgets. */
	static UColdSteelUIAudioSubsystem* FindForSlate();

private:
	friend class FColdSteelUIAudioInputProcessor;

	USoundBase* ResolveClickSound();
	void NotifyProcessorButtonPressed();
	void NotifyProcessorButtonReleased();

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> ButtonClickSound;

	TSharedPtr<IInputProcessor> InputProcessor;

	double LastPlayTime = -100.0;
	double LastProcessorButtonPressTime = -100.0;
	double LastProcessorButtonReleaseTime = -100.0;
	bool bProcessorButtonHeld = false;
};
