#include "FPSIceSpikeVolley.h"
#include "FPSIceSpikeComponent.h"
#include "FPSFireballComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Perception/AISense_Hearing.h"
#include "NiagaraComponent.h"

namespace
{
UStaticMeshComponent* AddIceMesh(AActor* Owner,UStaticMesh* Mesh,UMaterialInterface* Material)
{
    auto* C=NewObject<UStaticMeshComponent>(Owner);Owner->AddInstanceComponent(C);C->SetupAttachment(Owner->GetRootComponent());
    C->SetStaticMesh(Mesh);C->SetMaterial(0,Material);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    C->SetCanEverAffectNavigation(false);C->SetReceivesDecals(false);C->RegisterComponent();return C;
}
}
AFPSIceSpikeVolley::AFPSIceSpikeVolley()
{PrimaryActorTick.bCanEverTick=true;SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("VolleyRoot")));}
void AFPSIceSpikeVolley::Prepare(UFPSIceSpikeComponent* InSource,APawn* InShooter,const FIceSpikeCast& Snapshot,const TArray<TObjectPtr<UStaticMesh>>& Spikes,UStaticMesh* Shard,UMaterialInterface* Material,UMaterialInterface* ShellMaterial,UParticleSystem* FX,USoundBase* Sound,UNiagaraSystem* Motes,UNiagaraSystem* ColdMist)
{
    Source=InSource;Shooter=InShooter;Cast=Snapshot;ShardMesh=Shard;IceMaterial=Material;ImpactFX=FX;ImpactSound=Sound;
    AddTickPrerequisiteActor(InShooter);Flights.SetNum(Cast.Count);
    for(int32 I=0;I<Cast.Count;++I)
    {
        // Randomise each spike once; continuous noise supplies smooth, frame-independent drift.
        Flights[I].HoverNoiseSeed=FVector2D(FMath::FRandRange(0.f,512.f),FMath::FRandRange(0.f,512.f));
        Flights[I].HoverNoiseRate=FVector2D(FMath::FRandRange(.22f,.36f),FMath::FRandRange(.18f,.30f));
        auto* Spike=Spikes[I%Spikes.Num()].Get();
        auto* Core=AddIceMesh(this,Spike,ShellMaterial);Core->SetCastShadow(false);Cores.Add(Core);
        auto* Heart=AddIceMesh(this,Spike,Material);Heart->AttachToComponent(Core,FAttachmentTransformRules::KeepRelativeTransform);
        Heart->SetRelativeScale3D(FVector(.965f,.78f,.78f));Heart->SetCastShadow(false);Hearts.Add(Heart);
        auto* Trail=NewObject<UNiagaraComponent>(this);AddInstanceComponent(Trail);Trail->SetupAttachment(GetRootComponent());Trail->SetAsset(Motes);Trail->SetAutoActivate(false);Trail->SetCastShadow(false);Trail->RegisterComponent();Trail->AddTickPrerequisiteActor(this);Trails.Add(Trail);
        auto* VaporHost=GetWorld()->SpawnActor<AActor>(GetActorLocation(),FRotator::ZeroRotator);
        auto* Vapor=NewObject<UNiagaraComponent>(VaporHost);VaporHost->AddInstanceComponent(Vapor);VaporHost->SetRootComponent(Vapor);
        Vapor->SetAsset(ColdMist);Vapor->SetAutoActivate(false);Vapor->SetCastShadow(false);Vapor->RegisterComponent();
        Vapor->AddTickPrerequisiteActor(this);Vapors.Add(Vapor);VaporHosts.Add(VaporHost);
    }
    UpdateHover();
    for(const auto& Vapor:Vapors)Vapor->Activate(true);
    for(const auto& Trail:Trails)Trail->Activate(true);
}
void AFPSIceSpikeVolley::UpdateVapor(int32 Index,const FVector& Previous,float Strength)
{
    auto* Vapor=Vapors[Index].Get();auto* Core=Cores[Index].Get();
    Vapor->SetWorldLocation(Flights[Index].Position);
    Vapor->SetVariablePosition(TEXT("User.PreviousPosition"),Previous);
    Vapor->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[Index].Position);
    Vapor->SetVariableVec3(TEXT("User.FlightDirection"),Core->GetForwardVector());
    Vapor->SetVariableVec3(TEXT("User.Side"),Core->GetRightVector());
    Vapor->SetVariableVec3(TEXT("User.Up"),Core->GetUpVector());
    Vapor->SetVariableFloat(TEXT("User.Flight"),bFlying?1.f:0.f);
    Vapor->SetVariableFloat(TEXT("User.Strength"),Strength);
    Vapor->SetVariableFloat(TEXT("User.ReleasePulse"),bFlying?FMath::Clamp(1.f-FlightAge/.16f,0.f,1.f):0.f);
    auto* Trail=Trails[Index].Get();Trail->SetWorldLocation(Flights[Index].Position);
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"),Previous);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[Index].Position);
    Trail->SetVariableVec3(TEXT("User.FlightDirection"),Core->GetForwardVector());
    Trail->SetVariableVec3(TEXT("User.Side"),Core->GetRightVector());Trail->SetVariableVec3(TEXT("User.Up"),Core->GetUpVector());
    Trail->SetVariableFloat(TEXT("User.Flight"),bFlying?1.f:0.f);Trail->SetVariableFloat(TEXT("User.Strength"),Strength);
}
int32 AFPSIceSpikeVolley::RemainingCount() const
{int32 Count=0;for(const auto& F:Flights)if(F.bActive)++Count;return Count;}
void AFPSIceSpikeVolley::UpdateHover()
{
    if(!Shooter.IsValid())return;
    const auto* Camera=Shooter->FindComponentByClass<UCameraComponent>();
    const FVector Eye=Camera?Camera->GetComponentLocation():Shooter->GetPawnViewLocation();
    const FRotator ViewRotation=Camera?Camera->GetComponentRotation():Shooter->GetViewRotation();
    const FRotationMatrix ViewBasis(ViewRotation);
    const FVector Forward=ViewBasis.GetUnitAxis(EAxis::X),Right=ViewBasis.GetUnitAxis(EAxis::Y),Up=ViewBasis.GetUnitAxis(EAxis::Z);
    // The player camera maintains vertical FOV, using its configured aspect to store horizontal FOV.
    const float TanVertical=Camera?FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView*.5f))/FMath::Max(.1f,Camera->AspectRatio):FMath::Tan(FMath::DegreesToRadians(37.5f));
    float ViewAspect=Camera?Camera->AspectRatio:16.f/9.f;
    if(const auto* PC=::Cast<APlayerController>(Shooter->GetController()))
    {
        int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);
        if(Width>0&&Height>0)ViewAspect=float(Width)/Height;
    }
    constexpr float ForwardDistance=44.f;
    // At full size the upper frustum edge cuts the 54 cm mesh just ahead of its centre.
    // Its thick rear half stays above the frame; the pointed front extends into the top band.
    const float OverheadHeight=(ForwardDistance+4.f)*TanVertical;
    const float HalfRowWidth=ForwardDistance*TanVertical*ViewAspect*.72f;
    const float Spacing=FMath::Min(18.f,HalfRowWidth*2.f/FMath::Max(1,Flights.Num()-1));
    const float SideDrift=FMath::Min(2.8f,Spacing*.16f);
    const float VerticalDrift=FMath::Min(2.f,OverheadHeight*.05f);
    float Grow=FMath::Clamp(Age*Cast.CastSpeed/.95f,0.f,1.f);Grow=Grow*Grow*(3-2*Grow);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceSpikeHover),false,Shooter.Get());Query.AddIgnoredActor(this);
    for(int32 I=0;I<Flights.Num();++I)
    {
        const float Slot=float(I)-float(Flights.Num()-1)*.5f;
        const auto& Flight=Flights[I];
        const float DriftX=FMath::PerlinNoise1D(Flight.HoverNoiseSeed.X+Age*Flight.HoverNoiseRate.X)*SideDrift*Grow;
        const float DriftY=FMath::PerlinNoise1D(Flight.HoverNoiseSeed.Y+Age*Flight.HoverNoiseRate.Y)*VerticalDrift*Grow;
        // Preserve each overhead slot while its spike meanders independently, without orbit or spin.
        FVector Desired=Eye+Forward*ForwardDistance+Right*(Slot*Spacing+DriftX)+Up*(OverheadHeight+DriftY);
        FHitResult Cover;
        if(GetWorld()->SweepSingleByChannel(Cover,Eye,Desired,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query))Desired=Cover.Location;
        const FVector Previous=Age==0?Desired:Flights[I].Position;
        Flights[I].Position=Desired;
        auto* Core=Cores[I].Get();Core->SetWorldLocation(Desired);
        FRotator Facing=ViewRotation;Facing.Roll+=I*113.f;
        Core->SetWorldRotation(Facing);
        Core->SetWorldScale3D(FVector::OneVector*FMath::Max(.01f,Grow));
        Core->SetVisibility(!Camera||FVector::DistSquared(Camera->GetComponentLocation(),Desired)>FMath::Square(35.f),true);
        UpdateVapor(I,Previous,Core->IsVisible()?Grow:0.f);
    }
}
void AFPSIceSpikeVolley::Launch(const FVector& AimPoint)
{
    if(bFinished||bFlying)return;bFlying=true;FlightAge=0;
    for(int32 I=0;I<Flights.Num();++I)
    {
        auto& F=Flights[I];const FVector ToAim=AimPoint-F.Position;
        F.Direction=ToAim.GetSafeNormal(UE_SMALL_NUMBER,FVector::ForwardVector);F.Remaining=FMath::Min(float(ToAim.Size()),Cast.Range);F.bAimEndpoint=ToAim.Size()<Cast.Range;
        FRotator Facing=F.Direction.Rotation();Facing.Roll=I*113.f;
        Cores[I]->SetWorldLocation(F.Position);Cores[I]->SetWorldRotation(Facing);Cores[I]->SetWorldScale3D(FVector::OneVector);Cores[I]->SetVisibility(true,true);
        auto* Trail=Trails[I].Get();Trail->SetWorldLocation(F.Position);Trail->SetVariablePosition(TEXT("User.PreviousPosition"),F.Position);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),F.Position);
        Trail->SetVariableVec3(TEXT("User.FlightDirection"),F.Direction);Trail->SetVariableFloat(TEXT("User.FlightSpeed"),Cast.Speed);
        UpdateVapor(I,F.Position,1.f);
    }
}
void AFPSIceSpikeVolley::Tick(float Delta)
{
    Super::Tick(Delta);if(bFinished)return;
    if(!Shooter.IsValid()||!Source.IsValid()){Destroy();return;}
    if(auto* H=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){Destroy();return;}
    Age+=Delta;
    if(!bFlying){if(Age>=Cast.HoverDuration)Destroy();else UpdateHover();return;}
    FlightAge+=Delta;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    for(int32 I=0;I<Flights.Num();++I)
    {
        auto& F=Flights[I];if(!F.bActive)continue;
        const FVector Previous=F.Position;
        const float Step=FMath::Min(Cast.Speed*Delta,F.Remaining);const FVector End=F.Position+F.Direction*Step;
        Trails[I]->SetVariablePosition(TEXT("User.PreviousPosition"),F.Position);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(IceSpikeFlight),false,Shooter.Get());Query.AddIgnoredActor(this);FHitResult Hit;
        if(GetWorld()->SweepSingleByChannel(Hit,F.Position,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query))
        {
            const FHitResult First=Hit;
            // Source hit loop settles overlapping contacts before destroying a spike.
            // Limit that cluster to one diameter, independent of frame time; never pierce a wall.
            TSet<AActor*> Settled;
            const FVector ClusterEnd=F.Position+F.Direction*FMath::Min(Step,FVector::Distance(F.Position,First.Location)+36.f);
            do
            {
                AActor* Target=Hit.GetActor();
                if(!Target||!Target->FindComponentByClass<UMonsterCombatComponent>()||Settled.Contains(Target))break;
                Settled.Add(Target);if(M)M->ApplyIceSpikeHit(Shooter.Get(),Hit,Cast,Rewards);
                Query.AddIgnoredActor(Target);
            }
            while(GetWorld()->SweepSingleByChannel(Hit,F.Position,ClusterEnd,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(18),Query));
            F.Position=First.Location;Shatter(I,First.ImpactPoint,First.ImpactNormal,true);
        }
        else
        {
            F.Position=End;F.Remaining-=Step;Cores[I]->SetWorldLocation(End);
            if(F.Remaining<=UE_KINDA_SMALL_NUMBER)Shatter(I,End,-F.Direction,F.bAimEndpoint);
        }
        if(F.bActive)UpdateVapor(I,Previous,1.f);
    }
    for(int32 I=0;I<Flights.Num();++I){Trails[I]->SetWorldLocation(Flights[I].Position);Trails[I]->SetVariablePosition(TEXT("User.CurrentPosition"),Flights[I].Position);}
    if(RemainingCount()==0)Destroy();
}
void AFPSIceSpikeVolley::Shatter(int32 Index,const FVector& Position,const FVector& Normal,bool bEffect)
{
    Flights[Index].bActive=false;Cores[Index]->SetVisibility(false,true);Trails[Index]->Deactivate();
    // Let already emitted condensation dissipate after its spike/volley disappears.
    auto* Vapor=Vapors[Index].Get();Vapor->SetVariableFloat(TEXT("User.Strength"),0.f);
    if(VaporHosts[Index].IsValid())VaporHosts[Index]->SetLifeSpan(.85f);
    if(!bEffect)return;
    if(ImpactFX)UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactFX,Position,Normal.Rotation(),FVector(.7f),true,EPSCPoolMethod::AutoRelease);
    if(ShardMesh&&IceMaterial)if(auto* F=GetWorld()->SpawnActor<AFPSIceSpikeFragments>(Position,FRotator::ZeroRotator))F->Setup(ShardMesh,IceMaterial,Normal);
    const double Now=GetWorld()->GetTimeSeconds();
    if(ImpactSound&&Now-LastSound>=.09){UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Position,.65f,FMath::FRandRange(.94f,1.06f));LastSound=Now;}
    UAISense_Hearing::ReportNoiseEvent(this,Position,.4f,Shooter.Get(),900,TEXT("IceSpike"));
}
void AFPSIceSpikeVolley::Finish()
{
    if(bFinished)return;bFinished=true;
    if(!Shooter.IsValid())return;
    if(GetGameInstance())if(auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())M->FinishIceSpikeCast(Rewards);
    const auto* Health=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&!Health->IsDead()&&(Cast.bGrantChain||Cast.CastHasteStacks>0))
    {auto* Status=UCombatStatusFormula::GetOrAdd(Shooter.Get());if(Cast.bGrantChain)Status->AddChainSpell();Status->AddHaste(Cast.CastHasteStacks,Cast.CastHasteDuration);}
    if(Source.IsValid())Source->VolleyFinished(this);Source.Reset();
}
void AFPSIceSpikeVolley::EndPlay(EEndPlayReason::Type Reason)
{
    for(int32 I=0;I<Vapors.Num();++I)if(VaporHosts[I].IsValid())
    {
        Vapors[I]->SetVariableFloat(TEXT("User.Strength"),0.f);VaporHosts[I]->SetLifeSpan(.85f);
    }
    Finish();Super::EndPlay(Reason);
}

