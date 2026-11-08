// Replacement definitions for the existing local host; do not compile as a separate translation unit.
#include "FPSUDSBridgeComponent.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "Components/AudioComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "UObject/UnrealType.h"
#include "UObject/StructOnScope.h"

void UFPSUDSBridgeComponent::ApplyRainAudioGain(float Amount)
{
    auto* Actor=WeatherActor.Get();
    const bool Dungeon=UDungeonRoomSubsystem::IsDungeonPawn(UGameplayStatics::GetPlayerPawn(this,0));
    if(!Actor||!NativeRainVolume.IsValid()||!NativeSoundMaster.IsValid()||(!bRainAudioOverride&&Amount<=0.f&&!Dungeon))return;
    // UDW's periodic rain update sends intensity only. Submit the actual gain
    // parameter to both native sound sources, preserving authored/master volume.
    // Never write shared/replicated weather volume properties for a local duck.
    const float Base=WeatherAudio::Read(Actor,NativeRainVolume.Get())*WeatherAudio::Read(Actor,NativeSoundMaster.Get());
    const float Target=Dungeon?0.f:Base*(1.f-Amount*FMath::Clamp(ThunderRainReduction,0.f,1.f));
    if(!FMath::IsFinite(Target))return;
    auto* Global=WeatherAudio::Sound(Actor,NativeSoundGlobal.Get());
    auto* Directional=WeatherAudio::Sound(Actor,NativeSoundDirectional.Get());
    const bool Changed=!FMath::IsNearlyEqual(Target,LastRainVolume,.0001f);
    static const FName RainGain(TEXT("Rain Volume Multiplier"));
    if(Global&&(Changed||LastGlobalRainSound.Get()!=Global))Global->SetFloatParameter(RainGain,Target);
    if(Directional&&(Changed||LastDirectionalRainSound.Get()!=Directional))Directional->SetFloatParameter(RainGain,Target);
    LastGlobalRainSound=Global;LastDirectionalRainSound=Directional;LastRainVolume=Target;
    bRainAudioOverride=(Dungeon||Amount>0.f)&&(Global||Directional);
}
