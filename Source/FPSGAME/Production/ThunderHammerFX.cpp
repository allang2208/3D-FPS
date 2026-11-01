#include "ThunderHammerFX.h"
#include "ThunderHammerTuning.h"
#include "GameFramework/Pawn.h"
#include "../Skills/FPSLightningArc.h"
#include "Components/SceneComponent.h"
#include "Components/SplineComponent.h"
#include "Components/PointLightComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace
{
    constexpr int32 Capacity=4,PathCount=6;
    const FSoftObjectPath BoltPath(TEXT("/Game/Weapons/ThunderGodHammer20261028/HeavyThunderV1/NS_ThunderHammerBolt.NS_ThunderHammerBolt"));
    const FSoftObjectPath ImpactPath(TEXT("/Game/Weapons/ThunderGodHammer20261028/HeavyThunderV1/NS_ThunderHammerImpact.NS_ThunderHammerImpact"));
    const FSoftObjectPath SoundPath(TEXT("/Game/Weapons/ThunderGodHammer20261028/HeavyThunderV1/S_ThunderHammerStrike.S_ThunderHammerStrike"));
    const FSoftObjectPath ChainPath(TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"));
}

AThunderHammerStrikeFX::AThunderHammerStrikeFX()
{
    bReplicates=false;PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("StrikeRoot"));SetRootComponent(Root);
    for(int32 I=0;I<PathCount;++I)
    {
        auto* Path=CreateDefaultSubobject<USplineComponent>(*FString::Printf(TEXT("StrikePath%d"),I));
        Path->SetupAttachment(Root);Path->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Path->SetCanEverAffectNavigation(false);Paths.Add(Path);
        auto* FX=CreateDefaultSubobject<UNiagaraComponent>(*FString::Printf(TEXT("StrikeBolt%d"),I));
        FX->SetupAttachment(Path);FX->SetAutoActivate(false);FX->SetCastShadow(false);
        FX->SetCanEverAffectNavigation(false);FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        FX->AddTickPrerequisiteActor(this);Bolts.Add(FX);
    }
    Impact=CreateDefaultSubobject<UNiagaraComponent>(TEXT("ContactBurst"));Impact->SetupAttachment(Root);
    Impact->SetAutoActivate(false);Impact->SetCastShadow(false);Impact->SetCanEverAffectNavigation(false);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("ContactFlash"));Light->SetupAttachment(Root);
    Light->SetCastShadows(false);Light->SetIntensity(0);Light->SetAttenuationRadius(480.f);
    Light->SetLightColor(FLinearColor(.24f,.56f,1.f));Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetIndirectLightingIntensity(0);Light->SetVolumetricScatteringIntensity(0);
}

void AThunderHammerStrikeFX::Prepare(UNiagaraSystem* Bolt,UNiagaraSystem* Burst)
{
    for(int32 I=0;I<PathCount;++I)
    {
        auto* FX=Bolts[I].Get();FX->SetAsset(Bolt);
        FX->SetVariableObject(TEXT("User.BladeSpline"),Paths[I]);
        FX->SetVariableFloat(TEXT("User.Jitter"),0);FX->SetVariableFloat(TEXT("User._ColorHue"),0);
        FX->SetVariableFloat(TEXT("User._DetailSpeed"),.0013f);
        FX->SetVariableFloat(TEXT("User.MainPowerSpeed"),8);
        FX->SetVariableFloat(TEXT("User._DetailSpeedOffset"),6);
        FX->SetVariableBool(TEXT("User.AddDetail"),false);FX->SetVariableBool(TEXT("User.AddMainPower"),true);
        FX->PrecachePSOs();
    }
    Impact->SetAsset(Burst);Impact->PrecachePSOs();
}

