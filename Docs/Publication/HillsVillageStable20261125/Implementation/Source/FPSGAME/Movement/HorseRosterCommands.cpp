#include "HorseRiderComponent.h"
#include "StableRidingHorse.h"
#include "PlayerKnockdownComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "EngineUtils.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"

namespace
{
bool UnboundLegacyClaim(const APawn* Keeper,const AStableRidingHorse& Horse)
{
    // Before R24 a profile could reserve one of two stalls without holding its live actor.
    for(auto It=Keeper->GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        const APawn* Other=It->IsValid()?It->Get()->GetPawn():nullptr;
        if(!Other||Other==Keeper)continue;
        const auto* Model=ColdSteelAuthority::ForPawn(Other);
        const auto* Legacy=Model?Model->ProfileView().MountRoster.Find(FStableMountRecord::LegacyId(Model->ProfileView().NetworkProfileId,Horse.HomeStall())):nullptr;
        if(Legacy&&(!Legacy->SourceResident.IsValid()||Legacy->SourceResident==Horse.SourceIdentity()))return true;
    }
    return false;
}
}

int64 UHorseRiderComponent::HorseUtcNow() const
{
    if(GetNetMode()!=NM_Client||!ServerUtcSample)return FDateTime::UtcNow().GetTicks();
    return ServerUtcSample+FTimespan::FromSeconds(FPlatformTime::Seconds()-ClockSampleSeconds).GetTicks();
}
void UHorseRiderComponent::ClientHorseClock_Implementation(int64 UtcTicks,double ServerSeconds)
{
    const double Transit=FMath::Clamp(double(Clock())-ServerSeconds,0.,2.);
    ServerUtcSample=UtcTicks+FTimespan::FromSeconds(Transit).GetTicks();
    ClockSampleSeconds=FPlatformTime::Seconds();
}
void UHorseRiderComponent::ServerRequestHorseClock_Implementation()
{
    ClientHorseClock(FDateTime::UtcNow().GetTicks(),Clock());
}
bool UHorseRiderComponent::MayUseResident(AStableRidingHorse& Horse)
{
    auto* Pawn=Player.Get();
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Pawn||!Model||!Horse.ResolveIdentity())return false;
    const auto& P=Model->ProfileView();
    if(!P.NetworkProfileId.IsValid())return false;
    if((Horse.Keeper().IsValid()&&Horse.Keeper()!=P.NetworkProfileId) ||
        (!Horse.Keeper().IsValid()&&Horse.HomeStall()&&UnboundLegacyClaim(Pawn,Horse)))
    {ClientHorseNotice(TEXT("这匹马已有主人"));return false;}
    auto* Entry=P.MountRoster.Find(Horse.Identity());
    if(!Entry&&!Horse.Keeper().IsValid()&&Horse.HomeStall())
    {
        const auto* Old=P.MountRoster.Find(FStableMountRecord::LegacyId(P.NetworkProfileId,Horse.HomeStall()));
        if(Old&&(!Old->SourceResident.IsValid()||Old->SourceResident==Horse.SourceIdentity()))Entry=Old;
    }
    if(Entry)
    {
        if(Entry->Health<=0.f||Entry->Cooling(HorseUtcNow()))
        {ClientHorseNotice(TEXT("这匹马正在休养，请在马匹栏查看"));return false;}
        for(TActorIterator<AStableRidingHorse> It(GetWorld());It;++It)
            if(*It!=&Horse && It->HasActiveKeeper() && It->Identity()==Entry->HorseId)
            {ClientHorseNotice(TEXT("这匹马已在场内"));return false;}
    }
    return true;
}
bool UHorseRiderComponent::ClaimHorse(AStableRidingHorse& Horse)
{
    auto* Pawn=Player.Get();
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Model||!Horse.ResolveIdentity())return false;
    const auto Profile=Model->ProfileView().NetworkProfileId;
    auto Book=Model->ProfileView().MountRoster;
    auto* Former=GetOwnedHorse();
    if(IsValid(Former) && Former!=&Horse && Former->Visit()!=EStableHorseVisit::Present)
    {ClientHorseNotice(TEXT("请等马匹进出完成"));return false;}
    FGuid Id=Horse.Identity();
    if(!Horse.Keeper().IsValid() && Horse.HomeStall())
    {
        const FGuid Legacy=FStableMountRecord::LegacyId(Profile,Horse.HomeStall());
        const auto* Old=Book.Find(Legacy);
        if(Old&&(!Old->SourceResident.IsValid()||Old->SourceResident==Horse.SourceIdentity()))Id=Legacy;
    }
    if(Former==&Horse && Book.Deployed==Id)return true;
    if(IsValid(Former)&&!Former->IsRetreating())
        if(auto* Prior=Book.Find(Former->Identity()))*Prior=Former->Condition();
    FStableMountRecord Entry=Horse.Condition();
    if(const auto* Saved=Book.Find(Id))Entry=*Saved;
    else {Entry.HorseId=Id;Book.Horses.Add(Entry);}
    Entry.SourceResident=Horse.SourceIdentity();*Book.Find(Id)=Entry;
    Book.Deployed=Id;
    // Write the deed first. If the inventory save fails, only this owner may retry
    // on the same resident and finish registering the same ID.
    if(!Horse.RecordClaim(Profile,Id,Entry.BirthVersion)||!Model->CommitMountRoster(MoveTemp(Book)))
    {ClientHorseNotice(TEXT("马匹归属保存失败，请重试"));return false;}
    if(IsValid(Former)&&Former!=&Horse&&!Former->IsRetreating())Former->BeginVisit(EStableHorseVisit::Departing,Pawn);
    Horse.RestoreCondition(Entry);Horse.SetKeeper(*Model,Entry);
    OwnedHorse=&Horse;Pawn->ForceNetUpdate();
    ClientHorseNotice(Entry.DisplayName()+TEXT("已出战"));return true;
}

