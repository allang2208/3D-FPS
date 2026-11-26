#include "SkillNetworkAuditCommandlet.h"
#include "ChainSlashMotion.h"
#include "PlayerSkillPreparation.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../Production/ProductionToolComponent.h"
#include "ChainSlashAssets.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodyWarhammerMotion.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

namespace
{
// Evaluate the two halves separately so a frozen windup or recovery cannot
// pass on the strength of a jump at the transition to the next cut.
struct FHalfCut
{
    int32 Frames=0;
    FVector First[3]{};
    double Travel[3]{};
    void Observe(const FVector (&Points)[3])
    {
        for(int32 I=0; I<3; ++I)
        {
            if(!Frames)First[I]=Points[I];
            Travel[I]=FMath::Max(Travel[I],FVector::Distance(Points[I],First[I]));
        }
        ++Frames;
    }
    bool Moved() const {return Frames>2 && Travel[0]>1. && Travel[1]>1. && Travel[2]>1.;}
};
}

int32 USkillNetworkAuditCommandlet::RunPojunChainPoseAudit()
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("PojunChainPoseAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Slot));
    ON_SCOPE_EXIT { FCommandLine::Set(*Original); };
    auto* GI=NewObject<UGameInstance>(GEngine);
    GI->AddToRoot();
    GI->InitializeStandalone(TEXT("PojunChainPoseAudit"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {
        GI->Shutdown();
        if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}
        GI->RemoveFromRoot();
    };
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 OldDelay=Delay?Delay->GetInt():0;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    ON_SCOPE_EXIT { if(Delay)Delay->Set(OldDelay,ECVF_SetByCode); };

    auto Seed=Model->Snapshot();
    Seed.ActiveWeaponSlot=6;
    Seed.ActiveProductionTool.Reset();
    Seed.Stamina=150;
    Seed.bSprintExhausted=false;
    Seed.ChainSlashCooldown=Seed.ChainSlashCooldownDuration=0.f;
    Seed.Skills.FindOrAdd(TEXT("chainSlash")).Level=1;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
    auto* PC=World->SpawnActor<APlayerController>();
    if(!Pawn||!PC)return 2;
    auto* Local=NewObject<ULocalPlayer>(GEngine);
    GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));
    PC->SetAsLocalPlayerController();PC->SetPlayer(Local);PC->Possess(Pawn);PC->bShowMouseCursor=false;
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    Body->Character=Pawn;
    Sword->Character=Pawn;
    Sword->InitializePresentation();
    Model->AttachPawn(Pawn);

    constexpr float Step=1.f/60.f;
    const auto Advance=[&]()
    {
        Tool->AdvanceActionBeforeCamera(Step);
        Sword->TickComponent(Step,LEVELTICK_All,&Sword->PrimaryComponentTick);
        Tool->TickComponent(Step,LEVELTICK_All,&Tool->PrimaryComponentTick);
    };
    int32 Failures=0;
    for(const TCHAR* Blade:{TEXT("yanling_edge"),TEXT("tengyun_dragon")})
    for(const TCHAR* Rune:{ColdSteelFrostRunes::Chixiao,ColdSteelFrostRunes::Zhufeng})
    {
        auto Item=Model->CreateItem(PojunGrip::Weapon);
        Item.Place=1;Item.Cell=6;
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return 2;
        auto Parts=MakeShared<FJsonObject>();
        Parts->SetStringField(TEXT("grip"),PojunGrip::Part);
        Parts->SetStringField(TEXT("blade_1"),Blade);
        Parts->SetStringField(TEXT("blade_2"),Rune);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Item.Data.Reset();
        FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        Seed.Items={Item};
        if(!Model->CommitState(Seed))return 2;
        TArray<FSoftObjectPath> SkillAssets;
        PlayerSkillAssets::Gather(TEXT("chainSlash"),Seed,SkillAssets);
        for(const auto& Path:SkillAssets)if(!Path.TryLoad())return 2;
        Sword->RefreshEquipment(Model);
        Tool->InitializeLocalTool();
        Tool->RefreshHeldTool();
        if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
        for(int32 Frame=0;Frame<150;++Frame)Advance();
        auto* Arms=Tool->ArmsMesh();
        if(!Arms||!Arms->DoesSocketExist(TEXT("hand_l"))||!Arms->DoesSocketExist(TEXT("hand_r"))||
            !Arms->DoesSocketExist(TEXT("WPN_root"))||Tool->PojunBladeTip.Equals(Tool->PojunBladeBase))
        {
            UE_LOG(LogTemp,Error,TEXT("POJUN_POSE missing rig or blade landmarks on %s %s"),Blade,Rune);
            return 2;
        }
        const FString Status=Sword->ChainSlashStatusText();
        const float Stamina=Model->Stamina(),Cost=Model->ChainSlashStats().StaminaCost;
        const bool Started=Model->UseQuickSkill(TEXT("chainSlash"));
        bool OK=Started&&Sword->IsPojunChainOccupied()&&Sword->ChainSlashContacts.Num()==4&&
            FMath::IsNearlyEqual(Stamina-Model->Stamina(),Cost)&&Model->ChainSlashCooldown()>0.f;
        FHalfCut Cuts[4][2];
        int32 LastCut=-1;
        for(int32 Frame=0;Started&&Sword->IsChainSlashActive()&&Frame<600;++Frame)
        {
            Advance();
            if(!Sword->IsChainSlashActive())break;
            const auto Phase=ChainSlashMotion::Phase(Sword->Elapsed,Sword->CurrentAnimation->GetPlayLength(),Sword->ChainSlashContacts);
            auto* Single=Arms->GetSingleNodeInstance();
            const auto BodyState=Body->SampleLocalState();
            const FName BodyClip=FPSBodyWarhammerMotion::Clip(BodyState);
            OK&=Single&&Single->GetCurrentAsset()==Sword->CurrentAnimation&&Arms->IsVisible()&&
                Sword->CurrentAnimation->GetPathName()==ChainSlash::Pojun&&BodyState.Weapon==TEXT("warhammer")&&
                BodyState.ActionVariant==ChainSlashMotion::Variant(Phase.Cut)&&BodyClip.IsNone();
            if(LastCut!=Phase.Cut)
            {
                UE_LOG(LogTemp,Display,TEXT("POJUN_POSE %s %s cut=%d arms=%s body=%s visible=%d"),
                    Blade,Rune,Phase.Cut+1,*GetNameSafe(Single?Single->GetCurrentAsset():nullptr),*BodyClip.ToString(),Arms->IsVisible());
                LastCut=Phase.Cut;
            }
            const FVector Points[]={
                Arms->GetSocketTransform(TEXT("hand_l"),RTS_Component).GetLocation(),
                Arms->GetSocketTransform(TEXT("hand_r"),RTS_Component).GetLocation(),
                Arms->GetSocketTransform(TEXT("WPN_root"),RTS_Component).TransformPosition(Tool->PojunBladeTip)};
            Cuts[Phase.Cut][Sword->Elapsed>=Phase.Contact].Observe(Points);
        }
        for(int32 Cut=0;Cut<4;++Cut)
        {
            const auto& In=Cuts[Cut][0];
            const auto& Out=Cuts[Cut][1];
            OK&=In.Moved()&&Out.Moved();
            UE_LOG(LogTemp,Display,TEXT("POJUN_POSE %s %s cut=%d samples=%d/%d windup_cm=%.2f,%.2f,%.2f follow_cm=%.2f,%.2f,%.2f"),
                Blade,Rune,Cut+1,In.Frames,Out.Frames,In.Travel[0],In.Travel[1],In.Travel[2],Out.Travel[0],Out.Travel[1],Out.Travel[2]);
        }
        Advance();
        OK&=!Sword->IsPojunChainOccupied()&&Tool->CurrentMotion==Tool->Motions.FindRef(TEXT("Idle"));
        UE_LOG(LogTemp,Display,TEXT("POJUN_POSE %s %s %s start=%d gate=%s cost=%.2f expected=%.2f cooldown=%.2f end=%s"),
            OK?TEXT("PASS"):TEXT("FAIL"),Blade,Rune,Started,*Status,Stamina-Model->Stamina(),Cost,Model->ChainSlashCooldown(),*GetNameSafe(Tool->CurrentMotion));
        Failures+=!OK;
        if(Sword->IsChainSlashActive())Sword->CancelAction();
    }
    return Failures?1:0;
}
