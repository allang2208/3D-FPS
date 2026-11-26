#include "BlacksmithApprenticeship.h"
#include "../WorldGeneration/ForestVillageMap.h"
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
static const FString LegacyReceipt = TEXT("village.blacksmith.lesson.materials.v1");
static const FString ForgeSuppliesReceipt = TEXT("village.blacksmith.lesson.materials.v2");
static const FString SuppliesReceipt = TEXT("village.blacksmith.lesson.smelting.v3");

static const FString PickReceipt = TEXT("village.blacksmith.lesson.pickaxe.v4");

bool IsMining(EStage Value)
{
    return Value >= EStage::Mining && Value < EStage::ReturnOre;
}

int32 OreCollected(EStage Value)
{
    if (Value == EStage::NotStarted) return 0;
    return IsMining(Value) ? int32(Value)-int32(EStage::Mining) : RequiredOre;
}

bool InsertPickup(FColdSteelProfile& Profile,FColdSteelItem Item)
{
    const bool Fresh = Item.bFreshMinedIron && Item.Definition == TEXT("iron_ore");
    const int64 Quantity = Item.Count;
    Item.bFreshMinedIron = false;
    if (!ColdSteelInventory::Insert(Profile.Items, Item)) return false;
    const auto Current = EStage(Profile.BlacksmithApprenticeshipStage);
    if (Fresh && IsMining(Current))
    {
        const int32 Added = int32(FMath::Clamp<int64>(Quantity, 0, RequiredOre-OreCollected(Current)));
        Profile.BlacksmithApprenticeshipStage += uint8(Added);
    }
    return true;
}

int32 LessonStep(EStage Value)
{
    if (IsMining(Value)) return 1;
    if (Value == EStage::ReturnOre) return 2;
    if (Value >= EStage::Smelting) return 3;
    return Value == EStage::NotStarted ? 0 : int32(Value) + 3;
}

int32 IngotsCollected(EStage Value)
{
    if (Value == EStage::NotStarted || Value >= EStage::Mining) return 0;
    return Value >= EStage::Smelting ? int32(Value) - int32(EStage::Smelting) : RequiredIngots;
}


static bool IsLessonWeapon(const FColdSteelForgeJob& Job)
{
    return !Job.Id.IsEmpty() && Job.Recipe == TargetRecipe && Job.Item.Definition == TEXT("ue_forged_steel_greatsword");
}

static EStage WorkpieceStage(const FColdSteelProfile& Profile)
{
    const auto& Job = Profile.ForgeJob;
    if (!IsLessonWeapon(Job) || Profile.CampfireWorldReceipts.Contains(ApprenticeMaterials::PriorWorkpieceKey(Job.Id))) return EStage::Materials;
    if (!Job.bFinished) return EStage::Hammering;
    return (Job.bHammeredBlank || Job.Hits > 0) ? EStage::Finish : EStage::Materials;
}

EStage Stage(const FColdSteelProfile& Profile)
{
    const uint8 Value = Profile.BlacksmithApprenticeshipStage;
    const EStage Saved = Value <= uint8(EStage::ReturnOre) ? EStage(Value) : EStage::NotStarted;
    if (Saved == EStage::NotStarted && Profile.CampfireWorldReceipts.Contains(SuppliesReceipt))
    {
        const auto Workpiece = WorkpieceStage(Profile);
        return Workpiece == EStage::Materials ? EStage::Smelting : Workpiece;
    }
    if (Saved == EStage::NotStarted && Profile.CampfireWorldReceipts.Contains(PickReceipt)) return EStage::Mining;
    if (Saved == EStage::Complete || Saved >= EStage::Smelting || Profile.CampfireWorldReceipts.Contains(SuppliesReceipt))
        return Saved;
    if (Saved == EStage::NotStarted && !Profile.CampfireWorldReceipts.Contains(ForgeSuppliesReceipt)
        && !Profile.CampfireWorldReceipts.Contains(LegacyReceipt)) return Saved;
    // Honour an existing paid lesson blade. Older apprentices who have not opened a forge learn smelting first.
    const auto Existing = WorkpieceStage(Profile);
    return Existing == EStage::Materials ? EStage::Smelting : Existing;
}

bool Reset(FColdSteelProfile& Profile)
{
    if (Stage(Profile) == EStage::NotStarted) return false;
    const auto& Job = Profile.ForgeJob;
    if (IsLessonWeapon(Job))
        Profile.CampfireWorldReceipts.Add(ApprenticeMaterials::PriorWorkpieceKey(Job.Id), Profile.CampfireInventoryRevision);
    Profile.BlacksmithApprenticeshipStage = uint8(EStage::NotStarted);
    Profile.CampfireWorldReceipts.Remove(PickReceipt);
    Profile.CampfireWorldReceipts.Remove(SuppliesReceipt);
    Profile.CampfireWorldReceipts.Remove(ForgeSuppliesReceipt);
    Profile.CampfireWorldReceipts.Remove(LegacyReceipt);
    return true;
}

bool NeedsSupplies(const FColdSteelProfile& Profile)
{
    const EStage Current = Stage(Profile);
    if (Current == EStage::NotStarted || Current == EStage::ReturnOre) return true;
    return Current >= EStage::Smelting && Current <= EStage::TwoIngots && !Profile.CampfireWorldReceipts.Contains(SuppliesReceipt);
}

