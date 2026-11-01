#include "ProductionToolComponent.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerTuning.h"
#include "ProductionToolMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Skills/FPSMagicPreview.h"
#include "Components/LineBatchComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"

bool UProductionToolComponent::IsThunderHammerAway() const
{
    if(ThunderAwayInstance.IsEmpty())return false;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    return Item&&Item->InstanceId==ThunderAwayInstance;
}
bool UProductionToolComponent::HandleThunderPrimary()
{
    if(!IsThunderHammerAway())return false;
    if(IsEquipped()&&CanPresent()&&HasReadyPresentation()&&ThrownHammer&&ThrownHammer->IsGrounded()&&!Character->IsCastBlockingLeftHandAction())
    {
        ThunderActionInstance=ThunderAwayInstance;
        bThunderRecallPending=true;ThunderReachAge=0.f;FinishUse();ServerRecallThunderHammer();
    }
    return true;
}
void UProductionToolComponent::ServerRecallThunderHammer_Implementation()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    if(!Pawn||!PC||!Item||Item->InstanceId!=ThunderAwayInstance||!ThrownHammer||ThrownHammer->GetOwner()!=Pawn||!ThrownHammer->IsGrounded()||
        (Health&&Health->IsDead())||Pawn->IsTraversing()||Pawn->IsCastBlockingLeftHandAction()||
        AFPSGAMEPlayerController::BlocksOngoingActions(PC)||(Building&&Building->IsBuilding())){ClientThunderRecallRejected();return;}
    ThunderActionInstance=ThunderAwayInstance;ThrownHammer->Recall();
}
void UProductionToolComponent::ClientThunderRecallRejected_Implementation()
{bThunderRecallPending=false;ThunderReachAge=-1.f;}
bool UProductionToolComponent::LaunchThunderHammer(const FColdSteelSkillShot& Shot,float Magic)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Pawn->HasAuthority()||ThrownHammer)return false;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||Item->InstanceId!=Shot.ItemInstance||!ThunderHammerThrow::Installed(*Item,Profile))return false;
    FActorSpawnParameters Params;Params.Owner=Pawn;Params.Instigator=Pawn;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Hammer=GetWorld()->SpawnActor<AThunderHammerThrown>(FVector::ZeroVector,FRotator::ZeroRotator,Params);
    if(!Hammer)return false;
    ThrownHammer=Hammer;ThunderAwayInstance=Item->InstanceId;ThunderCatchStartedAt=-100.;
    Hammer->Launch(*Item,Shot,Magic);Pawn->ForceNetUpdate();return true;
}
void UProductionToolComponent::ThunderHammerReturned(AThunderHammerThrown* Hammer,bool bCaught)
{
    // Only this actor's live instance can clear the current flight/receipt.
    if(ThrownHammer!=Hammer)return;
    const bool Equipped=IsThunderHammerAway();ThrownHammer=nullptr;ThunderAwayInstance.Reset();
    if(bCaught)
    {
        const float Age=Hammer?Hammer->CatchAge():0.f;ThunderCatchStartedAt=RuneboundClock()-Age;
        if(Equipped)ThunderCatchAge=Age;
        if(GetOwner()->HasAuthority())BluntServerReadyAt=FMath::Max(BluntServerReadyAt,double(GetWorld()->GetTimeSeconds()+FMath::Max(0.f,ThunderHammerThrow::CatchSeconds-Age)));
    }
    else
    {
        ThunderCatchStartedAt=-100.;ThunderCatchAge=-1.f;bThunderSwitchQueued=false;
        ThunderActionInstance.Reset();
    }
    ThunderReachAge=-1.f;
    bThunderRecallPending=false;
    // The projectile ticks after the arms. Restore the held assembly here so
    // retiring it cannot leave one rendered frame with an empty closed hand.
    if(bCaught&&Equipped&&CanPresent()&&HasReadyPresentation()&&ToolMesh&&Viewmodel)
    {
        PresentThunderCatch(0.f);
        ToolMesh->UpdateComponentToWorld();
        ToolMesh->SetVisibility(true,true);Viewmodel->SetVisibility(true);
    }
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
}
void UProductionToolComponent::OnRep_ThunderAway(const FString& Previous)
{
    if(!ThunderAwayInstance.IsEmpty())return;
    bThunderRecallPending=false;ThunderReachAge=-1.f;
    const auto* Profile=ColdSteelAuthority::ForPawn(Cast<AFPSGAMECharacter>(GetOwner()));
    const auto* Active=Profile?Profile->ActiveProductionTool():nullptr;
    const bool Caught=ThunderCatchStartedAt>=0.&&RuneboundClock()-ThunderCatchStartedAt<ThunderHammerThrow::CatchSeconds;
    if(!Previous.IsEmpty()&&Active&&Active->InstanceId==Previous)
    {
        if(Caught)ThunderCatchAge=FMath::Max(0.f,float(RuneboundClock()-ThunderCatchStartedAt));
        else {ThunderCatchAge=-1.f;bThunderSwitchQueued=false;}
    }
}
void UProductionToolComponent::OnRep_ThunderCatch()
{
    if(ThunderCatchStartedAt<0.)return;
    const float Age=FMath::Max(0.f,float(RuneboundClock()-ThunderCatchStartedAt));
    if(ThunderAwayInstance.IsEmpty()&&IsWarhammerEquipped()&&Age<ThunderHammerThrow::CatchSeconds)
    {ThunderCatchAge=Age;}
}
void UProductionToolComponent::TickThunderThrow(float Delta)
{
    ServiceThunderLifecycle();
    if(!Character.IsValid()||!Character->IsLocallyControlled())
    {FPSMagicPreview::Clear(ThunderPreview);ThunderPreviewWait=0.f;return;}
    const auto* Profile=ColdSteelAuthority::ForPawn(Character.Get());
    const bool Preview=bThunderThrowSeat&&bBluntCharging&&HeavyChargeFraction()>=1.f-UE_SMALL_NUMBER&&CanUse()&&
        Profile&&Profile->CanSpendStamina(float(ToolStats.HeavyReleaseStaminaCost));
    if(!Preview){FPSMagicPreview::Clear(ThunderPreview);ThunderPreviewWait=0.f;return;}
    ThunderPreviewWait-=Delta;if(ThunderPreviewWait>0.f)return;ThunderPreviewWait=.05f;
    FVector P,V;ThunderHammerThrow::Launch(Character.Get(),P,V,Profile->ActiveProductionTool());ThunderPreviewPoints.Reset();ThunderPreviewPoints.Add(P);
    FHitResult Landing;bool bHasLanding=false;
    for(int32 I=0;I<240;++I)
    {
        FHitResult Floor;const bool Ground=ThunderHammerThrow::Advance(Character.Get(),nullptr,P,V,Floor);
        ThunderPreviewPoints.Add(Ground?Floor.ImpactPoint:P);
        if(Ground){Landing=Floor;bHasLanding=true;break;}
    }
    FPSMagicPreview::BeginRefresh(ThunderPreview,Character.Get());
    // Unlike the off-centre hovering spells, this release sits on the sight
    // axis. Keep the short lead-in visible and give its narrow projection more
    // weight, without moving the predicted trajectory away from real flight.
    FPSMagicPreview::DrawPath(ThunderPreview,ThunderPreviewPoints,3.2f,.6f);
    if(bHasLanding)
    {
        // A compact contact marker remains readable when looking straight
        // down, where an accurate ballistic arc projects almost to a point.
        // This identifies the impact centre, not the thunder damage radius.
        FVector X,Y;Landing.ImpactNormal.FindBestAxisVectors(X,Y);
        const FVector Center=Landing.ImpactPoint+Landing.ImpactNormal*2.f;
        constexpr int32 Segments=24;constexpr float MarkerRadius=18.f;
        for(int32 I=0;I<Segments;++I)
        {
            const float A=2.f*PI*I/Segments,B=2.f*PI*(I+1)/Segments;
            ThunderPreview->DrawLine(Center+(X*FMath::Cos(A)+Y*FMath::Sin(A))*MarkerRadius,
                Center+(X*FMath::Cos(B)+Y*FMath::Sin(B))*MarkerRadius,FPSMagicPreview::LineColor(),0,3.2f,0.f);
        }
    }
}
bool UProductionToolComponent::PresentThunderCatch(float Delta)
{
    const bool Returning=IsThunderHammerAway()&&ThrownHammer&&ThrownHammer->IsReturning();
    const bool Docking=IsThunderHammerAway()&&ThrownHammer&&ThrownHammer->IsCatching();
    const bool Waiting=Returning||(IsThunderHammerAway()&&bThunderRecallPending&&!Docking);
    if(!Waiting&&!Docking&&ThunderCatchAge<0.f)return false;
    if(!Viewmodel||!Motions.FindRef(TEXT("ThunderCatch")))return false;
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if(auto* Arms=Cast<UProductionToolMeshComponent>(Viewmodel))Arms->SetFloorContact(FVector::ZeroVector,0.f);
    if(Waiting)
    {
        // Re-entering this weapon during its return restores the local catch
        // receipt too, even if the short replicated docking phase is skipped.
        if(Returning)bThunderRecallPending=true;
        ThunderReachAge=FMath::Max(0.f,ThunderReachAge)+Delta;
        if(Returning)ThunderReachAge=FMath::Max(ThunderReachAge,ThrownHammer->RecallAge());
        // The first .32 s extends the right palm; its following one-second
        // authored hold contains a small hand-only tremor and loops smoothly.
        const float Ready=ThunderHammerThrow::RecallReadySeconds;
        const float Sample=ThunderReachAge<=Ready?ThunderReachAge:
            Ready+FMath::Fmod(ThunderReachAge-Ready,1.f);
        SampleMotion(TEXT("ThunderRecallReady"),Sample);return true;
    }
    if(Docking)
    {ThunderCatchAge=ThrownHammer->CatchAge();ThunderCatchStartedAt=RuneboundClock()-ThunderCatchAge;}
    else ThunderCatchAge=FMath::Max(ThunderCatchAge,float(RuneboundClock()-ThunderCatchStartedAt));
    SampleMotion(TEXT("ThunderCatch"),ThunderCatchAge);
    if(!Docking&&ThunderCatchAge>=ThunderHammerThrow::CatchSeconds)ThunderCatchAge=-1.f;
    return true;
}
bool UProductionToolComponent::GetThunderCatchFrame(FTransform& Frame) const
{
    if(!Viewmodel||!ToolMesh||!IsEquipped())return false;
    const bool Ready=CurrentMotion&&CurrentMotion==Motions.FindRef(TEXT("ThunderRecallReady"))&&Viewmodel->GetPosition()>=ThunderHammerThrow::RecallReadySeconds-.002f;
    const bool Catching=CurrentMotion&&CurrentMotion==Motions.FindRef(TEXT("ThunderCatch"));
    if(!Ready&&!Catching)return false;
    // Read the freshly sampled bone directly: child component transforms may
    // still belong to the previous frame until attachment propagation runs.
    const auto T=ToolMesh->GetRelativeTransform()*Viewmodel->GetSocketTransform(TEXT("WPN_root"));
    Frame=FTransform(T.GetRotation(),T.TransformPosition(FVector(0,0,ThunderHammerThrow::CenterZ)));return true;
}
