#include "FPSUDSBridgeComponent.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "Components/AudioComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "UObject/UnrealType.h"
#include "UObject/StructOnScope.h"

namespace WeatherAudio
{
FProperty* Number(UObject* Object,const TCHAR* Name)
{
    auto* P=Object?CastField<FNumericProperty>(Object->GetClass()->FindPropertyByName(FName(Name))):nullptr;
    return P&&P->IsFloatingPoint()?P:nullptr;
}
float Read(UObject* Object,FProperty* Property)
{
    auto* N=CastField<FNumericProperty>(Property);
    return Object&&N?static_cast<float>(N->GetFloatingPointPropertyValue(N->ContainerPtrToValuePtr<void>(Object))):0.f;
}
void Write(UObject* Object,FProperty* Property,float Value)
{
    if(auto* N=CastField<FNumericProperty>(Property);Object&&N)
        N->SetFloatingPointPropertyValue(N->ContainerPtrToValuePtr<void>(Object),Value);
}
FProperty* SoundProperty(UObject* Object,const TCHAR* Name)
{
    auto* P=CastField<FObjectPropertyBase>(Object->GetClass()->FindPropertyByName(Name));
    return P&&P->PropertyClass->IsChildOf(UAudioComponent::StaticClass())?P:nullptr;
}
UAudioComponent* Sound(UObject* Object,FProperty* Property)
{
    auto* P=CastField<FObjectPropertyBase>(Property);
    return Object&&P?Cast<UAudioComponent>(P->GetObjectPropertyValue_InContainer(Object)):nullptr;
}
bool Enabled(UObject* Object,FProperty* Property)
{
    auto* P=CastField<FBoolProperty>(Property);
    return Object&&P&&P->GetPropertyValue_InContainer(Object);
}
}

void UFPSUDSBridgeComponent::ConfigureWeatherAudio()
{
    auto* Actor=WeatherActor.Get();
    if(bWeatherAudioConfigured||!Actor||!Actor->HasActorBegunPlay()||GetNetMode()==NM_DedicatedServer)return;
    NativeRainVolume=WeatherAudio::Number(Actor,TEXT("Rain Volume"));
    NativeSoundMaster=WeatherAudio::Number(Actor,TEXT("Weather Sounds Master Volume"));
    NativeSoundGlobal=WeatherAudio::SoundProperty(Actor,TEXT("Sound_Global"));
    NativeSoundDirectional=WeatherAudio::SoundProperty(Actor,TEXT("Sound_Directional"));
    NativeSoundEnabled=CastField<FBoolProperty>(Actor->GetClass()->FindPropertyByName(TEXT("Enable Weather Sound Effects")));
    NativeFlashActive=CastField<FBoolProperty>(Actor->GetClass()->FindPropertyByName(TEXT("Lightning Flash Active")));
    NativeThunderDelay=WeatherAudio::Number(Actor,TEXT("Close Thunder Delay Per KM"));
    auto* Location=CastField<FStructProperty>(Actor->GetClass()->FindPropertyByName(TEXT("Current Lightning Location")));
    if(Location&&Location->Struct==TBaseStructure<FVector>::Get())NativeLightningLocation=Location;
    auto* Event=CastField<FMulticastDelegateProperty>(Actor->GetClass()->FindPropertyByName(TEXT("Lightning Flash Started")));
    if(!NativeRainVolume.IsValid()||!NativeSoundMaster.IsValid()||!NativeSoundGlobal.IsValid()||!NativeSoundDirectional.IsValid()
        ||!NativeSoundEnabled.IsValid()||!NativeFlashActive.IsValid()||!NativeThunderDelay.IsValid()||!Event||Event->SignatureFunction->NumParms!=0)
    {
        // Report once per binding; do not invent a second lightning timer/player.
        bWeatherAudioConfigured=true;
        UE_LOG(LogTemp,Warning,TEXT("UDSBridge: native thunder mix interface unavailable; preserving authored audio"));
        return;
    }
    LastRainVolume=-1.f;bRainAudioOverride=false;
    OriginalThunderDelay=WeatherAudio::Read(Actor,NativeThunderDelay.Get());
    if(auto* Function=Actor->FindFunction(TEXT("Close Thunder Sound Delay"));Function&&Function->NumParms==1)
        for(TFieldIterator<FProperty> P(Function);P;++P)
            if(auto* N=CastField<FNumericProperty>(*P);N&&N->IsFloatingPoint()&&P->HasAnyPropertyFlags(CPF_OutParm|CPF_ReturnParm))
            {NativeThunderDelayFunction=Function;NativeThunderDelayResult=*P;}
    // Upgrade the vendor default only. Authored map delays remain intentional.
    bOwnThunderDelay=FMath::IsNearlyEqual(OriginalThunderDelay,.15f,.0001f);
    if(bOwnThunderDelay)WeatherAudio::Write(Actor,NativeThunderDelay.Get(),CloseThunderSecondsPerKm);
    FScriptDelegate Delegate;Delegate.BindUFunction(this,GET_FUNCTION_NAME_CHECKED(ThisClass,OnLightningFlashStarted));
    Event->AddDelegate(Delegate,Actor);NativeFlashEvent=Event;bWeatherAudioConfigured=true;
}

