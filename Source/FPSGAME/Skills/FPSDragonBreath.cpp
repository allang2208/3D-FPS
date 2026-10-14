#include "FPSFireMagicComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "FPSFireballComponent.h"
#include "FireMagicArea.h"
#include "MagicOcclusion.h"
#include "HolyLightTargets.h"
#include "NetCastUtils.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Scalability.h"

namespace
{
constexpr float DragonVisualTailSeconds=.65f;
FVector DragonFluidCenter(const FVector& Origin,const FQuat& Rotation,float Range)
{
    return Origin+Rotation.GetForwardVector()*(FMath::Clamp(Range,500.f,1500.f)*.46f);
}
double DragonClock(UWorld* World)
{
    const auto* State=World?World->GetGameState<AGameStateBase>():nullptr;
    return State?State->GetServerWorldTimeSeconds():World?World->GetTimeSeconds():0.;
}
}

void UFPSFireMagicComponent::LoadDragonBreath()
{
    const FSoftObjectPath Path(TEXT("/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume.NS_DragonVolume"));
    DragonLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,FSimpleDelegate::CreateWeakLambda(this,[this,Path]()
    {DragonSystem=Cast<UNiagaraSystem>(Path.ResolveObject());OnRep_DragonBreath();}));
}

const FDragonBreathState& UFPSFireMagicComponent::DragonView() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    return Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled()?DragonPrediction:DragonState;
}

bool UFPSFireMagicComponent::IsDragonBreathActive() const{return DragonView().bActive;}

FVector UFPSFireMagicComponent::CaptureDragonNozzle() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn)return FVector(95,17,4);
    FVector Tip;
    if(const auto* H=Hands();H&&H->TryStaffCastOrigin(Tip))
        return Pawn->GetBaseAimRotation().UnrotateVector(Tip-Pawn->GetPawnViewLocation());
    return FVector(95,17,4);
}

void UFPSFireMagicComponent::DragonBreathFrame(FVector& Origin,FQuat& Rotation) const
{
    auto* Pawn=Cast<APawn>(GetOwner());
    Rotation=Pawn?Pawn->GetBaseAimRotation().Quaternion():GetOwner()->GetActorQuat();
    const FVector Eye=Pawn?Pawn->GetPawnViewLocation():GetOwner()->GetActorLocation();
    Origin=Eye+Rotation.RotateVector(DragonView().NozzleOffset);
    FHitResult Wall;
    // Do not let a staff protruding through a wall become an origin behind it.
    if(FireMagic::TraceSurface(Pawn,Eye,Origin,Wall,true))Origin=Eye;
}

bool UFPSFireMagicComponent::StartDragonBreath(const FFireMagicCast& Spell,bool bPredict,uint32 CastId,const FVector& NozzleOffset)
{
    if(IsDragonBreathActive()||(!DragonSystem&&GetWorld()->GetNetMode()!=NM_DedicatedServer))return false;
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* Profile=bPredict?Model():NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance());
    if(!Pawn||!Profile||!Profile->HasEquippedStaff())return false;
    if(const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead())return false;
    if(UBoundCongregateCaptureComponent::IsCaptured(Pawn))return false;
    if(const auto* Status=Pawn->FindComponentByClass<UCombatStatusFormula>();Status&&Status->BlocksMovement())return false;
    // Finite, physically bounded tip offset; eye-to-tip obstruction is still
    // resolved every frame by DragonBreathFrame on authority and observers.
    if(NozzleOffset.ContainsNaN()||NozzleOffset.X<0||NozzleOffset.X>140||
        FMath::Abs(NozzleOffset.Y)>65||FMath::Abs(NozzleOffset.Z)>85||NozzleOffset.SizeSquared()>FMath::Square(170.f))return false;
    if(bPredict&&!CastId)return false;
    if(!bPredict&&!Profile->CommitDragonBreathRelease())return false;
    if(!CastId){CastId=++DragonAuthoritySerial;if(!CastId)CastId=++DragonAuthoritySerial;}
    DragonRewards=FFireMagicRewards();DragonNextDamage=0;DragonProbeClock=0;
    auto& State=bPredict?DragonPrediction:DragonState;
    State.Cast=Spell;State.StartedAt=DragonClock(GetWorld());State.CastId=CastId;
    State.NozzleOffset=NozzleOffset;State.bActive=true;
    if(!bPredict)DragonRewardModel=Profile;
    bDragonGestureHeld=Pawn->IsLocallyControlled();PresentDragonBreath();
    if(Pawn->IsLocallyControlled())if(auto* H=Hands())H->ContinueSpellRelease(this,Spell.Duration,false);
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    return true;
}

