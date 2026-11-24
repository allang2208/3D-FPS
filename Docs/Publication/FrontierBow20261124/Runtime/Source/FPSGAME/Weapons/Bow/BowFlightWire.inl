#include "BowArrow.h"
#include "BowStats.h"
#include "BowMountainEchoComponent.h"
#include "EclipseBowMark.h"
#include "../../Props/FPSPracticeTarget.h"
#include "../../BallisticAuditTarget.h"
#include "Components/BoxComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "EngineUtils.h"

namespace BowFlightWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("BowFlightWire"));}
bool Frontier(){return FParse::Param(FCommandLine::Get(),TEXT("FrontierBowWire"));}

struct FTrack
{
    TSet<TWeakObjectPtr<ABowArrow>> Arrows,Flat,Falling,Glowing;
    TWeakObjectPtr<ABallisticAuditTarget> Target;
    TWeakObjectPtr<AFPSPracticeTarget> Practice;
    bool SawMark=false,SawCharged=false;
    TSet<TWeakObjectPtr<AActor>> BeamSources;
    FVector Origin=FVector::ZeroVector;
    FGuid Draw;
    bool Released=false;
    double Started=-1.;
};
static FTrack Track;

void Place(AFPSGAMECharacter* P,int32 Phase)
{
    P->SetActorLocation(FVector(0,500.*Phase,4000.));
    P->GetController()->SetControlRotation(FRotator::ZeroRotator);
    P->SetActorTickEnabled(false);
    P->GetCharacterMovement()->DisableMovement();
    P->GetCharacterMovement()->SetComponentTickEnabled(false);
    P->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void Reset(AFPSGAMECharacter* P,int32 Phase)
{
    if(Track.Target.IsValid())Track.Target->Destroy();
    if(Track.Practice.IsValid())Track.Practice->Destroy();
    Track={};Place(P,Phase);
    Track.Origin=P->GetPawnViewLocation()+FVector(45,0,0);
    if(!P->HasAuthority())return;
    auto* M=P->GetNetShadowProfile();
    const auto Stats=ColdSteelBow::Evaluate(*M->ActiveBow(),M);
    const double Range=Stats.Range*100.,Speed=Stats.Speed*100.;
    const double Gravity=ColdSteelInventory::Number(*M->ActiveBow(),TEXT("arrow_gravity_cm"),980.);
    const FVector End=Track.Origin+FVector(Range*1.5,0,-Gravity*.5*FMath::Square(.5*Range/Speed));
    if(Frontier()&&Phase==0)
    {
        auto* Practice=P->GetWorld()->SpawnActor<AFPSPracticeTarget>(End,FRotator::ZeroRotator);
        auto* Face=NewObject<UBoxComponent>(Practice);
        Face->SetupAttachment(Practice->GetRootComponent());Face->SetBoxExtent(FVector(8,80,150));
        Face->SetCollisionProfileName(TEXT("BlockAll"));Face->RegisterComponent();
        Practice->SetNetCullDistanceSquared(FMath::Square(Range*2.));
        Track.Practice=Practice;
        return;
    }
    auto* Target=P->GetWorld()->SpawnActor<ABallisticAuditTarget>(End,FRotator::ZeroRotator);
    Target->FindComponentByClass<UBoxComponent>()->SetBoxExtent(FVector(8,60,120));
    Track.Target=Target;
}
void Sample(AFPSGAMECharacter* P,int32 Phase)
{
    const double Range=Frontier()||Phase==0?28000.:32000.;
    if(Frontier())
    {
        if(Phase==0&&!Track.SawMark)
            for(TActorIterator<AFPSPracticeTarget> It(P->GetWorld());It;++It)
                if(UEclipseBowMark::DamageMultiplier(*It)>1.){Track.SawMark=true;break;}
        if(Phase==1)
        {
            if(const auto* Echo=P->FindComponentByClass<UBowMountainEchoComponent>())
                if(const auto* Bow=P->FindComponentByClass<UBowWeaponComponent>())
                    Track.SawCharged|=Echo->ChargesFor(Bow->EquippedInstance())==MountainEchoString::MaximumStacks;
            for(TActorIterator<AAuroraBeamVisual> It(P->GetWorld());It;++It)
                if(const auto* Arrow=Cast<ABowArrow>(It->GetOwner());Arrow&&Arrow->GetInstigator()==P)
                    Track.BeamSources.Add(It->GetOwner());
        }
    }
    for(TActorIterator<ABowArrow> It(P->GetWorld());It;++It)
    {
        if(It->GetInstigator()!=P||It->IsActorBeingDestroyed())continue;
        const FVector Travel=It->GetActorLocation()-Track.Origin;
        if(FMath::Abs(Travel.Y)>100.||Travel.X<200.)continue;
        Track.Arrows.Add(*It);
        if(Travel.X>Range*.7&&Travel.X<Range*.98&&FMath::Abs(Travel.Z)<15.)Track.Flat.Add(*It);
        if(Travel.X>Range*1.2&&Travel.X<Range*1.49&&Travel.Z<-50.)Track.Falling.Add(*It);
        auto* Glow=It->FindComponentByClass<UMaterialBillboardComponent>();
        if(Glow&&Glow->IsVisible()&&!Glow->Elements.IsEmpty())Track.Glowing.Add(*It);
    }
}
bool Check(int32 Phase,const TSharedPtr<FJsonObject>& R)
{
    const int32 Count=Phase==0?1:2;
    R->SetNumberField(TEXT("arrows"),Track.Arrows.Num());
    R->SetNumberField(TEXT("flat"),Track.Flat.Num());R->SetNumberField(TEXT("falling"),Track.Falling.Num());
    R->SetNumberField(TEXT("glowing"),Track.Glowing.Num());
    bool Effects=Track.Glowing.Num()==Count;
    if(Frontier()&&Phase==0){R->SetBoolField(TEXT("eclipse_received"),Track.SawMark);Effects&=Track.SawMark;}
    if(Frontier()&&Phase==1)
    {
        R->SetBoolField(TEXT("full_resonance_received"),Track.SawCharged);
        R->SetNumberField(TEXT("laser_projectiles"),Track.BeamSources.Num());
        Effects=Track.SawCharged&&Track.BeamSources.Num()==Count&&Track.Glowing.IsEmpty();
    }
    return Track.Arrows.Num()==Count&&Track.Flat.Num()==Count&&Track.Falling.Num()==Count&&Effects;
}
}