AFPSIceSpikeFragments::AFPSIceSpikeFragments()
{PrimaryActorTick.bCanEverTick=true;SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("FragmentRoot")));}
void AFPSIceSpikeFragments::Setup(UStaticMesh* Mesh,UMaterialInterface* Material,const FVector& Normal)
{
    for(int32 I=0;I<12;++I)
    {
        auto* C=AddIceMesh(this,Mesh,Material);C->SetRelativeScale3D(FVector(FMath::FRandRange(.25f,.65f)));C->SetRelativeRotation(FMath::VRand().Rotation());
        Shards.Add(C);Velocities.Add((Normal*.75f+FMath::VRand()).GetSafeNormal()*FMath::FRandRange(100.f,240.f));Spins.Add(FRotator(90+I*31,180-I*17,80+I*11));
    }
    SetLifeSpan(.65f);
}
void AFPSIceSpikeFragments::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    for(int32 I=0;I<Shards.Num();++I)
    {
        auto* C=Shards[I].Get();C->AddWorldOffset(Velocities[I]*Delta-FVector(0,0,375.f*Delta*Delta));Velocities[I].Z-=750.f*Delta;
        C->AddLocalRotation(Spins[I]*Delta);
        if(Age>.42f)C->SetVisibility(false);
    }
}
