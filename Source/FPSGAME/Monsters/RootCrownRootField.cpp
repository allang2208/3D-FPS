#include "RootCrownRootField.h"
#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "RootCrownMineDamage.h"
#include "Components/SceneComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

ARootCrownRootField::ARootCrownRootField()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=1.f/30.f;
    bReplicates=true;SetNetUpdateFrequency(20.f);SetCanBeDamaged(true);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("RootField"));
    Tags.Add(TEXT("NoSkillTraining"));
    for(int32 I=0;I<3;++I)
    {
        auto* Shape=CreateDefaultSubobject<USphereComponent>(*FString::Printf(TEXT("RootKnotHit%d"),I));
        Shape->SetupAttachment(RootComponent);Shape->InitSphereRadius(27.f);
        Shape->SetCollisionObjectType(ECC_WorldDynamic);Shape->SetCollisionResponseToAllChannels(ECR_Ignore);
        Shape->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);Shape->SetGenerateOverlapEvents(false);
        Shape->SetCanEverAffectNavigation(false);KnotShapes.Add(Shape);
        auto* Visual=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("RootKnot%d"),I));
        Visual->SetupAttachment(RootComponent);Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Visual->SetCanEverAffectNavigation(false);Visual->bReceivesDecals=false;Knots.Add(Visual);
    }
}
double ARootCrownRootField::Clock() const
{
    const auto* GS=GetWorld()->GetGameState();
    return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
float ARootCrownRootField::Age() const{return FMath::Max(0.f,float(Clock()-StartedAt));}
void ARootCrownRootField::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ARootCrownRootField,Source);DOREPLIFETIME(ARootCrownRootField,Paths);
    DOREPLIFETIME(ARootCrownRootField,Mines);DOREPLIFETIME(ARootCrownRootField,StartedAt);
    DOREPLIFETIME(ARootCrownRootField,TriggerRadius);DOREPLIFETIME(ARootCrownRootField,BlastRadius);
    DOREPLIFETIME(ARootCrownRootField,FuseSeconds);DOREPLIFETIME(ARootCrownRootField,Lifetime);
}
void ARootCrownRootField::BeginPlay(){Super::BeginPlay();OnRep_Layout();}
bool ARootCrownRootField::CanShoot(int32 Index) const
{
    return Mines.IsValidIndex(Index)&&(Mines[Index].Phase==ERootCrownMinePhase::Armed||Mines[Index].Phase==ERootCrownMinePhase::Triggered);
}
void ARootCrownRootField::OnRep_Layout()
{
    if(!Source||Paths.Num()!=3||Mines.Num()!=3)return;
    for(int32 I=0;I<3;++I)
    {
        Knots[I]->SetWorldLocation(Mines[I].Position);Knots[I]->SetStaticMesh(Source->RootKnotMesh);
        Knots[I]->SetWorldRotation(FRotationMatrix::MakeFromZ(Mines[I].Normal).Rotator());
        KnotShapes[I]->SetWorldLocation(FVector(Mines[I].Position)+FVector(Mines[I].Normal)*24.f);
        KnotShapes[I]->SetCollisionEnabled(CanShoot(I)?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    }
    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(!bPresentationBuilt)BuildPresentation();
        if(bPresentationBuilt)UpdatePresentation(Age());
    }
}
void ARootCrownRootField::SetPhase(int32 Index,ERootCrownMinePhase Phase)
{
    Mines[Index].Phase=Phase;Mines[Index].ChangedAt=Clock();OnRep_Layout();ForceNetUpdate();
}
void ARootCrownRootField::ArmMines()
{
    if(!HasAuthority()||!Source||Source->Dead()||!Source->IsRootEnclosing()||Mines.Num()!=3||Age()<RootCrownRootTiming::Warning)return;
    for(int32 I=0;I<3;++I)if(Mines[I].Phase==ERootCrownMinePhase::Growing)
        SetPhase(I,PathOpen(Paths[I])?ERootCrownMinePhase::Armed:ERootCrownMinePhase::Expired);
}
void ARootCrownRootField::FinishCast()
{
    if(!HasAuthority()||Mines.Num()!=3)return;
    ArmMines();
    // A completed plant survives recovery and later stagger. Interrupted growth does not.
    for(int32 I=0;I<3;++I)if(Mines[I].Phase==ERootCrownMinePhase::Growing)SetPhase(I,ERootCrownMinePhase::Expired);
}
bool ARootCrownRootField::ExposureTo(int32 Index,APawn* Player,float& Distance) const
{
    Distance=BIG_NUMBER;if(!Player||!Mines.IsValidIndex(Index))return false;
    const FVector Origin=FVector(Mines[Index].Position)+FVector(Mines[Index].Normal)*18.f;
    FVector Closest=Player->GetActorLocation();
    if(auto* Shape=Cast<UPrimitiveComponent>(Player->GetRootComponent()))Shape->GetClosestPointOnCollision(Origin,Closest);
    Distance=FVector::Dist(Origin,Closest);
    FHitResult Block;return !TraceScene(Origin,Closest,Block);
}
void ARootCrownRootField::Tick(float Dt)
{
    Super::Tick(Dt);
    if(!Source||Paths.Num()!=3||Mines.Num()!=3){if(HasAuthority())Destroy();return;}
    if(HasAuthority())
    {
        if(Source->Dead()||Source->IsActorBeingDestroyed()){Destroy();return;}
        ArmMines();
        bool AllSpent=true;double LastChange=StartedAt;
        for(int32 I=0;I<3;++I)
        {
            if(Mines[I].Phase==ERootCrownMinePhase::Growing&&!Source->IsRootEnclosing())SetPhase(I,ERootCrownMinePhase::Expired);
            if(Mines[I].Phase==ERootCrownMinePhase::Armed)
            {
                if(Age()>=RootCrownRootTiming::Warning+Lifetime)SetPhase(I,ERootCrownMinePhase::Expired);
                else for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
                {
                    APawn* Player=It->Get()?It->Get()->GetPawn():nullptr;
                    const auto* Vitals=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
                    if(!Vitals||Vitals->IsDead()||RangedAttackQuery::IsFriendlyUnit(Source,Player))continue;
                    if(FVector::DistSquared(Player->GetActorLocation(),Mines[I].Position)>FMath::Square(TriggerRadius+150.f))continue;
                    float Distance;
                    if(ExposureTo(I,Player,Distance)&&Distance<=TriggerRadius){SetPhase(I,ERootCrownMinePhase::Triggered);break;}
                }
            }
            if(Mines[I].Phase==ERootCrownMinePhase::Triggered&&Clock()-Mines[I].ChangedAt>=FuseSeconds)Detonate(I);
            if(IsActorBeingDestroyed()||!IsValid(Source)||Source->Dead())return;
            AllSpent&=Mines[I].Phase>=ERootCrownMinePhase::Exploded;
            LastChange=FMath::Max(LastChange,Mines[I].ChangedAt);
        }
        if(AllSpent&&Clock()-LastChange>RootCrownRootTiming::BurstVisualSeconds){Destroy();return;}
    }
    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(!bPresentationBuilt)OnRep_Layout();
        if(bPresentationBuilt)UpdatePresentation(Age());
    }
}
void ARootCrownRootField::Detonate(int32 Index)
{
    if(!HasAuthority()||Mines[Index].Phase!=ERootCrownMinePhase::Triggered)return;
    // Commit first: synchronous damage callbacks cannot detonate this mine twice.
    SetPhase(Index,ERootCrownMinePhase::Exploded);
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        APawn* Player=It->Get()?It->Get()->GetPawn():nullptr;
        const auto* Vitals=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!Vitals||Vitals->IsDead()||Vitals->IsInvulnerable()||RangedAttackQuery::IsFriendlyUnit(Source,Player))continue;
        if(FVector::DistSquared(Player->GetActorLocation(),Mines[Index].Position)>FMath::Square(BlastRadius+150.f))continue;
        float Distance;if(!ExposureTo(Index,Player,Distance)||Distance>BlastRadius)continue;
        const float Falloff=FMath::Lerp(1.f,.35f,FMath::Clamp(Distance/FMath::Max(1.f,BlastRadius),0.f,1.f));
        UGameplayStatics::ApplyDamage(Player,BlastDamage*Falloff,Source->GetController(),Source,URootCrownMineDamage::StaticClass());
        if(IsActorBeingDestroyed()||!IsValid(Source)||Source->Dead())return;
    }
}
float ARootCrownRootField::DamageKnot(int32 Index,float Damage)
{
    if(!CanShoot(Index))return 0.f;
    const float Applied=FMath::Min(Health[Index],Damage);Health[Index]-=Applied;
    // Shooting the tissue neutralizes it, preserving the existing 80 HP counterplay.
    if(Health[Index]<=0.f)SetPhase(Index,ERootCrownMinePhase::Disarmed);
    return Applied;
}
float ARootCrownRootField::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||!Source||Source->Dead()||!CanBeDamaged()||Damage<=0.f||!FMath::IsFinite(Damage)||Causer==Source)return 0.f;
    float Applied=0.f;
    if(Event.IsOfType(FPointDamageEvent::ClassID))
    {
        const auto& Hit=static_cast<const FPointDamageEvent&>(Event).HitInfo;
        for(int32 I=0;I<3;++I)if(Hit.GetComponent()==KnotShapes[I]||Hit.GetComponent()==Knots[I]){Applied=DamageKnot(I,Damage);break;}
        // Remote reports omit component pointers; match the actual live hit sphere.
        if(!Hit.GetComponent())for(int32 I=0;I<3;++I)
            if(CanShoot(I)&&FVector::DistSquared(Hit.ImpactPoint,KnotShapes[I]->GetComponentLocation())<=FMath::Square(33.f))
            {Applied=DamageKnot(I,Damage);break;}
    }
    else if(Event.IsOfType(FRadialDamageEvent::ClassID))
    {
        const auto& Radial=static_cast<const FRadialDamageEvent&>(Event);
        for(int32 I=0;I<3;++I)for(const auto& Hit:Radial.ComponentHits)
            if(Hit.GetComponent()==KnotShapes[I]){Applied+=DamageKnot(I,Damage);break;}
    }
    if(Applied>0.f)Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    return Applied;
}