void UFPSFireMagicComponent::OnRep_DragonBreath()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled())
    {
        // A newer spell must not consume this cast's receipt; a cancelled or
        // older cast must not recreate the predicted flame/gesture either.
        if(!DragonState.CastId||DragonState.CastId!=DragonLocalCastId)return;
        ConfirmDragonRelease(DragonState.CastId);
        if(DragonCancelledCastId==DragonState.CastId)return;
        DragonPrediction=DragonState;
    }
    PresentDragonBreath();
}

void UFPSFireMagicComponent::PlayDragonStartSound()
{
    const auto& State=DragonView();
    if(!State.bActive||!State.CastId||DragonSoundCastId==State.CastId||!CastSound||GetNetMode()==NM_DedicatedServer)return;
    DragonSoundCastId=State.CastId;
    // Late relevance / asynchronous loading must not replay an old onset.
    if(DragonClock(GetWorld())-State.StartedAt>1.25)return;
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    UGameplayStatics::PlaySoundAtLocation(this,CastSound,Origin);
}

void UFPSFireMagicComponent::PresentDragonBreath()
{
    const auto& State=DragonView();
    if(!State.bActive)
    {
        // Stop fuel births immediately. The bounded fluid grid fades out;
        // this residual heat is purely cosmetic and never causes damage.
        if(DragonFX&&DragonTailTime<=0)
        {
            DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),0.f);
            DragonTailTime=DragonVisualTailSeconds;
        }
        if(bDragonGestureHeld)if(auto* H=Hands())H->CancelSpellGesture(this);
        bDragonGestureHeld=false;
        return;
    }
    PlayDragonStartSound();
    if(DragonFX&&(DragonTailTime>0||DragonVisualCastId!=State.CastId))
    {
        DragonFX->DestroyComponent();DragonFX=nullptr;DragonTailTime=0;
    }
    if(GetWorld()->GetNetMode()==NM_DedicatedServer||!DragonSystem||DragonFX)return;
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    DragonFX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,DragonSystem,DragonFluidCenter(Origin,Rotation,State.Cast.Radius),Rotation.Rotator(),FVector::OneVector,false,false);
    if(!DragonFX)return;
    DragonVisualCastId=State.CastId;
    DragonFX->AddTickPrerequisiteComponent(this);
    DragonFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
    // One bounded volume per caster; remote casts use a smaller grid. Resolution
    // is selected at creation so turning or changing view cannot reallocate it.
    const float VisualRange=FMath::Clamp(State.Cast.Radius,500.f,1500.f);
    const FVector Domain(VisualRange*1.2f+160.f,VisualRange*1.55f+160.f,VisualRange*.65f+200.f);
    static constexpr int32 DragonGridResolutions[]={80,96,128,160,160};
    const auto* VisualPawn=Cast<APawn>(GetOwner());
    const int32 Quality=FMath::Clamp(Scalability::GetQualityLevels().EffectsQuality,0,4);
    const int32 GridResolution=VisualPawn&&VisualPawn->IsLocallyControlled()?DragonGridResolutions[Quality]:80;
    DragonFX->SetVariableVec3(TEXT("User.WorldSpaceSize"),Domain);
    DragonFX->SetVariableInt(TEXT("User.ResolutionMaxAxis"),GridResolution);
    DragonFX->SetVariableFloat(TEXT("User.CellSize"),float(Domain.GetMax())/GridResolution);
    DragonFX->SetVariableBool(TEXT("User.DrawBounds"),false);
    DragonFX->SetVariableFloat(TEXT("User.Range"),State.Cast.Radius);
    DragonFX->SetVariableFloat(TEXT("User.HalfAngle"),FMath::DegreesToRadians(State.Cast.ArcDegrees*.5f));
    DragonFX->SetVariableFloat(TEXT("User.Strength"),1.f);
    DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),1.f);
    DragonFX->SetVariablePosition(TEXT("User.Origin"),Origin);
    DragonFX->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
    DragonFX->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());
    DragonFX->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
    // Publish wall distances before the first particles spawn, including casts
    // started directly next to a wall.
    UpdateDragonBreathOcclusion(Origin,Rotation);
    DragonProbeClock=.10f;
    const FVector Bounds=Domain*.5f+FVector(64.f);
    DragonFX->SetSystemFixedBounds(FBox(-Bounds,Bounds));
    DragonFX->Activate(true);
}

