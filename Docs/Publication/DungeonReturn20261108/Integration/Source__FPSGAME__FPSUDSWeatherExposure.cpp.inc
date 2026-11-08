// Replacement definitions for the existing local host; do not compile as a separate translation unit.
#include "FPSUDSBridgeComponent.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "GameFramework/Pawn.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "UObject/StructOnScope.h"
#include "UObject/UnrealType.h"

bool UFPSUDSBridgeComponent::SampleActorRain(AActor* Actor,float& ExposedRain)
{
    if(UDungeonRoomSubsystem::IsDungeonActor(Actor)||UDungeonRoomSubsystem::IsDungeonPawn(Cast<APawn>(Actor)))
    {ExposedRain=0.f;return true;}
    auto* Source=WeatherActor.Get();auto* Function=ActorWeatherFunction.Get();
    if(!IsBridgeEnabled()||!IsValid(Actor)||Actor->GetWorld()!=GetWorld()||!Source||!Source->HasActorBegunPlay()
        ||!Weather.IsValid()||!Weather->HasAuthority()||!Function||!ActorWeatherConstruct.IsValid())return false;
    auto* Construct=CastFieldChecked<FMulticastDelegateProperty>(ActorWeatherConstruct.Get());
    const auto* Delegate=Construct->GetMulticastDelegate(Construct->ContainerPtrToValuePtr<void>(Source));
    if(!Delegate||!Delegate->IsBound())return false;
    auto* Settings=CastFieldChecked<FObjectPropertyBase>(ActorWeatherSettings.Get());
    if(!ActorWeatherSample)ActorWeatherSample=NewObject<UObject>(this,Settings->PropertyClass,NAME_None,RF_Transient);
    if(!ActorWeatherSample)return false;
    // Match UDW's local-state seed, but never replace its camera-local object.
    auto* Direction=CastFieldChecked<FNumericProperty>(ActorWindDirection.Get());
    Direction->SetFloatingPointPropertyValue(Direction->ContainerPtrToValuePtr<void>(ActorWeatherSample),
        ActorWeather::Read(Source,WeatherBaseDirection.Get()));
    if(auto* Changing=CastField<FBoolProperty>(ActorWeatherSample->GetClass()->FindPropertyByName(TEXT("Changing"))))
        Changing->SetPropertyValue_InContainer(ActorWeatherSample,false);
    FStructOnScope Parameters(Function);auto* Data=Parameters.GetStructMemory();
    *CastFieldChecked<FStructProperty>(ActorWeatherLocation.Get())->ContainerPtrToValuePtr<FVector>(Data)=Actor->GetActorLocation();
    Settings->SetObjectPropertyValue_InContainer(Data,ActorWeatherSample);
    Source->ProcessEvent(Function,Data);
    const double Rain=ActorWeather::Read(ActorWeatherSample,ActorRain.Get());
    const double Wind=ActorWeather::Read(ActorWeatherSample,ActorWindIntensity.Get());
    const double Yaw=ActorWeather::Read(ActorWeatherSample,ActorWindDirection.Get());
    if(!FMath::IsFinite(Rain)||!FMath::IsFinite(Wind)||!FMath::IsFinite(Yaw))return false;
    ExposedRain=0.f;if(Rain<=0.)return true;
    auto* Sky=SkyActor.Get();
    auto* DistanceProperty=Sky?ActorWeather::Number(Sky->GetClass(),TEXT("Occlusion Max Trace Distance")):nullptr;
    if(!DistanceProperty)return false;
    const double Distance=ActorWeather::Read(Sky,DistanceProperty);
    if(!FMath::IsFinite(Distance)||Distance<=0.)return false;
    FVector Origin,Extent;
    if(auto* Root=Actor->GetRootComponent()){Origin=Root->Bounds.Origin;Extent=Root->Bounds.BoxExtent;}
    else Actor->GetActorBounds(true,Origin,Extent);
    // UDW 9.7 General Weather Particle Direction + the six precipitation
    // samples from Trace Bounds for Exposure Values. Wind-only rays are unused.
    const FVector RainVelocity=FRotator(0.,Yaw,0.).RotateVector(FVector(.7*FMath::Pow(FMath::Max(0.,Wind)/10.,2.5),0.,0.))
        +FVector(0.,0.,-.66);
    const FVector Upwind=-RainVelocity.GetSafeNormal();
    const FVector Offsets[]={FVector(.95,0,0),FVector(0,.95,0),FVector(-.95,0,0),FVector(0,-.95,0),FVector(0,0,.8),FVector(0,0,-.8)};
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WeaponActorWeather),false,Actor);Query.AddIgnoredActor(Source);
    int32 Open=0;
    for(const FVector& Offset:Offsets)
    {
        const FVector Start=Origin+Extent*Offset;
        Open+=!GetWorld()->LineTraceTestByChannel(Start,Start+(Upwind+Offset*.2)*Distance,ECC_Visibility,Query);
    }
    ExposedRain=FMath::Clamp(static_cast<float>(Rain/10.),0.f,1.f)*Open/UE_ARRAY_COUNT(Offsets);
    return true;
}
