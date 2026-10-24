#include "ApartmentAtmosphere.h"
#include "ApartmentDeviceControl.h"
#include "ColdSteelSlidingDoor.h"
#include "../FPSWeatherManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/LightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Sound/SoundAttenuation.h"
#include "TimerManager.h"

AApartmentAtmosphere::AApartmentAtmosphere()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("ApartmentRoot")));
    LivingReflectionBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("LivingReflectionBounds"));
    BathReflectionBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("BathReflectionBounds"));
    LivingReflections=CreateDefaultSubobject<UPostProcessComponent>(TEXT("LivingReflections"));
    BathReflections=CreateDefaultSubobject<UPostProcessComponent>(TEXT("BathReflections"));
    LivingReflectionBounds->SetupAttachment(RootComponent);
    BathReflectionBounds->SetupAttachment(RootComponent);
    LivingReflectionBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BathReflectionBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LivingReflectionBounds->SetRelativeLocation(FVector(1430,-490,200));
    LivingReflectionBounds->SetBoxExtent(FVector(690,490,240));
    BathReflectionBounds->SetRelativeLocation(FVector(705,-1910,200));
    BathReflectionBounds->SetBoxExtent(FVector(173,377,240));
    LivingReflections->SetupAttachment(LivingReflectionBounds);
    BathReflections->SetupAttachment(BathReflectionBounds);
    for(UPostProcessComponent* PP:{LivingReflections.Get(),BathReflections.Get()})
    {
        PP->bUnbound=false; PP->Priority=3.f; PP->BlendRadius=150.f;
        PP->Settings.bOverride_LumenReflectionQuality=true;
        PP->Settings.LumenReflectionQuality=2.f;
        PP->Settings.bOverride_LumenRayLightingMode=true;
        PP->Settings.LumenRayLightingMode=ELumenRayLightingModeOverride::HitLightingForReflections;
        PP->Settings.bOverride_LumenFrontLayerTranslucencyReflections=true;
        PP->Settings.LumenFrontLayerTranslucencyReflections=true;
        PP->Settings.bOverride_LumenMaxReflectionBounces=true;
        PP->Settings.LumenMaxReflectionBounces=1;
    }
}

UAudioComponent* AApartmentAtmosphere::MakeAudio(USoundBase* Sound,const FVector& Location,bool bSpatial)
{
    if(!Sound)return nullptr;
    auto* Audio=NewObject<UAudioComponent>(this);
    Audio->bAutoActivate=false;Audio->bAutoDestroy=false;Audio->SetSound(Sound);
    Audio->SetupAttachment(RootComponent);Audio->SetWorldLocation(Location);
    Audio->bAllowSpatialization=bSpatial;Audio->bOverrideAttenuation=bSpatial;
    if(bSpatial)
    {
        Audio->AttenuationOverrides.bAttenuate=true;
        Audio->AttenuationOverrides.bSpatialize=true;
        Audio->AttenuationOverrides.AttenuationShapeExtents=FVector(70);
        Audio->AttenuationOverrides.FalloffDistance=450.f;
    }
    Audio->SetVolumeMultiplier(0.f);Audio->RegisterComponent();Audio->Play();return Audio;
}

void AApartmentAtmosphere::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer){SetActorTickEnabled(false);return;}
    auto BindMaterials=[](AActor* Actor,FName Parameter,TArray<TObjectPtr<UMaterialInstanceDynamic>>& Out)
    {
        if(!IsValid(Actor))return;
        TArray<AActor*> Parts{Actor};Actor->GetAttachedActors(Parts,false,true);
        for(auto* Part:Parts)
        {
            TInlineComponentArray<UStaticMeshComponent*> Meshes(Part);
            for(auto* Mesh:Meshes)for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
            {
                float Value=0.f;auto* Material=Mesh->GetMaterial(Slot);
                if(auto* Existing=Cast<UMaterialInstanceDynamic>(Material);Existing&&Out.Contains(Existing))continue;
                if(Material&&Material->GetScalarParameterValue(FMaterialParameterInfo(Parameter),Value))
                    if(auto* MID=Mesh->CreateDynamicMaterialInstance(Slot))Out.Add(MID);
            }
        }
    };
    for(auto& Device:Devices)
    {
        BindMaterials(Device.Station,TEXT("DeviceActive"),Device.Materials);
        for(const auto& Part:Device.MaterialActors)BindMaterials(Part.Get(),TEXT("DeviceActive"),Device.Materials);
        BindMaterials(Device.Control,TEXT("DeviceActive"),Device.Materials);
        Device.RotorBases.Reset();
        for(const auto& Rotor:Device.Rotors)Device.RotorBases.Add(IsValid(Rotor)?Rotor->GetActorQuat():FQuat::Identity);
        DeviceAudio.Add(IsValid(Device.Station)?MakeAudio(DeviceSound,Device.Station->GetActorLocation()+FVector(0,0,45),true):nullptr);
    }
    for(auto& Binding:Lights)if(IsValid(Binding.Actor))
    {
        Binding.Component=Binding.Actor->FindComponentByClass<ULightComponent>();
        if(Binding.Component){Binding.OriginalIntensity=Binding.Component->Intensity;Binding.bOriginalVisible=Binding.Component->IsVisible();}
        Binding.LastWanted=GetWorld()->GetTimeSeconds();
        for(const auto& Fixture:Binding.Fixtures)BindMaterials(Fixture.Get(),TEXT("FixtureLevel"),Binding.Materials);
    }
    LastPresentationTime=GetWorld()->GetTimeSeconds();
    for(const auto& Window:Windows)BindMaterials(Window.Get(),TEXT("WindowRain"),WindowMaterials);
    InteriorAudio=MakeAudio(InteriorSound,GetActorLocation(),false);
    HarborAudio=MakeAudio(HarborSound,GetActorLocation(),false);
    UpdatePresentation();
    GetWorldTimerManager().SetTimer(PresentationTimer,this,&AApartmentAtmosphere::UpdatePresentation,.25f,true);
}