void UFPSUDSBridgeComponent::OnLightningFlashStarted()
{
    auto* Actor=WeatherActor.Get();
    if(!Actor||GetNetMode()==NM_DedicatedServer||!NativeFlashEvent.IsValid())return;
    // UDW broadcasts even if Start Lightning Flash found no valid position.
    // Do not duck rain for an aborted flash or muted close-thunder playback.
    if(!WeatherAudio::Enabled(Actor,NativeFlashActive.Get())||!WeatherAudio::Enabled(Actor,NativeSoundEnabled.Get())
        ||WeatherAudio::Read(Actor,NativeSoundMaster.Get())<=0.f
        ||WeatherAudio::Read(Actor,WeatherAudio::Number(Actor,TEXT("Close Thunder Volume")))<=0.f)return;
    float Delay=0.f;
    if(auto* Function=NativeThunderDelayFunction.Get();Function&&NativeThunderDelayResult.IsValid())
    {
        FStructOnScope Parameters(Function);Actor->ProcessEvent(Function,Parameters.GetStructMemory());
        auto* P=CastFieldChecked<FNumericProperty>(NativeThunderDelayResult.Get());
        const double Value=P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Parameters.GetStructMemory()));
        if(FMath::IsFinite(Value))Delay=FMath::Max(0.f,static_cast<float>(Value));
    }
    else if(auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0))
        if(auto* P=CastField<FStructProperty>(NativeLightningLocation.Get()))
        {
            const FVector Position=*P->ContainerPtrToValuePtr<FVector>(Actor);
            if(!Position.ContainsNaN())Delay=FVector::Distance(Position,Camera->GetCameraLocation())/100000.f
                *WeatherAudio::Read(Actor,NativeThunderDelay.Get());
        }
    const double Now=GetWorld()->GetTimeSeconds();
    ThunderDuckWindows.RemoveAll([Now](const auto& Window){return Window.Y<Now;});
    // Keep the native MetaSound delay and use a short pre-roll for its gain ramp.
    const double Start=Now+FMath::Max(0.f,Delay-.5f),End=Now+Delay+5.f;
    if(ThunderDuckWindows.Num()<4)ThunderDuckWindows.Emplace(Start,End);
    else {auto& Window=ThunderDuckWindows.Last();Window.X=FMath::Min(Window.X,Start);Window.Y=FMath::Max(Window.Y,End);}
}

void UFPSUDSBridgeComponent::UpdateWeatherAudio(float Delta)
{
    if(!bWeatherAudioConfigured)ConfigureWeatherAudio();
    auto* Actor=WeatherActor.Get();
    if(!Actor||!NativeFlashEvent.IsValid()||!NativeRainVolume.IsValid())return;
    const double Now=GetWorld()->GetTimeSeconds();
    ThunderDuckWindows.RemoveAll([Now](const auto& Window){return Window.Y<Now;});
    float Amount=0.f;
    for(const auto& Window:ThunderDuckWindows)
    {
        const float Attack=FMath::Clamp(static_cast<float>((Now-Window.X)/.2),0.f,1.f);
        const float Release=FMath::Clamp(static_cast<float>((Window.Y-Now)/2.),0.f,1.f);
        Amount=FMath::Max(Amount,Attack*Release);
    }
    if(!WeatherAudio::Enabled(Actor,NativeSoundEnabled.Get())){ThunderDuckWindows.Reset();Amount=0.f;}
    ApplyRainAudioGain(Amount);
}

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

void UFPSUDSBridgeComponent::RestoreWeatherAudio()
{
    if(auto* Actor=WeatherActor.Get();Actor&&bWeatherAudioConfigured&&NativeFlashEvent.IsValid())
    {
        ApplyRainAudioGain(0.f);
        FScriptDelegate Delegate;Delegate.BindUFunction(this,GET_FUNCTION_NAME_CHECKED(ThisClass,OnLightningFlashStarted));
        if(auto* Event=CastField<FMulticastDelegateProperty>(NativeFlashEvent.Get()))Event->RemoveDelegate(Delegate,Actor);
        if(bOwnThunderDelay&&FMath::IsNearlyEqual(WeatherAudio::Read(Actor,NativeThunderDelay.Get()),CloseThunderSecondsPerKm,.0001f))
            WeatherAudio::Write(Actor,NativeThunderDelay.Get(),OriginalThunderDelay);
    }
    bWeatherAudioConfigured=false;bOwnThunderDelay=false;bRainAudioOverride=false;ThunderDuckWindows.Reset();
    NativeRainVolume.Reset();NativeThunderDelay.Reset();NativeLightningLocation.Reset();NativeFlashEvent.Reset();
    NativeThunderDelayFunction.Reset();NativeThunderDelayResult.Reset();
    NativeSoundMaster.Reset();NativeSoundGlobal.Reset();NativeSoundDirectional.Reset();NativeSoundEnabled.Reset();NativeFlashActive.Reset();
    LastGlobalRainSound.Reset();LastDirectionalRainSound.Reset();LastRainVolume=-1.f;
}
