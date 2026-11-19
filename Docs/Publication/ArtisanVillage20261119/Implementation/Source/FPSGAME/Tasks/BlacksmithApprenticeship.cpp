#include "BlacksmithApprenticeship.h"
#include "ApprenticeMaterials.h"
#include "../Building/ForgingSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

namespace BlacksmithApprenticeship
{
static const FString SuppliesReceipt = TEXT("village.blacksmith.lesson.materials.v1");

static bool IsLessonWeapon(const FColdSteelForgeJob& Job)
{
    return !Job.Id.IsEmpty() && Job.Recipe == TargetRecipe && Job.Item.Definition == TEXT("ue_tang_dao");
}

static EStage WorkpieceStage(const FColdSteelForgeJob& Job)
{
    if (!IsLessonWeapon(Job)) return EStage::Materials;
    if (!Job.bFinished) return EStage::Hammering;
    return (Job.bHammeredBlank || Job.Hits > 0) ? EStage::Finish : EStage::Materials;
}

EStage Stage(const FColdSteelProfile& Profile)
{
    const uint8 Value = Profile.BlacksmithApprenticeshipStage;
    const EStage Saved = Value <= uint8(EStage::Complete) ? EStage(Value) : EStage::NotStarted;
    const bool bReceivedSupplies = Profile.CampfireWorldReceipts.Contains(SuppliesReceipt);
    if (Saved == EStage::NotStarted && bReceivedSupplies)
        return WorkpieceStage(Profile.ForgeJob);
    // Old active saves could track a different recipe, or treat a discard as progress.
    if (Saved != EStage::NotStarted && Saved != EStage::Complete && !bReceivedSupplies)
        return WorkpieceStage(Profile.ForgeJob);
    return Saved;
}

bool NeedsSupplies(const FColdSteelProfile& Profile)
{
    return Stage(Profile) != EStage::Complete && !Profile.CampfireWorldReceipts.Contains(SuppliesReceipt);
}

void WorkpieceUpdated(FColdSteelProfile& Profile)
{
    const EStage Current = Stage(Profile);
    if (Current != EStage::NotStarted && Current != EStage::Complete)
        Profile.BlacksmithApprenticeshipStage = uint8(WorkpieceStage(Profile.ForgeJob));
}

void WorkpieceRemoved(FColdSteelProfile& Profile, bool bClaimed)
{
    const EStage Current = Stage(Profile);
    if (Current == EStage::NotStarted || Current == EStage::Complete) return;
    const bool Earned = bClaimed && WorkpieceStage(Profile.ForgeJob) == EStage::Finish;
    Profile.BlacksmithApprenticeshipStage = uint8(Earned ? EStage::Complete : EStage::Materials);
}

void NormalizeImportedProfile(FColdSteelProfile& Profile)
{
    Profile.BlacksmithApprenticeshipStage = uint8(Stage(Profile));
    WorkpieceUpdated(Profile);
}

bool Accept(UColdSteelStatusModel* Model, const FString& HostSlot, FString& Message)
{
    const auto* Pawn = Model ? Model->RuntimePawn() : nullptr;
    if (!Pawn || !Pawn->HasAuthority() || !Model->GetWorld() || Model->GetWorld()->GetNetMode() == NM_Client)
    {
        Message = TEXT("角色档案正在同步，请稍后再试。");
        return false;
    }
    const auto& Current = Model->ProfileView();
    if (!NeedsSupplies(Current))
    {
        Message = Stage(Current) == EStage::Complete ? TEXT("打铁修炼已完成。") : TEXT("教学材料已经领过。请亲手锻出唐刀，然后领取成品。");
        return true;
    }
    const auto* Workstation = Model->GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();
    TArray<FColdSteelCraftingInput> Inputs;
    if (!Workstation || !Workstation->InputsFor(TargetRecipe, TEXT("ironIngot"), Inputs))
    {
        Message = TEXT("唐刀的教学配方暂未就绪，请稍后再来。");
        return false;
    }
    Model->SyncRuntime();
    auto Next = Model->Snapshot();
    Next.BlacksmithApprenticeshipStage = uint8(WorkpieceStage(Next.ForgeJob));
    if (!ApprenticeMaterials::Grant(*Model, MoveTemp(Next), HostSlot, SuppliesReceipt, Inputs, Message)) return false;
    Message += TEXT("请亲手锻出唐刀，然后领取成品。");
    return true;
}
}

void AColdSteelPlayerState::ClientBlacksmithLesson_Implementation(FGuid ProfileId,uint8 StageValue)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(GetNetMode()!=NM_Client||!PC||!PC->IsLocalController()||PC->PlayerState!=this)return;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Model->GetWorld()!=GetWorld()||!ProfileId.IsValid()||Model->Current.NetworkProfileId!=ProfileId
        ||StageValue>uint8(BlacksmithApprenticeship::EStage::Complete)||Model->Current.BlacksmithApprenticeshipStage==StageValue)return;
    Model->Current.BlacksmithApprenticeshipStage=StageValue;
    Model->bTrainingDirty=true;
    Model->NotifyChanged();
}