void AThunderHammerStrikeFX::Play(const FVector& Point,const FVector& Normal,float Height,int32 Seed,float InitialAge,USoundBase* Sound,float Scale)
{
    for(const auto& FX:Bolts)FX->DeactivateImmediate();Impact->DeactivateImmediate();
    Age=InitialAge;VisualScale=Scale;SetActorLocationAndRotation(Point,FRotator::ZeroRotator);
    FRandomStream Random(Seed);TArray<FVector> Trunk;
    constexpr int32 Segments=22;
    // Monotonic world Z preserves a vertical strike. Small angular offsets
    // make an irregular bolt while both ends remain over the hammer contact.
    for(int32 I=0;I<=Segments;++I)
    {
        const float T=float(I)/Segments;
        const float Jitter=FMath::Min(Height*.025f,48.f)*FMath::Sin(PI*T);
        Trunk.Add(FVector(Random.FRandRange(-Jitter,Jitter),Random.FRandRange(-Jitter,Jitter),Height*(1.f-T)+5.f));
    }
    const FQuat FloorRotation=FRotationMatrix::MakeFromZ(Normal).ToQuat();
    for(int32 I=0;I<PathCount;++I)
    {
        auto* Path=Paths[I].Get();Path->ClearSplinePoints(false);
        TArray<FVector> Points;
        if(I==0)Points=Trunk;
        else if(I<4)
        {
            const FVector Start=Trunk[4+I*4];
            const float Angle=Random.FRandRange(0.f,2.f*PI);
            const float Spread=FMath::Min(Height*.15f,Random.FRandRange(180.f,310.f));
            const FVector End=Start+FVector(FMath::Cos(Angle)*Spread,FMath::Sin(Angle)*Spread,-FMath::Min(Height*.23f,460.f));
            for(int32 J=0;J<=8;++J)
            {
                const float T=J/8.f,W=FMath::Sin(PI*T)*Spread*.12f;
                Points.Add(FMath::Lerp(Start,End,T)+FVector(Random.FRandRange(-W,W),Random.FRandRange(-W,W),0));
            }
        }
        else
        {
            const float Angle=Random.FRandRange(0.f,2.f*PI);
            const FVector Start=Normal*8.f;
            FVector End=FloorRotation.RotateVector(FVector(FMath::Cos(Angle),FMath::Sin(Angle),0))*Random.FRandRange(150.f,245.f)+Start;
            FCollisionQueryParams Q(SCENE_QUERY_STAT(ThunderGroundArc),false,this);FHitResult Wall;
            if(GetWorld()->LineTraceSingleByChannel(Wall,Point+Start,Point+End,ECC_Visibility,Q))
                End=Wall.ImpactPoint-Point+Wall.ImpactNormal*5.f;
            for(int32 J=0;J<=8;++J)
            {
                const float T=J/8.f,W=FMath::Sin(PI*T)*13.f;
                Points.Add(FMath::Lerp(Start,End,T)+FloorRotation.RotateVector(FVector(Random.FRandRange(-W,W),Random.FRandRange(-W,W),Random.FRandRange(0.f,W*.5f))));
            }
        }
        for(int32 J=0;J<Points.Num();++J)
        {
            Path->AddSplinePoint(Points[J],ESplineCoordinateSpace::Local,false);
            Path->SetSplinePointType(J,ESplinePointType::Linear,false);
        }
        Path->UpdateSpline();
        auto* FX=Bolts[I].Get();FX->SetSystemFixedBounds(Path->CalcBounds(FTransform::Identity).GetBox().ExpandBy(90.f*VisualScale));
        FX->SetVariableFloat(TEXT("User._Width"),(I==0?76.f:I<4?16.f:12.f)*VisualScale);
        FX->SetVariableFloat(TEXT("User.Progress"),1.f);FX->SetVariableFloat(TEXT("User._Brightness"),I==0?28.f:18.f);
        FX->Activate(true);
    }
    Impact->SetRelativeLocation(Normal*12.f);Impact->SetRelativeScale3D(FVector(1.65f*FMath::Sqrt(VisualScale)));Impact->Activate(true);
    if(Age>1.f/60.f)Impact->AdvanceSimulation(FMath::FloorToInt(Age*60.f),1.f/60.f);
    Light->SetRelativeLocation(Normal*70.f);
    // The wave's server timestamp controls every client. Late observers see
    // only the remaining flash, and never restart a completed strike.
    UpdateEnvelope();SetActorTickEnabled(true);
    if(Sound&&Age<.2f)UGameplayStatics::PlaySoundAtLocation(this,Sound,Point,.7f,.88f,Age);
}

