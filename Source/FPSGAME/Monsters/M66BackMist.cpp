#include "M66BackMist.h"
#include "M66IncineratorMonster.h"
#include "../Combat/RangedAttackQuery.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraDataInterfaceArrayFunctionLibrary.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

AM66BackMist::AM66BackMist()
{
    DescendingSmoke=FSoftObjectPath(TEXT("/Game/Monsters/IncineratorBossM66/NetworkAudioV19/NS_M66HistorySoot.NS_M66HistorySoot"));
    bNetUseOwnerRelevancy=false;SetNetCullDistanceSquared(FMath::Square(4500.f));
    SetNetUpdateFrequency(10.f);
}
void AM66BackMist::BeginPlay()
{
    if(HasAuthority()){History.SetNum(32);HistoryOrigin=GetActorLocation();}
    // Resolve the authored variant once at creation, before activation. Keeping
    // the soft reference on the CDO also lets the asset-production commandlet
    // load this class before it has created the new Niagara package.
    GetSmokeComponent()->SetAsset(DescendingSmoke.LoadSynchronous());
    Super::BeginPlay();
}
double AM66BackMist::WakeClock() const
{const auto* Clock=GetWorld()->GetGameState();return Clock?Clock->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
void AM66BackMist::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AM66BackMist,History);DOREPLIFETIME(AM66BackMist,HistoryOrigin);}
void AM66BackMist::OnRep_History(){bHistoryDirty=true;}
void AM66BackMist::UpdateWake()
{
    const double Now=WakeClock();
    if(HasAuthority()&&bEmitting&&Now>=NextWake)
    {
        if(History.Num()!=32)History.SetNum(32);
        auto& Puff=History[NextPuffSerial%32];Puff.Serial=++NextPuffSerial;Puff.Born=Now;
        FVector Origins[4],Drift;GetEmissionSources(Origins,Drift);CapturePuffFloors(Origins,Puff.Floors);
        for(int32 I=0;I<4;++I)Puff.Origins[I]=Origins[I];Puff.Drift=Drift;
        NextWake=Now+.3;bHistoryDirty=true;ForceNetUpdate();
    }
    Trail.Reset();FBox Bounds(ForceInit);
    const float Lifetime=SmokeLifetime+1.5f;
    for(const auto& Puff:History)
    {
        const float Age=float(Now-Puff.Born);if(!Puff.Serial||Age<0.f||Age>=Lifetime)continue;
        FWakePuff Local;Local.Born=Puff.Born;Local.Drift=Puff.Drift;
        for(int32 I=0;I<4;++I)
        {
            Local.Origins[I]=Puff.Origins[I];Local.Floors[I]=Puff.Floors[I];
            Bounds+=FBox::BuildAABB(PuffCenter(Local.Origins[I],Local.Drift,Age,Local.Floors[I]),FVector(Radius*1.5f));
        }
        Trail.Add(Local);
    }
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* FX=GetSmokeComponent();
    FX->SetVariablePosition(TEXT("User.HistoryOrigin"),HistoryOrigin);
    FX->SetVariableFloat(TEXT("User.ClockOffset"),float(Now-GetWorld()->GetTimeSeconds()));
    if(bHistoryDirty)
    {
        TArray<FVector4> Birth,Motion;Birth.Init(FVector4(0,0,0,-10000),128);Motion.Init(FVector4(0,0,0,0),128);
        for(int32 Slot=0;Slot<History.Num();++Slot)
        {
            const auto& Puff=History[Slot];if(!Puff.Serial)continue;
            for(int32 I=0;I<4;++I)
            {
                const FVector Relative=FVector(Puff.Origins[I])-FVector(HistoryOrigin);
                Birth[Slot*4+I]=FVector4(Relative,float(Puff.Born));
                Motion[Slot*4+I]=FVector4(Puff.Drift.X,Puff.Drift.Y,Puff.Floors[I]-HistoryOrigin.Z,float(Puff.Serial*4+I));
            }
        }
        UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(FX,TEXT("User.PuffBirth"),Birth);
        UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(FX,TEXT("User.PuffMotion"),Motion);
        FX->SetVariableFloat(TEXT("User.HistoryReady"),1.f);
        bHistoryDirty=false;
    }
    if(Bounds.IsValid)FX->SetSystemFixedBounds(Bounds.TransformBy(FX->GetComponentTransform().ToInverseMatrixWithScale()));
}
bool AM66BackMist::ShouldEmit() const
{
    // Owner/death replication may arrive later than the cloud channel. Only
    // authority stops emission; clients consume the shared replicated flag.
    if(!HasAuthority())return true;
    const auto* Monster=Cast<AM66IncineratorMonster>(GetOwner());
    return IsValid(Monster)&&Monster->bEnableBackSmoke&&!Monster->Dead();
}
void AM66BackMist::GetEmissionSources(FVector (&Origins)[4],FVector& Drift) const
{
    const auto* Monster=Cast<AM66IncineratorMonster>(GetOwner());
    for(int32 I=0;I<4;++I)Origins[I]=Monster?Monster->BackSmokeOutlet(I):GetActorLocation();
    Drift=Monster?-Monster->GetActorForwardVector()*50.f:-GetActorForwardVector()*50.f;
    Drift.Z=0.f;
    // Only the birth drift is redirected. Old plumes retain their world course.
}
void AM66BackMist::CapturePuffFloors(const FVector (&Origins)[4],float (&Floors)[4]) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M66SmokeFloor),false,this);Query.AddIgnoredActor(GetOwner());
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get())Query.AddIgnoredActor(PC->GetPawn());
    const auto* Monster=Cast<AM66IncineratorMonster>(GetOwner());
    const float Fallback=Monster?float(Monster->GetNavAgentLocation().Z):float(GetActorLocation().Z-380.f);
    for(int32 I=0;I<4;++I)
    {
        FHitResult Hit;
        Floors[I]=RangedAttackQuery::LineTraceSingle(GetWorld(),GetOwner(),Hit,Origins[I],Origins[I]-FVector(0,0,700),ECC_Visibility,Query)
            ?float(Hit.ImpactPoint.Z):Fallback;
    }
}
FVector AM66BackMist::PuffCenter(const FVector& Origin,const FVector& Drift,float Age,float FloorZ) const
{
    // Identical to BackSmokeV12/author_smoke.py: finite horizontal travel,
    // acceleration into a 38 cm/s sink, then accumulation above the floor.
    FVector Point=Origin+Drift*(2.2f*(1.f-FMath::Exp(-Age/2.2f)));
    Point.Z=FMath::Max(FloorZ+55.f,float(Origin.Z)-38.f*(Age-.5f*(1.f-FMath::Exp(-Age*2.f))));
    return Point;
}
float AM66BackMist::CoreRadiusFraction(float NormalizedAge) const
{return .06f+.30f*FMath::Sqrt(NormalizedAge);}
