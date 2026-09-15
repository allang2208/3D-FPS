#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "TimerManager.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

void AFPSGAMEPlayerController::RunPrismHandstopAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
    if(!C||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("PrismHandstopAudit")))return;
    auto Counts=MakeShared<FIntPoint>(0,0);
    auto Check=[Counts](bool Pass,const TCHAR* Name){++Counts->X;if(!Pass)++Counts->Y;UE_LOG(LogTemp,Display,TEXT("PRISM_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto Later=[this](float T,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},T,false);};
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("PrismHandstopAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    auto Shot=[Dir](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(Dir/FString(Name),true,false);};
    auto State=P->Snapshot();State.Items.Reset();auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=1;I.Cell=9;I.Magazine=17;State.Items.Add(I);State.ActiveWeaponSlot=9;Check(P->CommitState(State),TEXT("seed isolated M4"));
    Later(3,[this,P,G,C,Check](){Check(OpenGunsmith(),TEXT("open workbench"));if(!GunsmithPanel)return;
        Check(G->Option(TEXT("ue_m4a1"),TEXT("underbarrel"),TEXT("prism_handstop"))!=nullptr,TEXT("catalog option exists"));
        GunsmithPanel->SelectCategory(TEXT("underbarrel"));GunsmithPanel->ChooseOption(TEXT("underbarrel"),TEXT("prism_handstop"));
        Check(C->HasPrismHandstop()&&G->Pending()==1,TEXT("select displays draft handstop"));
        Check(G->Installed(*P->Equipped()).FindRef(TEXT("underbarrel")).IsEmpty(),TEXT("preview does not save"));
        Check(C->GetMagazineAmmo()==17,TEXT("selection preserves ammo"));
        TArray<UStaticMeshComponent*> Parts;C->GetComponents(Parts);bool Mounted=false;
        for(auto* Part:Parts)if(Part->GetName()==TEXT("M4PrismHandstop"))Mounted=Part->GetAttachSocketName()==TEXT("WPN_root")&&Part->GetAttachParent()&&Part->GetCollisionEnabled()==ECollisionEnabled::NoCollision;
        Check(Mounted,TEXT("rigid weapon-root mount without collision"));
    });
    Later(5,[Shot](){Shot(TEXT("prism-side.png"));});
    Later(6,[this,Shot](){if(GunsmithPanel)GunsmithPanel->RotatePreview(FVector2D(-90,-35));});
    Later(7,[Shot](){Shot(TEXT("prism-rotated.png"));});
    Later(8,[this,C,P,G,Check](){CloseGunsmith();Check(!C->HasPrismHandstop(),TEXT("close cancels unsaved visual"));Check(OpenGunsmith(),TEXT("reopen"));if(!GunsmithPanel)return;
        GunsmithPanel->SelectCategory(TEXT("underbarrel"));GunsmithPanel->ChooseOption(TEXT("underbarrel"),TEXT("prism_handstop"));
        P->AuditFailNextSave=true;Check(!GunsmithPanel->ApplyDraft()&&G->Pending()==1&&C->HasPrismHandstop(),TEXT("failed save retains draft"));
        Check(GunsmithPanel->ApplyDraft(),TEXT("apply saves handstop"));CloseGunsmith();Check(P->ReloadProfile()&&C->HasPrismHandstop(),TEXT("reload restores installed handstop"));
        GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Request(*P->Equipped());
    });
    Later(10,[Shot](){Shot(TEXT("prism-first-person.png"));});
    Later(11,[this,P,C,Check](){Check(GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Find(*P->Equipped())!=nullptr,TEXT("equipped configuration icon renders"));
        Check(OpenGunsmith(),TEXT("open installed"));if(GunsmithPanel){GunsmithPanel->SelectCategory(TEXT("underbarrel"));GunsmithPanel->ChooseOption(TEXT("muzzle"),TEXT("true"));GunsmithPanel->ChooseDrum(true);GunsmithPanel->Choose(true);}
    });
    Later(13,[Shot](){Shot(TEXT("prism-all-parts.png"));});
    Later(14,[this,P,C,G,Check](){CloseGunsmith();Check(OpenGunsmith(),TEXT("open for removal"));if(!GunsmithPanel)return;
        GunsmithPanel->ChooseOption(TEXT("underbarrel"),TEXT("false"));Check(!C->HasPrismHandstop(),TEXT("remove preview hides attachment"));
        Check(GunsmithPanel->ApplyDraft(),TEXT("save removal"));CloseGunsmith();Check(P->ReloadProfile()&&!C->HasPrismHandstop(),TEXT("reload keeps removal"));
        Check(C->GetMagazineAmmo()==17,TEXT("all transactions preserve ammo"));
    });
    Later(16,[this,P,C,Check](){auto S=P->Snapshot();auto Other=P->CreateItem(TEXT("ue_m4a1"));Other.Place=0;Other.Cell=0;Other.Magazine=11;S.Items.Add(Other);Check(P->CommitState(S)&&OpenGunsmith(Other.InstanceId),TEXT("open unequipped instance"));if(!GunsmithPanel)return;
        GunsmithPanel->ChooseOption(TEXT("underbarrel"),TEXT("prism_handstop"));Check(!C->HasPrismHandstop(),TEXT("unequipped draft does not affect active gun"));Check(GunsmithPanel->ApplyDraft(),TEXT("save unequipped attachment"));CloseGunsmith();Check(P->ReloadProfile(),TEXT("reload unequipped data"));
    });
    Later(18,[this,P,G,Check,Counts](){const auto S=P->Snapshot();bool Found=false;for(const auto& Item:S.Items)if(Item.Place==0)Found|=G->Installed(Item).FindRef(TEXT("underbarrel"))==TEXT("prism_handstop");Check(Found,TEXT("unequipped instance retains attachment"));UE_LOG(LogTemp,Display,TEXT("PRISM_AUDIT COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);ConsoleCommand(TEXT("quit"));});
}