void AThunderHammerStrikeFX::UpdateEnvelope()
{
    const float Flash=FMath::Exp(-Age*13.f)+.7f*FMath::Exp(-FMath::Square((Age-.095f)/.018f))+
        .32f*FMath::Exp(-FMath::Square((Age-.205f)/.026f));
    const float Tail=FMath::Clamp((ThunderHammer::VisualSeconds-Age)/.16f,0.f,1.f);
    for(int32 I=0;I<PathCount;++I)
    {
        const float Strength=I>=4?FMath::Exp(-Age*5.f)*Tail:Flash*Tail;
        Bolts[I]->SetVariableFloat(TEXT("User._Brightness"),(I==0?28.f:18.f)*Strength);
    }
    Light->SetIntensity(2600.f*FMath::Min(1.f,Flash)*Tail*FMath::Sqrt(VisualScale));
}

void AThunderHammerStrikeFX::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    if(Age>=ThunderHammer::VisualSeconds)
    {
        for(const auto& FX:Bolts)FX->DeactivateImmediate();Impact->DeactivateImmediate();Light->SetIntensity(0);
        SetActorTickEnabled(false);return;
    }
    UpdateEnvelope();
}

bool UThunderHammerFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type==EWorldType::Game||Type==EWorldType::PIE;
}

void UThunderHammerFXSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);if(World.GetNetMode()==NM_DedicatedServer)return;
    Assets=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{BoltPath,ImpactPath,SoundPath,ChainPath},
        FStreamableDelegate::CreateUObject(this,&UThunderHammerFXSubsystem::PrepareNext));
}

void UThunderHammerFXSubsystem::PrepareNext()
{
    auto* World=GetWorld();if(!World||Pool.Num()>=Capacity)return;
    auto* Bolt=Cast<UNiagaraSystem>(BoltPath.ResolveObject());auto* Burst=Cast<UNiagaraSystem>(ImpactPath.ResolveObject());
    if(!Bolt||!Burst)return;
    FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Entry=World->SpawnActor<AThunderHammerStrikeFX>(FVector::ZeroVector,FRotator::ZeroRotator,Params))
    {Entry->Prepare(Bolt,Burst);Pool.Add(Entry);}
    if(Pool.Num()<Capacity)PreparationTimer=World->GetTimerManager().SetTimerForNextTick(
        FTimerDelegate::CreateUObject(this,&UThunderHammerFXSubsystem::PrepareNext));
}

bool UThunderHammerFXSubsystem::Emit(const FVector& Point,const FVector& Normal,float Height,int32 Seed,float Age,float Scale)
{
    if(Age>=ThunderHammer::VisualSeconds)return true;
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!Camera)return false;
    if(FVector::DistSquared(Camera->GetCameraLocation(),Point)>FMath::Square(9000.f))return true;
    if(Pool.IsEmpty())return false;
    AThunderHammerStrikeFX* Entry=Pool[0];
    for(const auto& Candidate:Pool)if(Candidate->Age>Entry->Age)Entry=Candidate;
    Entry->Play(Point,Normal,Height,Seed,Age,Cast<USoundBase>(SoundPath.ResolveObject()),Scale);return true;
}

void UThunderHammerFXSubsystem::EmitOverload(APawn* Owner,const FVector& Start,const FVector& End,const FLightningCast& Spell)
{
    if(!Owner||!Owner->HasAuthority())return;
    OverloadArcs.RemoveAll([](const auto& Arc){return !Arc.IsValid();});
    if(OverloadArcs.Num()>=32)return;
    FActorSpawnParameters Params;Params.Owner=Owner;Params.Instigator=Owner;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,Params))
    {auto Visual=Spell;Visual.Duration=.35f;Visual.Fade=.18f;Arc->InitializeArc(Cast<UNiagaraSystem>(ChainPath.ResolveObject()),Start,End,Visual,.45f);OverloadArcs.Add(Arc);}
}

void UThunderHammerFXSubsystem::Deinitialize()
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(PreparationTimer);
    for(const auto& Entry:Pool)if(IsValid(Entry))Entry->Destroy();Pool.Reset();
    for(const auto& Arc:OverloadArcs)if(Arc.IsValid())Arc->Destroy();OverloadArcs.Reset();
    if(Assets){Assets->CancelHandle();Assets.Reset();}Super::Deinitialize();
}