int32 AApartmentAtmosphere::FindRoom(const FVector& Eye) const
{
    int32 Best=INDEX_NONE;double Distance=10000.;
    for(int32 I=0;I<Rooms.Num();++I)
    {
        const double D=FBox(Rooms[I].Minimum,Rooms[I].Maximum).ComputeSquaredDistanceToPoint(Eye);
        if(D<Distance){Distance=D;Best=I;}
    }
    return Best;
}

void AApartmentAtmosphere::UpdateRoomLights(float Night,float Delta)
{
    // The dungeon's conservative room/portal policy, using this fixed map's
    // authored cells. Each local view contributes; remote peers do not get culled.
    TArray<bool> Wanted;Wanted.Init(false,Rooms.Num());bool bHasRoomView=false,bKeepAll=Rooms.IsEmpty();
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();if(!PC||!PC->IsLocalController()||!PC->GetLocalPlayer())continue;
        FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);const int32 Current=FindRoom(Eye);
        if(Current==INDEX_NONE){bKeepAll=true;continue;}
        bHasRoomView=true;Wanted[Current]=true;
        TArray<int32> Depth;Depth.Init(MAX_int32,Rooms.Num());Depth[Current]=0;
        TArray<int32> Queue;Queue.Add(Current);
        for(int32 Head=0;Head<Queue.Num();++Head)
        {
            const int32 Room=Queue[Head];
            for(const auto& Portal:Portals)
            {
                const int32 Next=Portal.RoomA==Room?Portal.RoomB:Portal.RoomB==Room?Portal.RoomA:INDEX_NONE;
                if(!Rooms.IsValidIndex(Next)||Depth[Next]<=Depth[Room]+1)continue;
                const bool bNear=FVector::DistSquared(Eye,Portal.Center)<FMath::Square(250.f);
                if(Portal.Door&&Portal.Door->GetOpenFraction()<.025f&&!bNear)continue;
                bool bVisible=Depth[Room]==0||bNear;
                if(!bVisible)
                {
                    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(ApartmentPortal),false,PC->GetPawn());
                    if(Portal.Door)Q.AddIgnoredActor(Portal.Door);
                    bVisible=!GetWorld()->LineTraceSingleByChannel(Hit,Eye,Portal.Center,ECC_Visibility,Q);
                }
                if(bVisible){Wanted[Next]=true;Depth[Next]=Depth[Room]+1;Queue.Add(Next);}
            }
        }
    }
    bKeepAll|=!bHasRoomView;const double Now=GetWorld()->GetTimeSeconds();
    for(auto& Binding:Lights)if(IsValid(Binding.Component))
    {
        const int32 Room=Binding.RoomIndex;
        const bool bWanted=bKeepAll||!Rooms.IsValidIndex(Room)||Rooms[Room].bKeepLit||Wanted[Room];
        if(bWanted)Binding.LastWanted=Now;
        const float Target=(bWanted||Now-Binding.LastWanted<2.2)?1.f:0.f;
        Binding.Relevance=FMath::Lerp(Binding.Relevance,Target,1.f-FMath::Exp(-Delta*(Target>0?5.f:2.f)));
        if(FMath::IsNearlyEqual(Binding.Relevance,Target,.005f))Binding.Relevance=Target;
        const float Factor=FMath::Lerp(Binding.DayFactor,Binding.NightFactor,Night)*Binding.Relevance;
        if(FMath::Abs(Factor-Binding.LastFactor)>.001f||Factor==0.f&&Binding.LastFactor!=0.f)
        {
            Binding.Component->SetIntensity(Binding.BaseIntensity*Factor);
            const bool bVisible=Factor>.0001f&&Binding.bOriginalVisible;
            if(Binding.Component->IsVisible()!=bVisible)Binding.Component->SetVisibility(bVisible);
            for(const auto& Material:Binding.Materials)if(Material)Material->SetScalarParameterValue(TEXT("FixtureLevel"),Factor);
            Binding.LastFactor=Factor;
        }
    }
}

