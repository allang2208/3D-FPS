#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "WeaponGripProfile.generated.h"

class UAnimSequence;

// Sparse local-space corrections. A key is translation delta, quaternion delta,
// scale delta (10 floats). Constant tracks need one key; identity tracks are absent.
USTRUCT()
struct FWeaponGripTrack
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, Category="Grip") FName Bone;
    UPROPERTY(VisibleAnywhere, Category="Grip") TArray<float> Times;
    UPROPERTY(VisibleAnywhere, Category="Grip") TArray<float> Values;
    FTransform Sample(float Time) const;
};

USTRUCT()
struct FWeaponGripClip
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, Category="Grip") TObjectPtr<UAnimSequence> Base;
    UPROPERTY(VisibleAnywhere, Category="Grip") float Duration=0.f;
    UPROPERTY(VisibleAnywhere, Category="Grip") TArray<FWeaponGripTrack> Tracks;
    void ApplyLocal(FName Bone,float Time,FTransform& Local) const;
    // Different skeletons or source durations retain their authored sequence.
    UPROPERTY(VisibleAnywhere, Category="Grip") TObjectPtr<UAnimSequence> Retained;
    UAnimSequence* Playback() const {return Retained?Retained.Get():Base.Get();}
};

// Shared pose/motion differences reference common base animations; incompatible
// authoring clips remain explicit runtime dependencies through Retained.
UCLASS(BlueprintType)
class FPSGAME_API UWeaponGripProfile : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, Category="Grip") FName Family;
    UPROPERTY(VisibleAnywhere, Category="Grip") TArray<FWeaponGripClip> Clips;
    const FWeaponGripClip* Find(const UAnimSequence* Base) const;
    const FWeaponGripClip* FindAction(FName Action) const;

    // Offline production API used by the background import script.
    UFUNCTION(BlueprintCallable, Category="Grip|Authoring")
    bool BakeClip(UAnimSequence* Base, UAnimSequence* Authored);
    UFUNCTION(BlueprintCallable, Category="Grip|Authoring")
    void KeepClip(UAnimSequence* Base,UAnimSequence* Authored);
    // Background production of shared clips whose sparse deltas were authored
    // outside Unreal. VisibleAnywhere track fields stay read-only to game logic.
    UFUNCTION(BlueprintCallable, Category="Grip|Authoring")
    bool SetSharedClipsFromJson(const FString& Json);
};