void UHorseRiderComponent::ClientMountRoster_Implementation(FGuid Profile,const FStableMountRoster& Roster)
{
    if(auto* Model=ColdSteelAuthority::ForPawn(Player.Get()))Model->ReceiveMountRoster(Profile,Roster);
}

void UHorseRiderComponent::ClientHorseNotice_Implementation(const FString& Message)
{
    if(auto* Model=ColdSteelAuthority::ForPawn(Player.Get()))Model->PostNotice(TEXT("马匹"),Message);
}
void UHorseRiderComponent::ToggleOwnedHorse()
{
    auto* PC=Player.IsValid()?Cast<AFPSGAMEPlayerController>(Player->GetController()):nullptr;
    if(!PC||!PC->IsLocalController()||PC->bShowMouseCursor||PC->IsGameMenuOpen()||PC->IsInBuildMode()||
        PC->IsActionPreservingPanelOpen()||AFPSGAMEPlayerController::BlocksOngoingActions(PC))return;
    FVector Eye;FRotator Look;
    PC->GetPlayerViewPoint(Eye,Look);
    int32 Width=0,Height=0;
    PC->GetViewportSize(Width,Height);
    float HalfVerticalFov=90.f;
    if(Width>0 && Height>0 && PC->PlayerCameraManager)
    {
        const float HalfHorizontal=FMath::DegreesToRadians(PC->PlayerCameraManager->GetFOVAngle()*.5f);
        HalfVerticalFov=FMath::RadiansToDegrees(FMath::Atan(FMath::Tan(HalfHorizontal)*float(Height)/Width));
    }
    ServerToggleMount(Eye,Look,HalfVerticalFov);
}
void UHorseRiderComponent::ServerSelectMount_Implementation(FGuid Id)
{
    auto* Model=ColdSteelAuthority::ForPawn(Player.Get());
    if(!Model||Active())return;
    auto Book=Model->ProfileView().MountRoster;
    if(Id==Book.Deployed || (Id.IsValid()&&!Book.Find(Id)))return;
    auto* Former=GetOwnedHorse();
    if(IsValid(Former)&&!Former->IsRetreating())
    {
        if(Former->GetRider()||Former->Visit()==EStableHorseVisit::Arriving)return;
        if(auto* Entry=Book.Find(Former->Identity()))*Entry=Former->Condition();
    }
    Book.Deployed=Id;
    if(!Model->CommitMountRoster(MoveTemp(Book))){ClientHorseNotice(TEXT("出战选择保存失败"));return;}
    if(IsValid(Former)&&!Former->IsRetreating()&&Former->Visit()==EStableHorseVisit::Present)
        Former->BeginVisit(EStableHorseVisit::Departing,Player.Get());
    OwnedHorse=nullptr;LedHorse.Reset();Player->ForceNetUpdate();
}
void UHorseRiderComponent::ServerToggleMount_Implementation(FVector_NetQuantize Eye,FRotator Look,float HalfVerticalFov)
{
    auto* Pawn=Player.Get();
    auto* PC=Pawn?Cast<AFPSGAMEPlayerController>(Pawn->GetController()):nullptr;
    if(!PC||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||UPlayerKnockdownComponent::IsKnockedDown(Pawn)||
        bAwaitingHorseImpact||PC->IsInBuildMode())return;
    const auto* Life=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if((Life&&Life->IsDead())||Look.ContainsNaN()||Eye.ContainsNaN()||!FMath::IsFinite(HalfVerticalFov)||
        FVector::DistSquared(Eye,Pawn->GetActorLocation())>FMath::Square(2000.f))return;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now<NextHorseCall)return;
    NextHorseCall=Now+.35;
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Model || !Model->ProfileView().NetworkProfileId.IsValid())return;
    const auto& Roster=Model->ProfileView().MountRoster;
    const auto* Entry=Roster.Find(Roster.Deployed);
    if(!Entry){ClientHorseNotice(Roster.Horses.IsEmpty()?TEXT("先靠近马匹，点按 E 让它跟随"):TEXT("请先在马匹栏选择出战马匹"));return;}
    if(Entry->Health<=0.f){ClientHorseNotice(TEXT("马匹已逃离，请在马匹栏使用生命药水"));return;}
    if(Entry->Cooling(HorseUtcNow())){ClientHorseNotice(TEXT("马匹休养中，请等待召唤冷却结束"));return;}
    auto* Live=GetOwnedHorse();
    const bool RecallingFar=IsValid(Live)&&Live->Identity()==Entry->HorseId&&!Live->GetRider()&&
        Live->Visit()==EStableHorseVisit::Present&&!Live->IsRetreating()&&(Live->NeedsRecall()||Live->IsFarFrom(*Pawn));
    if(IsValid(Live) && !Live->IsRetreating() && !RecallingFar)
    {
        if(Live->Visit()!=EStableHorseVisit::Present || Transferring())return;
        if(Live->Keeper()!=Model->ProfileView().NetworkProfileId || Live->Identity()!=Roster.Deployed)return;
        if(Active() && State.Horse!=Live)return;
        if(Live->GetRider() && Live->GetRider()!=Pawn)return;
        if(Live->InJump()||Live->GetCharacterMovement()->IsFalling())return;
        auto Saved=Roster;
        *Saved.Find(Roster.Deployed)=Live->Condition();
        if(!Model->CommitMountRoster(MoveTemp(Saved))){ClientHorseNotice(TEXT("马匹状态保存失败"));return;}
        if(Active())
        {
            ServerUse_Implementation(Live,true);
            if(State.Phase==ERiderPhase::Dismounting)DismissAfterDismount=Live;
            else ClientHorseNotice(TEXT("此处无法安全下马"));
            return;
        }
        Live->BeginVisit(EStableHorseVisit::Departing,Player.Get());
        return;
    }
    if(Active()||!Pawn->GetCharacterMovement()->IsMovingOnGround())return;
    AStableRidingHorse* Resident=RecallingFar?Live:nullptr;
    if(!Resident)
    {
        for(TActorIterator<AStableRidingHorse> It(GetWorld());It;++It)
        {
            auto* Candidate=*It;
            if(!Candidate->ResolveIdentity())continue;
            const bool Legacy=!Entry->SourceResident.IsValid() && !Candidate->Keeper().IsValid() &&
                Candidate->SourceIdentity().IsValid() && Candidate->HomeStall()==Entry->Stall &&
                Entry->HorseId==FStableMountRecord::LegacyId(Model->ProfileView().NetworkProfileId,Entry->Stall);
            if(Candidate->Identity()!=Entry->HorseId&&!Legacy)continue;
            if(Candidate->Keeper().IsValid() && Candidate->Keeper()!=Model->ProfileView().NetworkProfileId)
            {ClientHorseNotice(TEXT("这匹马已有主人"));return;}
            if(Candidate->IsRetreating()||Candidate->Visit()!=EStableHorseVisit::Present||
                Candidate->GetRider()||Candidate->GetLeader())
            {ClientHorseNotice(TEXT("请等马匹进出完成"));return;}
            Resident=Candidate;
            if(Candidate->HasActiveKeeper())break;
        }
    }
    FStableMountRecord Condition=Resident&&Resident->HasActiveKeeper()?Resident->Condition():*Entry;
    FTransform Spawn;
    if(!FindRecallSpot(Eye,Look,HalfVerticalFov,Resident,Spawn)){ClientHorseNotice(TEXT("视野外没有能通行的空地"));return;}
    if(Resident)
    {
        if(Resident->SourceIdentity().IsValid() && !Resident->RecordClaim(Model->ProfileView().NetworkProfileId,Condition.HorseId,Condition.BirthVersion))
        {ClientHorseNotice(TEXT("马匹归属保存失败，请重试"));return;}
        if(Resident->SourceIdentity().IsValid() && !Condition.SourceResident.IsValid())
        {
            Condition.SourceResident=Resident->SourceIdentity();
            auto Bound=Roster;*Bound.Find(Condition.HorseId)=Condition;
            if(!Model->CommitMountRoster(MoveTemp(Bound)))return;
        }
        if(!Resident->TeleportTo(Spawn.GetLocation(),Spawn.Rotator(),false,true))return;
    }
    else
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
        Resident=GetWorld()->SpawnActor<AStableRidingHorse>(Spawn.GetLocation(),Spawn.Rotator(),Params);
    }
    if(!Resident){ClientHorseNotice(TEXT("召唤位置已被占用"));return;}
    Resident->SetKeeper(*Model,Condition);
    if(!RecallingFar)Resident->RestoreCondition(Condition);
    OwnedHorse=Resident;LedHorse=Resident;Pawn->ForceNetUpdate();
    Resident->BeginVisit(EStableHorseVisit::Arriving,Pawn);
}