float AApartmentAtmosphere::RoomSoundTransmission(int32 Room) const
{
    if(!Rooms.IsValidIndex(Room)||!Rooms.IsValidIndex(HarborRoomIndex))return 1.f;
    TArray<float> Transmission;Transmission.Init(0.f,Rooms.Num());Transmission[HarborRoomIndex]=1.f;
    for(int32 Pass=0;Pass<Rooms.Num();++Pass)
    {
        bool bChanged=false;
        for(const auto& Portal:Portals)
        {
            if(!Rooms.IsValidIndex(Portal.RoomA)||!Rooms.IsValidIndex(Portal.RoomB))continue;
            const float Through=Portal.Door?FMath::Lerp(.12f,.86f,Portal.Door->GetOpenFraction()):.92f;
            for(int32 Side=0;Side<2;++Side)
            {
                const int32 A=Side?Portal.RoomA:Portal.RoomB,B=Side?Portal.RoomB:Portal.RoomA;
                const float Value=Transmission[A]*Through;
                if(Value>Transmission[B]+.001f){Transmission[B]=Value;bChanged=true;}
            }
        }
        if(!bChanged)break;
    }
    return FMath::Max(.06f,Transmission[Room]);
}

void AApartmentAtmosphere::UpdatePresentation()
{
    const double Now=GetWorld()->GetTimeSeconds();
    const float Delta=FMath::Clamp(float(Now-LastPresentationTime),.001f,.5f);LastPresentationTime=Now;
    if(AnimationClock)if(const auto* GS=GetWorld()->GetGameState())
        if(auto* Collection=GetWorld()->GetParameterCollectionInstance(AnimationClock))
            Collection->SetScalarParameterValue(TEXT("ServerTimeOffset"),GS->GetServerWorldTimeSeconds()-float(Now));
    if(!Weather.IsValid())
    {
        BindRetryLeft-=Delta;
        if(BindRetryLeft<=0.f){for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){Weather=*It;break;}BindRetryLeft=2.f;}
    }
    const float Hour=Weather.IsValid()?Weather->NormalizedDayTime*24.f:9.f;
    const float Night=1.f-FMath::SmoothStep(5.5f,7.f,Hour)*(1.f-FMath::SmoothStep(17.f,19.f,Hour));
    UpdateRoomLights(Night,Delta);LastNight=Night;
    const float Rain=Weather.IsValid()?FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f):0.f;
    if(FMath::Abs(LastRain-Rain)>.005f){for(const auto& MID:WindowMaterials)if(MID)MID->SetScalarParameterValue(TEXT("WindowRain"),Rain);LastRain=Rain;}
    auto* PC=UGameplayStatics::GetPlayerController(this,0);if(!PC||!PC->PlayerCameraManager)return;
    const FVector Eye=PC->PlayerCameraManager->GetCameraLocation();
    const float Outside=FMath::SmoothStep<float>(FacadeY+10.f,FacadeY+150.f,float(Eye.Y));
    const float Open=BalconyDoor?BalconyDoor->GetOpenFraction():0.f;
    const float NearDoor=BalconyDoor?1.f-FMath::Clamp(float(FVector::Distance(Eye,BalconyDoor->GetActorLocation()+FVector(0,0,140)))/1400.f,0.f,1.f):0.f;
    const float Inside=FMath::Lerp(.06f,.55f,Open)*FMath::Lerp(.35f,1.f,NearDoor)*RoomSoundTransmission(FindRoom(Eye));
    const float Exposure=FMath::Lerp(Inside,1.f,Outside);
    const float Smooth=LastHarborExposure<0?Exposure:FMath::FInterpTo(LastHarborExposure,Exposure,Delta,3.f);
    if(FMath::Abs(Smooth-LastHarborExposure)>.001f||FMath::Abs(Outside-LastOutside)>.001f)
    {
        if(InteriorAudio)InteriorAudio->SetVolumeMultiplier(FMath::Lerp(.16f,.035f,Outside));
        if(HarborAudio){HarborAudio->SetVolumeMultiplier(FMath::Lerp(.012f,.24f,Smooth));HarborAudio->SetLowPassFilterEnabled(true);HarborAudio->SetLowPassFilterFrequency(FMath::Lerp(550.f,9000.f,Smooth));}
        LastHarborExposure=Smooth;LastOutside=Outside;
    }
    bool bNeedsAnimation=false;
    for(int32 Index=0;Index<Devices.Num();++Index)
    {
        auto& Device=Devices[Index];if(!IsValid(Device.Station))continue;
        const FVector Centre=Device.Control?Device.Control->GetActorLocation():Device.Station->GetActorLocation()+FVector(0,0,90);
        const float Distance=FVector::Distance(Eye,Centre);bool bNear=Distance<Device.WakeRadius;
        if(bNear)
        {
            FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(ApartmentDeviceWake),false,PC->GetPawn());
            Params.AddIgnoredActor(Device.Station);if(Device.Control)Params.AddIgnoredActor(Device.Control);
            for(const auto& Part:Device.MaterialActors)if(Part)Params.AddIgnoredActor(Part.Get());
            bNear=!GetWorld()->LineTraceSingleByChannel(Hit,Eye,Centre,ECC_Visibility,Params);
        }
        const bool bPowered=Device.Control?Device.Control->IsPowered():bNear;
        const float Target=bPowered?(bNear?1.f:Device.bWorkout?0.f:.12f):0.f;
        Device.Activity=FMath::FInterpTo(Device.Activity,Target,Delta,3.2f);
        if(FMath::IsNearlyEqual(Device.Activity,Target,.005f))Device.Activity=Target;
        if(Device.Control)Device.Control->SetPresentationActive(bPowered&&bNear);
        const float Power=bPowered?1.f:0.f;
        if(Device.Control)
        {
            Device.Elapsed=Device.Control->GetPoweredSeconds();Device.Phase=FMath::Fmod(Device.Elapsed,1000.f);
            for(const auto& MID:Device.Materials)if(MID)
            {MID->SetScalarParameterValue(TEXT("DevicePhase"),Device.Phase);if(Device.bWorkout)MID->SetScalarParameterValue(TEXT("DeviceElapsed"),Device.Elapsed);}
        }
        else if(Device.LastPower!=Power&&Power>0.f){Device.Elapsed=0.f;Device.Phase=0.f;}
        if(FMath::Abs(Device.LastMaterialActivity-Device.Activity)>.001f||Device.LastPower!=Power)
        {
            for(const auto& MID:Device.Materials)if(MID)
            {
                MID->SetScalarParameterValue(TEXT("DeviceActive"),Device.Activity);
                MID->SetScalarParameterValue(TEXT("DevicePower"),Power);
            }
            if(DeviceAudio.IsValidIndex(Index)&&DeviceAudio[Index])DeviceAudio[Index]->SetVolumeMultiplier((Device.bWorkout?.07f:.035f)*Device.Activity);
            Device.LastMaterialActivity=Device.Activity;Device.LastPower=Power;
        }
        Device.bAnimate=Device.Activity>.005f&&Distance<FMath::Max(Device.WakeRadius,900.f)
            &&(bNear||FMath::Abs(Device.Activity-Target)>.01f);
        bNeedsAnimation|=Device.bAnimate;
    }
    SetActorTickEnabled(bNeedsAnimation);
}