void CollectIngots(FColdSteelProfile& Profile, int64 Count)
{
    const EStage Current = Stage(Profile);
    if (Current < EStage::Smelting || Current > EStage::TwoIngots || Count <= 0 || !Profile.CampfireWorldReceipts.Contains(SuppliesReceipt)) return;
    const int32 Total = IngotsCollected(Current) + int32(FMath::Min<int64>(Count, RequiredIngots));
    if (Total >= RequiredIngots && IsLessonWeapon(Profile.ForgeJob))
        Profile.CampfireWorldReceipts.Add(ApprenticeMaterials::PriorWorkpieceKey(Profile.ForgeJob.Id), Profile.CampfireInventoryRevision);
    Profile.BlacksmithApprenticeshipStage = uint8(Total >= RequiredIngots ? EStage::Materials : EStage(int32(EStage::Smelting) + Total));
}

void WorkpieceUpdated(FColdSteelProfile& Profile)
{
    const EStage Current = Stage(Profile);
    if (Current >= EStage::Materials && Current <= EStage::Finish)
        Profile.BlacksmithApprenticeshipStage = uint8(WorkpieceStage(Profile));
}

void WorkpieceRemoved(FColdSteelProfile& Profile, bool bClaimed)
{
    const EStage Current = Stage(Profile);
    const bool Earned = bClaimed && WorkpieceStage(Profile) == EStage::Finish;
    Profile.CampfireWorldReceipts.Remove(ApprenticeMaterials::PriorWorkpieceKey(Profile.ForgeJob.Id));
    if (Current < EStage::Materials || Current > EStage::Finish) return;
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
    if (ForestVillageMap::Is(Model->GetWorld()) && Stage(Current)==EStage::NotStarted)
    {
        Message=TEXT("这片林地的村外采矿教学暂缓开放。");
        return false;
    }
    if (!NeedsSupplies(Current))
    {
        Message = Stage(Current) == EStage::Complete ? TEXT("打铁修炼已完成。") : TEXT("教学材料已领取。打开任务栏可查看当前步骤。");
        return true;
    }
    Model->SyncRuntime();
    auto Next = Model->Snapshot();
    const EStage CurrentStage = Stage(Next);
    if (CurrentStage == EStage::NotStarted)
    {
        Next.BlacksmithApprenticeshipStage = uint8(EStage::Mining);
        if (!ApprenticeMaterials::Grant(*Model, MoveTemp(Next), HostSlot, PickReceipt, {{TEXT("tool_pickaxe"),1}}, Message)) return false;
        Message += TEXT("地图上标出了最近可采的露天铁矿脉。用十字镐采矿，拾取十块铁矿石后回来交给我。");
        return true;
    }
    if (CurrentStage == EStage::ReturnOre)
    {
        int64 Left = RequiredOre;
        for (int32 Index=Next.Items.Num()-1; Index>=0 && Left>0; --Index)
        {
            auto& Ore = Next.Items[Index];
            if (Ore.Definition!=TEXT("iron_ore") || (Ore.Place!=0 && Ore.Place!=ColdSteelInventory::ColdSteelCompartment::Place)) continue;
            const int64 Take = FMath::Min(Left,Ore.Count);
            Left-=Take;
            Ore.Count-=Take;
            if (!Ore.Count) Next.Items.RemoveAt(Index);
        }
        if (Left>0)
        {
            Message=FString::Printf(TEXT("交付需要随身携带十块铁矿石，还差 %lld 块。"),Left);
            return false;
        }
    }
    const auto* Workstation = Model->GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();
    TArray<FColdSteelCraftingInput> Inputs;
    if (!Workstation || !Workstation->InputsFor(TargetRecipe, TEXT("ironIngot"), Inputs))
    {
        Message = TEXT("锻钢双手剑的教学配方暂未就绪，请稍后再来。");
        return false;
    }
    // Replace the ready-made iron with ore and fuel. An old material grant already included the blank.
    const bool HadKit = Next.CampfireWorldReceipts.Contains(ForgeSuppliesReceipt) || Next.CampfireWorldReceipts.Contains(LegacyReceipt);
    Inputs.RemoveAll([HadKit](const FColdSteelCraftingInput& Input) {
        return Input.Item == TEXT("ironIngot") || (HadKit && Input.Item == TEXT("search_forging_alloy_blank"));
    });
    Inputs.Add({TEXT("iron_ore"), RequiredIngots});
    Inputs.Add({TEXT("wood"), 1});
    Next.BlacksmithApprenticeshipStage = uint8(EStage::Smelting);
    if (!ApprenticeMaterials::Grant(*Model, MoveTemp(Next), HostSlot, SuppliesReceipt, Inputs, Message)) return false;
    if (CurrentStage == EStage::ReturnOre) Message=TEXT("收到十块铁矿石。三块分给你练手，合金胚和木材也拿好。");
    Message += TEXT("先去铺外的高炉添木材，把三份铁矿炼成铁锭，取锭后再回来打铁。");
    return true;
}
}

void AColdSteelPlayerState::ClientBlacksmithLesson_Implementation(FGuid ProfileId,uint8 StageValue)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(GetNetMode()!=NM_Client||!PC||!PC->IsLocalController()||PC->PlayerState!=this)return;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Model->GetWorld()!=GetWorld()||!ProfileId.IsValid()||Model->Current.NetworkProfileId!=ProfileId
        ||StageValue>uint8(BlacksmithApprenticeship::EStage::ReturnOre)||Model->Current.BlacksmithApprenticeshipStage==StageValue)return;
    Model->Current.BlacksmithApprenticeshipStage=StageValue;
    Model->bTrainingDirty=true;
    Model->NotifyChanged();
}
