#include "WeaponWeatherStateComponent.h"
#include "FPSGAMECharacter.h"
#include "FPSWeatherManager.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "Weapons/WoodenTorchItem.h"
#include "Multiplayer/ColdSteelAuthorityContext.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"

UWeaponWeatherStateComponent::UWeaponWeatherStateComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=.1f;
}

void UWeaponWeatherStateComponent::BeginPlay()
{
    Super::BeginPlay();
    SetComponentTickEnabled(GetOwner()->HasAuthority());
}

void UWeaponWeatherStateComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UWeaponWeatherStateComponent,Snapshot);
}

float UWeaponWeatherStateComponent::GetWetness(uint8 Hand,const FString& Instance) const
{
    if(Instance.IsEmpty())return 0.f;
    if(Hand==1)return Instance==Snapshot.OffhandInstance?Snapshot.OffhandWetness/255.f:0.f;
    return Instance==Snapshot.MainInstance?Snapshot.MainWetness/255.f:0.f;
}

void UWeaponWeatherStateComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority())return;
    WeatherSearchLeft-=Delta;
    if(!Weather.IsValid()&&WeatherSearchLeft<=0.f)
    {
        WeatherSearchLeft=1.f;
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It)
        {Weather=*It;AddTickPrerequisiteActor(*It);break;}
    }
    FWeaponWeatherSnapshot Next;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* Held=Profile?Profile->Equipped():nullptr;
    const auto* Main=Tool?Tool:Held;
    const auto* Off=Profile&&!Tool?Profile->Equipped(Profile->ActiveOffhandSlot()):nullptr;
    const bool HasTorch=(Main&&ColdSteelInventory::IsWoodenTorch(*Main))||(Off&&ColdSteelInventory::IsWoodenTorch(*Off));
    if(Main)Next.MainInstance=Main->InstanceId;
    else if(Pawn->HasInventoryWeapon())Next.MainInstance=Pawn->bUseM4Infima?TEXT("PreviewM4"):TEXT("PreviewAKM");
    if(Off)Next.OffhandInstance=Off->InstanceId;

    if(Weather.IsValid()&&(!Next.MainInstance.IsEmpty()||!Next.OffhandInstance.IsEmpty()))
    {
        ShelterCheckLeft-=Delta;
        if(HasTorch)Next.TorchBurnRate=Snapshot.TorchBurnRate;
        if(ShelterCheckLeft<=0.f || (HasTorch&&(Next.MainInstance!=Snapshot.MainInstance||Next.OffhandInstance!=Snapshot.OffhandInstance)))
        {
            ShelterCheckLeft=.25f;
            // Native UDW query includes this actor's local weather and shelter;
            // no listen-host camera state is shared with other players.
            if(!Weather->SampleActorRain(Pawn,ExposedRainTarget))
            {
                ExposedRainTarget=0.f;
                const float Rain=Weather->GetEffectiveRainIntensity();
                if(Rain>0.f)
                {
                    const FVector Eye=Pawn->GetPawnViewLocation();
                    const FVector Wind=Weather->GetWeatherWind();
                    const FVector Upwind=FVector(-Wind.X,-Wind.Y,1800.f).GetSafeNormal()*3000.f;
                    const FVector Offsets[]={FVector::ZeroVector,FVector(18,0,0),FVector(-18,0,0),FVector(0,18,0),FVector(0,-18,0)};
                    FCollisionQueryParams Params(SCENE_QUERY_STAT(WeaponWeatherShelter),false,Pawn);
                    int32 Open=0;
                    for(const auto& Offset:Offsets)
                        Open+=!GetWorld()->LineTraceTestByChannel(Eye+Offset,Eye+Offset+Upwind,ECC_Visibility,Params);
                    ExposedRainTarget=Rain*Open/UE_ARRAY_COUNT(Offsets);
                }
            }
            Next.TorchBurnRate=1;
            if(HasTorch&&ExposedRainTarget>0.f)
            {
                const auto State=Weather->CurrentState;
                const int32 Rate=State==EFPSWeatherState::Storm?3:
                    ((State==EFPSWeatherState::Rain||State==EFPSWeatherState::LightRain)?2:1);
                if(Rate>1&&!UDungeonRoomSubsystem::IsDungeonPawn(Pawn))
                {
                    const FVector Eye=Pawn->GetPawnViewLocation();
                    const FCollisionQueryParams Params(SCENE_QUERY_STAT(TorchRoof),false,Pawn);
                    if(!GetWorld()->LineTraceTestByChannel(Eye,Eye+FVector(0,0,3000),ECC_Visibility,Params))
                        Next.TorchBurnRate=Rate;
                }
            }
        }
    }
    else {ShelterCheckLeft=0.f;ExposedRainTarget=0.f;}
    ExposedRain=FMath::Lerp(ExposedRain,ExposedRainTarget,1.f-FMath::Exp(-Delta*4.f));
    for(auto It=ItemWetness.CreateIterator();It;++It)
    {
        It.Value()=FMath::Max(0.f,It.Value()-Delta/120.f);
        if(It.Value()<=0.f&&It.Key()!=Next.MainInstance&&It.Key()!=Next.OffhandInstance)It.RemoveCurrent();
    }
    const auto WetItem=[&](const FString& Instance)
    {
        if(Instance.IsEmpty())return uint8(0);
        float& Value=ItemWetness.FindOrAdd(Instance);
        Value=FMath::Clamp(Value+Delta*ExposedRain*.065f,0.f,1.f);
        return static_cast<uint8>(FMath::RoundToInt(Value*255.f));
    };
    Next.MainWetness=WetItem(Next.MainInstance);
    Next.OffhandWetness=Next.OffhandInstance==Next.MainInstance?Next.MainWetness:WetItem(Next.OffhandInstance);
    const bool IdentityChanged=Next.MainInstance!=Snapshot.MainInstance||Next.OffhandInstance!=Snapshot.OffhandInstance;
    Snapshot=MoveTemp(Next);
    // Continuous wetness uses the pawn's normal replication cadence. Only an
    // equipment edge asks for an immediate update; no extra per-frame RPC.
    if(IdentityChanged)Pawn->ForceNetUpdate();
}
