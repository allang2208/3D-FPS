#include "../UI/ColdSteelStatusModel.h"
#include "../NPC/ChapelNun.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "ColdSteelSkillTree.h"
#include "../Monsters/FPSCombatHealthComponent.h"

bool UColdSteelStatusModel::LearnHolyLightFromTrainer(AActor* Trainer)
{
    auto* Pawn=RuntimePawn();
    if(!Pawn||!Pawn->HasAuthority()||!IsValid(Cast<AChapelNun>(Trainer))||Trainer->GetWorld()!=Pawn->GetWorld()
        ||FVector::DistSquared(Pawn->GetActorLocation(),Trainer->GetActorLocation())>FMath::Square(380.f))
    {Message=TEXT("请与教堂中的修女交谈学习。");return false;}
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Health||Health->IsDead()){Message=TEXT("死亡状态无法学习圣光。");return false;}
    if(IsSkillLearned(TEXT("holyLight")))return true;
    const auto* Node=ColdSteelSkillTree::Get().Find(TEXT("holyLight"));
    if(!Node){Message=TEXT("圣光资料尚未就绪。");return false;}
    SyncRuntime();auto Next=Snapshot();
    for(const auto& R:Node->Requires)if(!ColdSteelSkillTree::RequirementMet(Next,R))
    {Message=TEXT("需要角色达到 Lv15，才能学习圣光。");return false;}
    ColdSteelSkillTree::Migrate(Next);Next.LearnedSkills.AddUnique(TEXT("holyLight"));
    auto& Skill=Next.Skills.FindOrAdd(TEXT("holyLight"));Skill.Level=FMath::Max(1,Skill.Level);
    // The same durable guest-profile writer used by server transactions saves
    // before publishing; a failed write must not grant a temporary ability.
    FString GuestSlot;
    if(bNetShadowProfile)
    {
        const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        if(!PS||PS->CampfireGuestSlot().IsEmpty()){Message=TEXT("角色档案正在同步。");return false;}
        GuestSlot=PS->CampfireGuestSlot();
    }
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
    return CommitState(MoveTemp(Next));
}
