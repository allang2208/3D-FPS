#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"

namespace
{
TSharedPtr<FJsonObject> BodyObject(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{
    const TSharedPtr<FJsonObject>* Value=nullptr;
    return Parent&&Parent->TryGetObjectField(Key,Value)?*Value:nullptr;
}
FName BodyName(const TSharedPtr<FJsonObject>& Object,const TCHAR* Key)
{
    FString Value;if(Object)Object->TryGetStringField(Key,Value);return FName(*Value);
}
}

void UFPSPlayerBodyComponent::InitializeBodyConfigurations()
{
    BaseBodyConfiguration=Configuration;
    BodyConfigurations.Reset();
    BodyConfigurations.Add(TEXT("jason"),BaseBodyConfiguration);
    if(const auto Variants=BodyObject(BaseBodyConfiguration,TEXT("body_variants")))
        for(const auto& Entry:Variants->Values)
        {
            const TSharedPtr<FJsonObject>* Override=nullptr;
            if(!Entry.Value->TryGetObject(Override))continue;
            // Only published, fully authored variants can be selected. No male
            // animation or equipment fallbacks are copied into a female body.
            bool Ready=false;(*Override)->TryGetBoolField(TEXT("ready"),Ready);
            if(!Ready||!BodyObject(*Override,TEXT("clips"))||!BodyObject(*Override,TEXT("heads")))continue;
            BodyConfigurations.Add(FName(*Entry.Key),*Override);
        }
}

TSharedPtr<FJsonObject> UFPSPlayerBodyComponent::ConfigurationForHead(FName HeadId) const
{
    for(const auto& Entry:BodyConfigurations)
        if(const auto Heads=BodyObject(Entry.Value,TEXT("heads"));Heads&&Heads->HasField(HeadId.ToString()))return Entry.Value;
    return BaseBodyConfiguration.IsValid()?BaseBodyConfiguration:Configuration;
}

FName UFPSPlayerBodyComponent::GetBodyType() const
{
    for(const auto& Entry:BodyConfigurations)if(Entry.Value==Configuration)return Entry.Key;
    return TEXT("jason");
}

bool UFPSPlayerBodyComponent::CanUseBodyType(FName BodyId) const
{
    return Character.IsValid()&&Character->IsLocallyControlled()&&BodyConfigurations.Contains(BodyId)
        &&!AppearanceLoad.IsValid()&&!IsDeathViewActive();
}

bool UFPSPlayerBodyComponent::SetBodyType(FName BodyId)
{
    if(!CanUseBodyType(BodyId))return false;
    const auto* Config=BodyConfigurations.Find(BodyId);if(!Config)return false;
    const FName HeadId=BodyName(*Config,TEXT("default_head"));
    const auto Heads=BodyObject(*Config,TEXT("heads"));
    const TSharedPtr<FJsonObject>* Head=nullptr;
    if(!Heads||!Heads->TryGetObjectField(HeadId.ToString(),Head))return false;
    return SetHeadAndHair(HeadId,BodyName(*Head,TEXT("default_hair")));
}

void UFPSPlayerBodyComponent::InitializeFurnitureCamera()
{
    FurnitureEyeTracks.Reset();
    const auto Tracks=BodyObject(Configuration,TEXT("furniture_camera_tracks"));if(!Tracks)return;
    const auto Clips=BodyObject(Configuration,TEXT("clips"));if(!Clips)return;
    for(const auto& Pair:Tracks->Values)
    {
        const auto Track=Pair.Value->AsObject();if(!Track)continue;
        FString AuthoredAnimation,ActiveAnimation;
        if(Track->TryGetStringField(TEXT("animation"),AuthoredAnimation)&&
            (!Clips->TryGetStringField(Pair.Key,ActiveAnimation)||AuthoredAnimation!=ActiveAnimation))continue;
        double Duration=0.;const TArray<TSharedPtr<FJsonValue>>* Samples=nullptr;
        if(!Track->TryGetNumberField(TEXT("duration"),Duration)||Duration<=0.||
           !Track->TryGetArrayField(TEXT("eyes"),Samples)||Samples->Num()<2)continue;
        FFurnitureEyeTrack Data;Data.Duration=Duration;
        for(const auto& Value:*Samples)
        {
            const auto& XYZ=Value->AsArray();if(XYZ.Num()!=3){Data.Eyes.Reset();break;}
            Data.Eyes.Add(FVector(XYZ[0]->AsNumber(),XYZ[1]->AsNumber(),XYZ[2]->AsNumber()));
        }
        if(Data.Eyes.Num()>=2)FurnitureEyeTracks.Add(FName(*Pair.Key),MoveTemp(Data));
    }
}

bool UFPSPlayerBodyComponent::SampleFurnitureEye(FName Clip,float Seconds,FVector& Eye) const
{
    const auto* Track=FurnitureEyeTracks.Find(Clip);if(!Track)return false;
    const float Frame=FMath::Clamp(Seconds/Track->Duration,0.f,1.f)*(Track->Eyes.Num()-1);
    const int32 A=FMath::Min(FMath::FloorToInt(Frame),Track->Eyes.Num()-2);
    Eye=FMath::Lerp(Track->Eyes[A],Track->Eyes[A+1],Frame-A);return true;
}
