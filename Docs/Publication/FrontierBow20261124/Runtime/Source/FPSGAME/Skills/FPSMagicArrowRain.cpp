#include "FPSMagicArrowRain.h"
#include "../Weapons/Bow/AuroraBeamVisual.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "../Combat/FPSAttackQuery.h"
#include "MagicArrowRainGround.h"
#include "BlizzardEnvironment.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInterface.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Net/UnrealNetwork.h"

AFPSMagicArrowRain::AFPSMagicArrowRain()
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetNetCullDistanceSquared(FMath::Square(15000.f));
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Arrows=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Arrows"));Arrows->SetupAttachment(RootComponent);
    Trails=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Trails"));Trails->SetupAttachment(RootComponent);
    for(auto* Mesh:{Arrows.Get(),Trails.Get()}){Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetCanEverAffectNavigation(false);}
}
double AFPSMagicArrowRain::Clock() const
{const auto* State=GetWorld()->GetGameState();return State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
void AFPSMagicArrowRain::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AFPSMagicArrowRain,Flight);DOREPLIFETIME(AFPSMagicArrowRain,bBlocked);}
void AFPSMagicArrowRain::BeginPlay()
{
    Super::BeginPlay();if(GetNetMode()==NM_DedicatedServer)return;
    Arrows->SetNumCustomDataFloats(1);
    TArray<FSoftObjectPath> Paths;for(const auto* Name:MagicArrowRainAssets::Names)Paths.Emplace(MagicArrowRainAssets::Path(Name));
    Paths.Emplace(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    Paths.Emplace(MagicArrowRainAssets::Path(TEXT("ATT_ArrowRain")));
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths]
    {
        for(const auto& Path:Paths)Assets.Add(Path.ResolveObject());
        Arrows->SetStaticMesh(Cast<UStaticMesh>(Paths[0].ResolveObject()));
        Arrows->SetMaterial(0,Cast<UMaterialInterface>(Paths[1].ResolveObject()));
        Trails->SetStaticMesh(Cast<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")).ResolveObject()));
        Trails->SetMaterial(0,Cast<UMaterialInterface>(FSoftObjectPath(MagicArrowRainAssets::Path(TEXT("M_ArrowRainTrailV4"))).ResolveObject()));
        bReady=Arrows->GetStaticMesh()&&Trails->GetStaticMesh();
        ApplyAuroraBeam();
    }));
}
void AFPSMagicArrowRain::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Laser.IsValid())Laser->Release();
    if(Load)Load->CancelHandle();
    StopDescentAudio();Super::EndPlay(Reason);
}
void AFPSMagicArrowRain::Launch(UColdSteelStatusModel* InModel,const FMagicArrowRainCast& InSpell,
    const FVector& Start,const FVector& Ground,const FVector& Burst)
{
    Model=InModel;Spell=InSpell;Flight.Start=Start;Flight.Ground=Ground;Flight.Burst=Burst;
    Flight.bAuroraBeam=GetInstigator()&&GetInstigator()->IsPlayerControlled()&&InModel&&ColdSteelBow::AuroraRiser(InModel,InModel->ActiveBow());
    Spell.EclipseShot = FEclipseBowShot::Capture(GetInstigator());
    Flight.StartedAt=Clock();Flight.FlightSeconds=FMath::Max(.12f,float(FVector::Dist(Start,Burst))/Spell.SeedSpeed);
    Flight.Radius=Spell.Radius;Flight.SurfaceNormal=Spell.SurfaceNormal;Flight.Count=Spell.ArrowCount;Flight.Seed=FMath::Rand();Flight.bLaunched=true;
    SetActorLocation(Ground);ApplyAuroraBeam();ForceNetUpdate();SetLifeSpan(Flight.FlightSeconds+2.4f);
}
void AFPSMagicArrowRain::ApplyAuroraBeam()
{
    if(!Flight.bAuroraBeam||!Flight.bLaunched||GetNetMode()==NM_DedicatedServer)return;
    Arrows->SetVisibility(false);Trails->SetVisibility(false);
    if(!Laser.IsValid())Laser=AAuroraBeamVisual::Open(this,Flight.Start);
    if(Laser.IsValid()&&Flight.AuroraBlock.At>=0.)
    {
        Laser->Finish(0,Flight.Start,Flight.StartedAt,Flight.AuroraBlock);
        Laser->Release();
    }
}
void AFPSMagicArrowRain::OnRep_Flight(){SetActorLocation(Flight.Ground);ApplyAuroraBeam();}
void AFPSMagicArrowRain::OnRep_Blocked(){Arrows->ClearInstances();Trails->ClearInstances();StopDescentAudio();ApplyAuroraBeam();}
void AFPSMagicArrowRain::MulticastBlockedImpact_Implementation(FVector_NetQuantize Point)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* Asset=Cast<UNiagaraSystem>(FSoftObjectPath(MagicArrowRainAssets::Path(TEXT("NS_ArrowRainDust"))).ResolveObject());
    if(Asset)if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,Asset,Point,FRotator::ZeroRotator,FVector::OneVector,true,false,ENCPoolMethod::AutoRelease))
    {
        FX->SetVariableFloat(TEXT("User.Count"),1.f);FX->SetVariableFloat(TEXT("User.Seed"),float(Flight.Seed%1000));
        FX->SetVariableFloat(TEXT("User.Elapsed"),0.f);FX->SetVariableFloat(TEXT("User.ImpactDelay0"),0.f);
        FX->SetVariableVec3(TEXT("User.ImpactNormal0"),FVector::UpVector);
        FX->SetVariableVec3(TEXT("User.Impact0"),FVector::ZeroVector);FX->Activate(true);
    }
    Sound(TEXT("S_ArrowRainImpact"),Point,.2f);
}
void AFPSMagicArrowRain::BuildRain()
{
    auto* Pawn=GetInstigator();if(!Pawn)return;
    bRainBuilt=true;
    FRandomStream Random(Flight.Seed);
    const int32 Count=FMath::Clamp(Flight.Count,0,MagicArrowRainTiming::MaxArrows);
    for(int32 I=0;I<Count;++I)
    {
        const float Angle=I*2.39996323f+Random.FRandRange(-.08f,.08f);
        const float Radius=Flight.Radius*FMath::Sqrt((I+.5f)/Count)*.96f;
        const FVector Offset(Radius*FMath::Cos(Angle),Radius*FMath::Sin(Angle),0);
        const FVector Start=Flight.Burst;FHitResult Block,Floor;
        const float SlopeZ=-FVector::DotProduct(Flight.SurfaceNormal,Offset)/FMath::Max(.45f,float(Flight.SurfaceNormal.Z));
        const float Drop=FMath::Max(1.f,float(Start.Z-Flight.Ground.Z)-SlopeZ+160.f);
        if(!BlizzardEnvironment::Floor(Pawn,Start+Offset,0.f,Drop,Floor))continue;
        const FVector IntendedEnd=Floor.ImpactPoint+Floor.ImpactNormal*2.f;
        FVector End=IntendedEnd,Normal=Floor.ImpactNormal;
        // Every arrow starts at the actual burst, not a disk floating above the target.
        // A wall on the diagonal route becomes the visible impact, never a teleport past it.
        if(BlizzardEnvironment::Trace(Pawn,Start,IntendedEnd,Block,true))
        {
            if(Block.bStartPenetrating)continue;
            Normal=Block.ImpactNormal;End=Block.ImpactPoint+Normal*2.f;
        }
        RainStarts.Add(Start);RainEnds.Add(End);RainNormals.Add(Normal.GetSafeNormal());
        const float TravelFraction=FMath::Clamp(float(FVector::Dist(Start,End)/FMath::Max(1.,FVector::Dist(Start,IntendedEnd))),0.f,1.f);
        TravelTimes.Add(FMath::Max(.01f,MagicArrowRainTiming::FallSeconds*TravelFraction));
        Delays.Add(MagicArrowRainTiming::LaunchDelay+Random.FRandRange(0.f,MagicArrowRainTiming::LaunchSpread));
    }
    BuildDescentAudio();
}
void AFPSMagicArrowRain::BuildDescentAudio()
{
    DescentCues.Reset();NextDescentCue=0;
    const int32 Count=FMath::Min(5,RainEnds.Num());if(!Count)return;
    // An independent stream keeps audio variation from changing arrow trajectories.
    FRandomStream Random(Flight.Seed^0x6EA2F13D);
    TArray<int32,TInlineAllocator<MagicArrowRainTiming::MaxArrows>> Order;
    float First=Delays[0],Last=First;
    for(int32 I=0;I<RainEnds.Num();++I)
    {Order.Add(I);First=FMath::Min(First,Delays[I]);Last=FMath::Max(Last,Delays[I]);}
    for(int32 I=Order.Num()-1;I>0;--I)Order.Swap(I,Random.RandRange(0,I));
    int32 Pitches[]={0,1,2,3,4};
    for(int32 I=4;I>0;--I)Swap(Pitches[I],Pitches[Random.RandRange(0,I)]);
    static constexpr float Pitch[]={.945f,.975f,1.f,1.025f,1.055f};
    static constexpr float Gain[]={.78f,.34f,.30f,.28f,.26f};
    for(int32 I=0;I<Count;++I)
    {
        auto& Cue=DescentCues.AddDefaulted_GetRef();
        const float T=Count>1?float(I)/(Count-1):0.f;
        Cue.Time=I==0?First:FMath::Clamp(FMath::Lerp(First,Last,T)+Random.FRandRange(-.007f,.007f),First,Last);
        Cue.Pitch=Pitch[Pitches[I]];Cue.Gain=Gain[I]*Random.FRandRange(.94f,1.04f);
        Cue.Point=FMath::Lerp(RainStarts[Order[I]],RainEnds[Order[I]],Random.FRandRange(.12f,.28f));
    }
    DescentCues.Sort([](const FDescentCue& A,const FDescentCue& B){return A.Time<B.Time;});
}
void AFPSMagicArrowRain::PlayDescentAudio(float BurstAge)
{
    if(NextDescentCue>=DescentCues.Num())return;
    // Ignore genuinely stale replication, but retain a live volley across normal
    // loading/frame hitches. The former 80 ms per-cue expiry could discard all five.
    if(BurstAge>MagicArrowRainTiming::DamageDelay+.5f)
    {NextDescentCue=DescentCues.Num();return;}
    auto* Wave=Cast<USoundBase>(FSoftObjectPath(MagicArrowRainAssets::Path(TEXT("S_ArrowRainBurst"))).ResolveObject());
    if(!Wave||Wave->HasAnyFlags(RF_NeedLoad|RF_NeedPostLoad)||BurstAge<DescentCues[NextDescentCue].Time)return;
    const auto Cue=DescentCues[NextDescentCue++];
    const float LateBy=BurstAge-Cue.Time;
    // Start one voice per frame; after a hitch move the remaining spacing forward
    // instead of consuming voices that were never played or dumping them together.
    if(LateBy>1.f/30.f)
        for(int32 I=NextDescentCue;I<DescentCues.Num();++I)DescentCues[I].Time+=LateBy;
    // The wave owns its descent-only attenuation. Do not override it with the
    // short-range ground-impact settings (almost silent at the 40 m cast limit).
    if(auto* Audio=UGameplayStatics::SpawnSoundAtLocation(this,Wave,Cue.Point,FRotator::ZeroRotator,
        Cue.Gain,Cue.Pitch,0.f,nullptr,nullptr,true))DescentAudio.Add(Audio);
}
void AFPSMagicArrowRain::StopDescentAudio()
{
    for(auto& Audio:DescentAudio)if(Audio.IsValid())Audio->Stop();
    DescentAudio.Reset();NextDescentCue=DescentCues.Num();
}
void AFPSMagicArrowRain::Smoke(bool Impact,float Elapsed)
{
    if(Impact&&RainEnds.IsEmpty())return;
    auto* Asset=Cast<UNiagaraSystem>(FSoftObjectPath(MagicArrowRainAssets::Path(Impact?TEXT("NS_ArrowRainDust"):TEXT("NS_ArrowRainBurst"))).ResolveObject());
    if(!Asset)return;
    const FVector Location=Impact?Flight.Ground:Flight.Burst;
    if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,Asset,Location,FRotator::ZeroRotator,FVector::OneVector,true,false,ENCPoolMethod::AutoRelease))
    {
        FX->SetVariableFloat(TEXT("User.Radius"),Flight.Radius);
        FX->SetVariableFloat(TEXT("User.Count"),float(RainEnds.Num()));
        FX->SetVariableFloat(TEXT("User.Seed"),float(Flight.Seed%1000));
        FX->SetVariableFloat(TEXT("User.Elapsed"),Elapsed);
        FBox ImpactBounds(ForceInit);
        for(int32 I=0;I<RainEnds.Num();++I)
        {
            const FVector Offset=RainEnds[I]-Location;
            FX->SetVariableVec3(FName(*FString::Printf(TEXT("User.Impact%d"),I)),Offset);ImpactBounds+=Offset;
            FX->SetVariableVec3(FName(*FString::Printf(TEXT("User.ImpactNormal%d"),I)),RainNormals[I]);
            FX->SetVariableFloat(FName(*FString::Printf(TEXT("User.ImpactDelay%d"),I)),Delays[I]+TravelTimes[I]);
        }
        // Downhill impacts can lie below the flat-ground system bounds.
        if(Impact&&ImpactBounds.IsValid)FX->SetSystemFixedBounds(ImpactBounds.ExpandBy(180.f));
        FX->Activate(true);
    }
}
void AFPSMagicArrowRain::Sound(const TCHAR* Name,const FVector& Point,float Volume)
{
    auto* Sound=Cast<USoundBase>(FSoftObjectPath(MagicArrowRainAssets::Path(Name)).ResolveObject());
    auto* Attenuation=Cast<USoundAttenuation>(FSoftObjectPath(MagicArrowRainAssets::Path(TEXT("ATT_ArrowRain"))).ResolveObject());
    if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound,Point,Volume,1.f,0.f,Attenuation);
}
void AFPSMagicArrowRain::Present(float Age)
{
    if(!bReady&&!Flight.bAuroraBeam)return;
    auto Arrow=[this](int32 Index,const FVector& Point,const FVector& Direction,float Scale,float HeadPulse=0.f)
    {
        const FTransform Transform(Direction.Rotation(),Point,FVector(Scale));
        if(Index>=Arrows->GetInstanceCount())Arrows->AddInstance(Transform,true);
        else Arrows->UpdateInstanceTransform(Index,Transform,true,false,true);
        Arrows->SetCustomDataValue(Index,0,HeadPulse,false);
    };
    auto Tail=[this](int32 Index,const FVector& Tip,const FVector& Direction,float Length,float Width)
    {
        const FTransform Transform(FRotationMatrix::MakeFromZ(Direction).ToQuat(),Tip-Direction*Length*.5f,FVector(Width/50.f,Width/50.f,Length/100.f));
        if(Index>=Trails->GetInstanceCount())Trails->AddInstance(Transform,true);
        else Trails->UpdateInstanceTransform(Index,Transform,true,false,true);
    };
    if(Age<Flight.FlightSeconds)
    {
        const float T=FMath::Clamp(Age/Flight.FlightSeconds,0.f,1.f);
        const FVector Point=MagicArrowRainGround::Flight(Flight.Start,Flight.Burst,T);
        const FVector Direction=(Flight.Burst-Flight.Start+FVector(0,0,60.f*PI*FMath::Cos(PI*T))).GetSafeNormal();
        if(Flight.bAuroraBeam)
        {
            if(Laser.IsValid())Laser->Trace(0,Flight.Start,Flight.StartedAt,Point,Flight.StartedAt+Age);
        }
        else {Arrow(0,Point,Direction,1.f);Tail(0,Point,Direction,100.f,1.1f);}
    }
    else
    {
        const float BurstAge=Age-Flight.FlightSeconds;
        if(!bRainBuilt)BuildRain();
        // Instigator may resolve after Flight on a remote actor channel.
        if(!bRainBuilt)return;
        if(!bBurstPlayed)
        {
            bBurstPlayed=true;Arrows->ClearInstances();Trails->ClearInstances();
            if(Laser.IsValid())
            {
                FAuroraBeamContact Burst;
                Burst.At=Flight.StartedAt+Flight.FlightSeconds;Burst.Point=Flight.Burst;
                Laser->Finish(0,Flight.Start,Flight.StartedAt,Burst);
            }
            if(BurstAge<.5f)Smoke(false,BurstAge);
            // One pooled system schedules every impact from the same arrow clock.
            // Late presentation receives elapsed time rather than replaying all contacts.
            if(BurstAge<1.4f)Smoke(true,BurstAge);
        }
        if(BurstAge>=MagicArrowRainTiming::DamageDelay&&!bImpactPlayed)
        {bImpactPlayed=true;if(!RainEnds.IsEmpty()&&BurstAge<MagicArrowRainTiming::DamageDelay+.2f)Sound(TEXT("S_ArrowRainImpact"),Flight.Ground,.8f);}
        for(int32 I=0;I<RainStarts.Num();++I)
        {
            const float Falling=BurstAge-Delays[I];const float T=FMath::Clamp(Falling/TravelTimes[I],0.f,1.f);
            const FVector Direction=(RainEnds[I]-RainStarts[I]).GetSafeNormal();
            const FVector Point=FMath::Lerp(RainStarts[I],RainEnds[I],T*T*.3f+T*.7f);
            const float ImpactAge=Falling-TravelTimes[I];
            if(Flight.bAuroraBeam)
            {
                if(Falling<0.f||!Laser.IsValid())continue;
                const double StartAt=Flight.StartedAt+Flight.FlightSeconds+Delays[I];
                if(ImpactAge<0.f)Laser->Trace(I+1,RainStarts[I],StartAt,Point,StartAt+Falling,.72f);
                else if(ImpactAge<.55f)
                {
                    FAuroraBeamContact Contact;
                    Contact.At=StartAt+TravelTimes[I];Contact.Point=RainEnds[I];Contact.Normal=RainNormals[I];
                    Laser->Finish(I+1,RainStarts[I],StartAt,Contact,.72f);
                }
                continue;
            }
            const float Fade=Falling<0.f?0.f:1.f-FMath::SmoothStep(.17f,.43f,ImpactAge);
            const float BirthPulse=1.f-FMath::SmoothStep(0.f,.085f,Falling);
            const float HeadPulse=Falling<0.f?0.f:(.68f+.32f*BirthPulse)*(1.f-FMath::SmoothStep(0.f,.07f,ImpactAge));
            Arrow(I,Point,Direction,.9f*Fade,HeadPulse);
            // The newborn trail reaches into the burst before stretching downward.
            const float TailLength=FMath::Min(300.f,float(FVector::Dist(Point,RainStarts[I]))+45.f);
            Tail(I,Point,Direction,ImpactAge>=0.f?0.f:TailLength*Fade,(2.6f+.6f*BirthPulse)*Fade);
        }
    }
    if(!Flight.bAuroraBeam){Arrows->MarkRenderStateDirty();Trails->MarkRenderStateDirty();}
}
void AFPSMagicArrowRain::Tick(float Delta)
{
    Super::Tick(Delta);if(!Flight.bLaunched||bBlocked||Flight.AuroraBlock.At>=0.)return;
    const float Age=FMath::Max(0.f,float(Clock()-Flight.StartedAt));
    if(HasAuthority())
    {
        const float Fraction=FMath::Clamp(Age/Flight.FlightSeconds,0.f,1.f);
        auto* Pawn=GetInstigator();
        for(float T=PreviousFraction;T<Fraction;)
        {
            const float Next=FMath::Min(T+.025f,Fraction);FHitResult Hit;
            FFPSAttackQuery Query(SCENE_QUERY_STAT(ArrowRainFlight),true,Pawn);Query.AddIgnoredActor(this);
            if(RangedAttackQuery::LineTraceSingle(GetWorld(),Pawn,Hit,
                MagicArrowRainGround::Flight(Flight.Start,Flight.Burst,T),MagicArrowRainGround::Flight(Flight.Start,Flight.Burst,Next),ECC_Visibility,Query))
            {
                if(Flight.bAuroraBeam)
                {
                    Flight.AuroraBlock.At=Flight.StartedAt+Flight.FlightSeconds*FMath::Lerp(T,Next,Hit.Time);
                    Flight.AuroraBlock.Point=Hit.ImpactPoint;Flight.AuroraBlock.Normal=Hit.ImpactNormal;
                }
                bBlocked=true;OnRep_Blocked();MulticastBlockedImpact(Hit.ImpactPoint);ForceNetUpdate();SetLifeSpan(.25f);return;
            }
            T=Next;
        }
        PreviousFraction=Fraction;
        if(!bDamageDone&&Age>=Flight.FlightSeconds+MagicArrowRainTiming::DamageDelay)
        {
            bDamageDone=true;
            if(Pawn&&Model.IsValid()){ColdSteelAuthority::FScope Context(Model.Get());Model->ApplyMagicArrowRain(Pawn,Flight.Ground,Flight.Burst,Spell);}
        }
    }
    if(GetNetMode()!=NM_DedicatedServer)
    {
        // Audio must not depend on the mesh/material readiness gate in Present.
        if(Age>=Flight.FlightSeconds)
        {
            if(!bRainBuilt)BuildRain();
            if(bRainBuilt)PlayDescentAudio(Age-Flight.FlightSeconds);
        }
        Present(Age);
    }
}