void UFPSFireMagicComponent::DragonBreathHit()
{
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* Profile=NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance());
    if(!Pawn||!Pawn->HasAuthority()||!Profile)return;
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    const auto& C=DragonState.Cast;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DragonBreathArea),false,Pawn);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,Objects,FCollisionShape::MakeSphere(C.Radius+100),Query);
    TSet<AActor*> Seen;int32 Hits=0;
    const float Slope=FMath::Tan(FMath::DegreesToRadians(C.ArcDegrees*.5f));
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();if(!IsValid(Target)||Target==Pawn||Seen.Contains(Target))continue;Seen.Add(Target);
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Pawn,Target))continue;
        MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Origin,Samples);
        bool Exposed=false;
        for(const FVector& Point:Samples)
        {
            const FVector Local=Rotation.UnrotateVector(Point-Origin);
            if(Local.X<0||Local.X*Local.X+Local.Y*Local.Y>FMath::Square(C.Radius)||
                FMath::Abs(Local.Y)>Local.X*Slope||FMath::Abs(Local.Z)>80.f+Local.X*.28f)continue;
            FHitResult Block;if(!FireMagic::TraceSurface(Pawn,Origin,Point,Block,true)){Exposed=true;break;}
        }
        if(!Exposed)continue;
        const int32 Before=DragonRewards.Hits;
        Profile->ApplyFireMagicHit(Pawn,Target,C,C.Damage,DragonRewards);
        Hits+=DragonRewards.Hits-Before;
    }
    DragonRewards.bMultiHit|=Hits>=2;
}

void UFPSFireMagicComponent::TickDragonBreath(float Delta)
{
    if(!IsDragonBreathActive())
    {
        if(DragonFX&&DragonTailTime>0)
        {
            DragonTailTime=FMath::Max(0.f,DragonTailTime-Delta);
            DragonFX->SetVariableFloat(TEXT("User.Strength"),DragonTailTime/DragonVisualTailSeconds);
            if(DragonTailTime<=0){DragonFX->DestroyComponent();DragonFX=nullptr;}
        }
        return;
    }
    auto* Pawn=Cast<APawn>(GetOwner());if(!Pawn){StopDragonBreath(false);return;}
    const auto& State=DragonView();
    const double Age=DragonClock(GetWorld())-State.StartedAt;
    const auto& C=State.Cast;
    if(Pawn->HasAuthority()||Pawn->IsLocallyControlled())
    {
        const auto* Profile=Pawn->HasAuthority()?NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance()):Model();
        const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        const auto* Status=Pawn->FindComponentByClass<UCombatStatusFormula>();
        const bool Dead=HP&&HP->IsDead();
        const bool Interrupted=!Profile||!Profile->HasEquippedStaff()||Dead||UBoundCongregateCaptureComponent::IsCaptured(Pawn)||
            (Status&&Status->BlocksMovement())||(Pawn->IsLocallyControlled()&&(!Hands()||!Hands()->IsSpellGesture(this)));
        if(Interrupted)
        {
            if(Pawn->IsLocallyControlled())RequestDragonStop();
            else StopDragonBreath(!Dead);
            return;
        }
    }
    if(Pawn->HasAuthority())
        while(DragonNextDamage<C.Duration-UE_KINDA_SMALL_NUMBER&&DragonNextDamage<=Age)
        {DragonBreathHit();DragonNextDamage+=C.TickSeconds;}
    if(Age>=C.Duration){StopDragonBreath(true);return;}
    if(Pawn->IsLocallyControlled()&&Hands())Hands()->ContinueSpellRelease(this,.10f,false);
    PlayDragonStartSound();
    if(!DragonFX){PresentDragonBreath();if(!DragonFX)return;}
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    // The template compensates the previous grid transform during advection.
    // Moving/turning the staff changes the source without rigidly dragging fire.
    DragonFX->SetWorldLocationAndRotation(DragonFluidCenter(Origin,Rotation,C.Radius),Rotation);
    DragonFX->SetVariablePosition(TEXT("User.Origin"),Origin);
    DragonFX->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
    DragonFX->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());
    DragonFX->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
    DragonFX->SetVariableFloat(TEXT("User.Strength"),1.f);
    DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),FMath::Min(FMath::Clamp(float(Age)/.08f,0.f,1.f),FMath::Clamp(float(C.Duration-Age)/.12f,0.f,1.f)));
    DragonProbeClock-=Delta;
    if(DragonProbeClock<=0)
    {
        DragonProbeClock=.10f;
        UpdateDragonBreathOcclusion(Origin,Rotation);
    }
}

