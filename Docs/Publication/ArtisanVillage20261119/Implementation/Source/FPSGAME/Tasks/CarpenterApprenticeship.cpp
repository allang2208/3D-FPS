#include "CarpenterApprenticeship.h"
#include "ApprenticeMaterials.h"
#include "../Building/WoodworkingSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

namespace CarpenterApprenticeship
{
static const FString SuppliesReceipt = TEXT("village.carpenter.lesson.materials.v1");

static bool IsLessonWeapon(const FColdSteelWoodworkingJob& Job)
{
    return !Job.Id.IsEmpty() && Job.Recipe == TargetRecipe && Job.Item.Definition == TEXT("ue_apprentice_staff");
}

static EStage WorkpieceStage(const FColdSteelWoodworkingJob& Job)
{
    if (!IsLessonWeapon(Job)) return EStage::Materials;
    if (!Job.bFinished) return EStage::Working;
    return Job.bPassed ? EStage::Finish : EStage::Materials;
}

EStage Stage(const FColdSteelProfile& Profile)
{
    const uint8 Value = Profile.CarpenterApprenticeshipStage;
    const EStage Saved = Value <= uint8(EStage::Complete) ? EStage(Value) : EStage::NotStarted;
    const bool bReceivedSupplies = Profile.CampfireWorldReceipts.Contains(SuppliesReceipt);
    if (Saved == EStage::NotStarted && bReceivedSupplies)
        return WorkpieceStage(Profile.WoodworkingJob);
    // Old active saves could track a different recipe, or treat a discard as progress.
    if (Saved != EStage::NotStarted && Saved != EStage::Complete && !bReceivedSupplies)
        return WorkpieceStage(Profile.WoodworkingJob);
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
        Profile.CarpenterApprenticeshipStage = uint8(WorkpieceStage(Profile.WoodworkingJob));
}

void WorkpieceRemoved(FColdSteelProfile& Profile, bool bClaimed)
{
    const EStage Current = Stage(Profile);
    if (Current == EStage::NotStarted || Current == EStage::Complete) return;
    const bool Earned = bClaimed && WorkpieceStage(Profile.WoodworkingJob) == EStage::Finish;
    Profile.CarpenterApprenticeshipStage = uint8(Earned ? EStage::Complete : EStage::Materials);
}

void NormalizeImportedProfile(FColdSteelProfile& Profile)
{
    Profile.CarpenterApprenticeshipStage = uint8(Stage(Profile));
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
        Message = Stage(Current) == EStage::Complete ? TEXT("木工修炼已完成。") : TEXT("教学材料已经领过。请锯出一把学徒长杖，达到图样要求后领取成品。");
        return true;
    }
    const auto* Workstation = Model->GetWorld()->GetGameInstance()->GetSubsystem<UWoodworkingSystem>();
    TArray<FColdSteelCraftingInput> Inputs;
    if (!Workstation || !Workstation->RecipeInputs(TargetRecipe, TEXT("wood_core_plain"), Inputs))
    {
        Message = TEXT("学徒长杖的教学配方暂未就绪，请稍后再来。");
        return false;
    }
    Model->SyncRuntime();
    auto Next = Model->Snapshot();
    Next.CarpenterApprenticeshipStage = uint8(WorkpieceStage(Next.WoodworkingJob));
    if (!ApprenticeMaterials::Grant(*Model, MoveTemp(Next), HostSlot, SuppliesReceipt, Inputs, Message)) return false;
    Message += TEXT("请锯出一把学徒长杖，达到图样要求后领取成品。");
    return true;
}
}

void AColdSteelPlayerState::ClientCarpenterLesson_Implementation(FGuid ProfileId, uint8 StageValue)
{
    const auto* PC = Cast<APlayerController>(GetOwner());
    if (GetNetMode() != NM_Client || !PC || !PC->IsLocalController() || PC->PlayerState != this) return;
    auto* Model = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Model || Model->GetWorld() != GetWorld() || !ProfileId.IsValid() || Model->Current.NetworkProfileId != ProfileId
        || StageValue > uint8(CarpenterApprenticeship::EStage::Complete) || Model->Current.CarpenterApprenticeshipStage == StageValue) return;
    Model->Current.CarpenterApprenticeshipStage = StageValue;
    Model->bTrainingDirty = true;
    Model->NotifyChanged();
}
