#include "../Monsters/MonsterCombatComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogSniperStun,Log,All);

namespace
{
double ServerTime(UWorld* World)
{
    const auto* State=World->GetGameState();
    return State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();
}
}

void UMonsterCombatComponent::ShowZhimingCritical(FVector Impact,float Seconds)
{
    // A quarter-second proc can finish before an idle monster's next replication update.
    GetOwner()->ForceNetUpdate();
    MulticastZhimingCritical(Impact,ServerTime(GetWorld()),Seconds);
}

void UMonsterCombatComponent::MulticastZhimingCritical_Implementation(FVector_NetQuantize Impact,double ServerAt,float Seconds)
{
    UWorld* World=GetWorld();
    if(!World||World->GetNetMode()==NM_DedicatedServer||Seconds<=0.f)return;
    const double EstimatedServerTime=ServerTime(World);
    const bool Remote=!GetOwner()->HasAuthority();
    float Age=0.f;
    if(Remote)
    {
        if(IsDead())return;
        // Clock smoothing during joins or frame stalls can exceed this short
        // proc. Its live reliable cue uses measured one-way latency instead.
        if(const auto* PC=World->GetFirstPlayerController())
            if(const auto* State=PC->GetPlayerState<APlayerState>())
                Age=FMath::Clamp(State->GetPingInMilliseconds()*.0005f,0.f,Seconds);
        if(Age>=Seconds)return;
        if(ServerAt+Seconds>=ObservedStunServerEnd)
        {
            const double Now=FPlatformTime::Seconds();
            const double End=Now+Seconds-Age;
            const bool AlreadyObserved=ObservedStunServerEnd==ServerAt+Seconds;
            ExplicitStunUntil=AlreadyObserved&&ExplicitStunUntil>Now?FMath::Min(ExplicitStunUntil,End):End;
            ObservedStunServerEnd=ServerAt+Seconds;
            NetStunEndsAt=ServerAt+Seconds;NetStunSeconds=Seconds;
            OnRep_StunEnd();
        }
    }
    UE_LOG(LogSniperStun,Verbose,TEXT("role=%d start=%.4f clock=%.4f transit=%.4f wall=%.4f receipt_clock=monotonic"),
        int32(World->GetNetMode()),ServerAt,EstimatedServerTime,Age,FPlatformTime::Seconds());
    // Network dispatch precedes UWorld's clock advance. Create the visual after
    // that advance so the previous frame's hitch cannot consume a new effect.
    const auto Present=[Owner=GetOwner(),Impact,Seconds,Transit=Age,ReceivedAt=FPlatformTime::Seconds()]()
    {
        UWorld* World=Owner->GetWorld();if(!World)return;
        const float Age=Transit+float(FPlatformTime::Seconds()-ReceivedAt);
        if(Age>=Seconds)return;
        static TWeakObjectPtr<UMaterialInterface> Cached;
        if(!Cached.IsValid())
            Cached=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/SniperZhiming/M_Zhiming_Critical"));
        if(!Cached.IsValid()||!Owner||!Owner->GetRootComponent())return;
        const auto Spawn=[&](const FVector& At,float HalfWidth,float HalfHeight,bool Spark)
        {
            auto* Card=NewObject<UMaterialBillboardComponent>(Owner);
            Card->SetupAttachment(Owner->GetRootComponent());
            Card->SetUsingAbsoluteScale(true);
            Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Card->SetCastShadow(false);
            auto* Mat=UMaterialInstanceDynamic::Create(Cached.Get(),Card);
            Mat->SetScalarParameterValue(TEXT("Start"),World->GetTimeSeconds()-Age);
            Mat->SetScalarParameterValue(TEXT("InvDuration"),1.f/Seconds);
            Mat->SetScalarParameterValue(TEXT("Spark"),Spark?1.f:0.f);
            Card->AddElement(Mat,nullptr,false,HalfWidth,HalfHeight,nullptr);
            Card->RegisterComponent();
            Card->SetWorldLocation(At);
            FTimerHandle Handle;
            World->GetTimerManager().SetTimer(Handle,FTimerDelegate::CreateWeakLambda(Card,[Card](){Card->DestroyComponent();}),Seconds-Age,false);
        };
        FVector Center,Extents;
        Owner->GetActorBounds(true,Center,Extents);
        const float Radius=FMath::Clamp(FMath::Max(Extents.X,Extents.Y)*1.16f,22.f,180.f);
        Spawn(Center+FVector::UpVector*(Extents.Z*.70f),Radius,Radius*.46f,false);
        if(Age<Seconds*.42f)Spawn(Impact,13.f,13.f,true);
    };
    if(Remote)World->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(GetOwner(),Present));
    else Present();
}