void UFPSFireMagicComponent::UpdateDragonBreathOcclusion(const FVector& Origin,const FQuat& Rotation)
{
    if(!DragonFX)return;
    auto* Pawn=Cast<APawn>(GetOwner());
    const auto& C=DragonView().Cast;
    static const FName RayNames[]={TEXT("User.Ray0"),TEXT("User.Ray1"),TEXT("User.Ray2"),TEXT("User.Ray3"),TEXT("User.Ray4"),TEXT("User.Ray5"),TEXT("User.Ray6"),TEXT("User.Ray7"),TEXT("User.Ray8")};
    static const FName NormalNames[]={TEXT("User.HitNormal0"),TEXT("User.HitNormal1"),TEXT("User.HitNormal2"),TEXT("User.HitNormal3"),TEXT("User.HitNormal4"),TEXT("User.HitNormal5"),TEXT("User.HitNormal6"),TEXT("User.HitNormal7"),TEXT("User.HitNormal8")};
    for(int32 I=0;I<9;++I)
    {
        const float Angle=FMath::DegreesToRadians(FMath::Lerp(-C.ArcDegrees*.5f,C.ArcDegrees*.5f,I/8.f));
        const FVector Direction=Rotation.RotateVector(FVector(FMath::Cos(Angle),FMath::Sin(Angle),0));
        FHitResult Hit;
        const bool bBlocked=FireMagic::TraceSurface(Pawn,Origin,Origin+Direction*C.Radius,Hit,true);
        DragonFX->SetVariableFloat(RayNames[I],bBlocked?FMath::Max(0.f,Hit.Distance-12.f):C.Radius);
        DragonFX->SetVariableVec3(NormalNames[I],bBlocked?Hit.ImpactNormal.GetSafeNormal():-Direction);
    }
}

void UFPSFireMagicComponent::StopDragonBreath(bool bTrain)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    auto& State=Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled()?DragonPrediction:DragonState;
    const bool WasActive=State.bActive;State.bActive=false;PresentDragonBreath();
    if(!WasActive)return;
    if(GetOwner()->HasAuthority())
    {
        GetOwner()->ForceNetUpdate();
        if(const auto* HP=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead())bTrain=false;
        if(bTrain)if(auto* M=DragonRewardModel.Get())M->FinishFireMagicCast(TEXT("dragonBreath"),DragonRewards);
    }
    DragonRewards=FFireMagicRewards();
    DragonRewardModel.Reset();
}

void UFPSFireMagicComponent::RequestDragonStop()
{
    if(GetNetMode()==NM_Client&&DragonLocalCastId&&DragonCancelledCastId!=DragonLocalCastId)
    {
        DragonCancelledCastId=DragonLocalCastId;
        NetCast::Send(GetOwner(),TEXT("dragonBreath"),4,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,DragonLocalCastId);
    }
    bDragonAwaitingRelease=false;
    StopDragonBreath(true);
}

void UFPSFireMagicComponent::NetStopDragonBreath(uint32 CastId)
{
    if(GetOwner()->HasAuthority()&&CastId&&DragonState.CastId==CastId)StopDragonBreath(true);
}

void UFPSFireMagicComponent::FinishDragonBreathForRemoval()
{
    if(GetOwner()->HasAuthority())StopDragonBreath(true);
}

void UFPSFireMagicComponent::ConfirmDragonRelease(uint32 CastId)
{
    if(!CastId||CastId!=DragonLocalCastId||DragonConfirmedCastId==CastId)return;
    DragonConfirmedCastId=CastId;bDragonAwaitingRelease=false;
    if(auto* M=Model())M->CommitDragonBreathRelease();
    // A delayed receipt must not consume a newer meteor/armor gesture payment.
    if(CommittedSkill.IsNone()&&IsDragonBreathActive())
        if(auto* H=Hands();H&&H->IsSpellGesture(this))H->TakeGesturePayment();
}

void UFPSFireMagicComponent::NetDragonCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=DragonLocalCastId)return;
    if(Code==0)
    {
        if(Phase==1)ConfirmDragonRelease(CastId);
        return;
    }
    if(Phase>1||DragonConfirmedCastId==CastId)return;
    const bool Pending=CommittedSkill==TEXT("dragonBreath");
    const bool Cancelled=DragonCancelledCastId==CastId;
    if(auto* M=Model())M->RefundUnreleasedCast(Pending&&Hands()?Hands()->TakeGesturePayment():0.f,TEXT("dragonBreath"));
    bDragonAwaitingRelease=false;DragonCancelledCastId=CastId;
    StopDragonBreath(false);
    if(Pending){CommittedSkill=NAME_None;bNetPaid=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
    if(QueuedSkill==TEXT("dragonBreath"))QueuedSkill=NAME_None;
    if(!Cancelled)Feedback(TEXT("dragonBreath"),TEXT("施法失败"));
}