void AApartmentAtmosphere::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    for(auto& Device:Devices)if(Device.bAnimate)
    {
        const float Motion=Device.bWorkout?Device.Activity:FMath::Max(.08f,Device.Activity);
        if(Device.Control)
        {Device.Elapsed=Device.Control->GetPoweredSeconds();Device.Phase=FMath::Fmod(Device.Elapsed,1000.f);}
        else
        {Device.Phase=FMath::Fmod(Device.Phase+DeltaSeconds*Motion,1000.f);if(Device.LastPower>.5f&&Device.Activity>.8f)Device.Elapsed+=DeltaSeconds;}
        for(const auto& MID:Device.Materials)if(MID)
        {
            MID->SetScalarParameterValue(TEXT("DevicePhase"),Device.Phase);
            if(Device.bWorkout)MID->SetScalarParameterValue(TEXT("DeviceElapsed"),Device.Elapsed);
        }
        for(int32 I=0;I<Device.Rotors.Num();++I)if(IsValid(Device.Rotors[I])&&Device.RotorBases.IsValidIndex(I))
            Device.Rotors[I]->SetActorRotation(Device.RotorBases[I]*FRotator(FMath::Fmod(120.f*Device.Phase,360.f),0,0).Quaternion());
    }
}

void AApartmentAtmosphere::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(PresentationTimer);
    for(auto& Binding:Lights)if(IsValid(Binding.Component))
    {Binding.Component->SetIntensity(Binding.OriginalIntensity);Binding.Component->SetVisibility(Binding.bOriginalVisible);}
    SetActorTickEnabled(false);
    for(const auto& Audio:DeviceAudio)if(Audio)Audio->Stop();
    if(InteriorAudio)InteriorAudio->Stop();if(HarborAudio)HarborAudio->Stop();
    Super::EndPlay(Reason);
}
