#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/M4GunsmithWidget.h"
#include "../UI/ColdSteelWeaponIcons.h"
#include "../UI/ColdSteelPickup.h"
#include "GunsmithSystem.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

void AFPSGAMECharacter::RunStockAudit()
{
    auto* PC=Cast<AFPSGAMEPlayerController>(GetController());if(!PC)return;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!P||!G||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("StockAudit")))return;
    const bool AKM=FParse::Param(FCommandLine::Get(),TEXT("StockAKM")),Load=FParse::Param(FCommandLine::Get(),TEXT("StockLoad"));
    const FString Def=AKM?TEXT("ue_akm"):TEXT("ue_m4a1"),Ammo=AKM?TEXT("ammo_762"):TEXT("ammo_556");
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("StockRun="),Run);
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("SkeletonStockAudit")/Run;IFileManager::Get().MakeDirectory(*Dir,true);
    auto Check=[this](bool Pass,const TCHAR* Name){++StockAuditChecks;if(!Pass)++StockAuditFailures;UE_LOG(LogTemp,Display,TEXT("STOCK_AUDIT: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    // Continuous moving-pose sampling, including all four reload paths.
    if(StockAuditStage>=8&&StockAuditStage<=16&&HasSkeletonStock())Check(ValidateStockAttachment(),TEXT("root following during gameplay"));
    static float LastCapture=0.f;
    static int32 CaptureFrame=0;
    if((StockAuditStage==10||StockAuditStage==11||StockAuditStage==13||StockAuditStage==14)&&IsReloading()&&GetWorld()->GetTimeSeconds()>LastCapture+.2f)
    {
        LastCapture=GetWorld()->GetTimeSeconds();
        FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("reload-%02d-%04d.png"),StockAuditStage,++CaptureFrame),false,false);
    }
    if(GetWorld()->GetTimeSeconds()<StockAuditNextTime)return;
    auto Shot=[&](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(Dir/(FString(Name)+TEXT(".png")),true,false);};
    auto Panel=[&](){TArray<UUserWidget*> Widgets;UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this,Widgets,UM4GunsmithWidget::StaticClass(),true);return Widgets.IsEmpty()?nullptr:Cast<UM4GunsmithWidget>(Widgets[0]);};
    float Delay=.8f;
    switch(StockAuditStage)
    {
    case 0:{
        if(!Load){auto S=P->Snapshot();S.Items.Empty();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);auto Gun=P->CreateItem(Def);Gun.Place=1;Gun.Cell=9;Gun.Magazine=17;S.Items.Add(Gun);S.ActiveWeaponSlot=9;auto A=P->CreateItem(Ammo,999);A.Cell=0;S.Items.Add(A);Check(P->CommitState(S),TEXT("seed isolated profile"));}
        else Check(P->Equipped()&&G->Installed(*P->Equipped()).FindRef(TEXT("stock"))==TEXT("skeleton")&&HasSkeletonStock(),TEXT("new process restores skeleton stock"));
        AuditSavedAmmo=P->Equipped()?P->Equipped()->Magazine:0;Delay=3.f;break;}
    case 1:Check(ValidateStockAttachment(),TEXT("initial factory or saved section state"));Check(PC->OpenGunsmith(),TEXT("open live workbench"));if(auto* W=Panel()){W->SelectCategory(TEXT("stock"));W->SetSidePreview(true);}break;
    case 2:Shot(TEXT("baseline"));break;
    case 3:if(auto* W=Panel()){
        Check(!G->Select(TEXT("stock"),TEXT("invalid")),TEXT("reject unknown stock"));
        W->ChooseOption(TEXT("stock"),TEXT("false"));Check(!HasSkeletonStock()&&ValidateStockAttachment(),TEXT("factory restore preview"));
        W->ChooseOption(TEXT("stock"),TEXT("skeleton"));Check(HasSkeletonStock()&&ValidateStockAttachment(),TEXT("skeleton draft replaces factory"));
        W->UndoDraft();Check(HasSkeletonStock()==Load,TEXT("undo returns installed stock"));
        W->ChooseOption(TEXT("stock"),Load?TEXT("false"):TEXT("skeleton"));P->AuditFailNextSave=true;Check(!W->ApplyDraft(),TEXT("save failure rejects stock transaction"));
        Check(G->Installed(*P->Equipped()).Contains(TEXT("stock"))==Load,TEXT("failed save preserves inventory"));
        W->ChooseOption(TEXT("stock"),TEXT("skeleton"));if(G->Pending())Check(W->ApplyDraft(),TEXT("apply stock and save"));
        const auto S=G->Calculate(Def,G->Installed(*P->Equipped()));const auto Base=G->Calculate(Def,{});
        Check(FMath::IsNearlyEqual(S.ADS,Base.ADS*.8,.00001)&&FMath::IsNearlyEqual(ADSInDuration,float(S.ADS),.00001f),TEXT("catalog and pawn agree on twenty percent ADS"));
        Check(FMath::IsNearlyEqual(S.RecoilMultiplier,1.1,.00001)&&FMath::IsNearlyEqual(S.ShakeMultiplier,1.1,.00001)&&S.Spread==1,TEXT("legacy recoil shake and spread preserved"));
        Check(P->Equipped()->Magazine==AuditSavedAmmo,TEXT("install preserves ammo"));W->SetSidePreview(true);
        }else Check(false,TEXT("workbench widget exists"));break;
    case 4:Shot(TEXT("installed-side"));break;
    case 5:if(auto* W=Panel())W->RotatePreview(FVector2D(120,20));break;
    case 6:Shot(TEXT("installed-oblique"));break;
    case 7:PC->CloseGunsmith();AimPressed();break;
    case 8:Check(HasSkeletonStock()&&ValidateStockAttachment(),TEXT("ADS stock and mount"));Shot(TEXT("ads"));FirePressed();Delay=.16f;break;
    case 9:FireReleased();AimReleased();Shot(TEXT("fire"));ReloadPressed();Check(IsReloading(),TEXT("normal reload starts"));Delay=ReloadDuration+.3f;break;
    case 10:Check(!IsReloading()&&MagazineAmmo==MagazineCapacity,TEXT("normal reload completes"));MagazineAmmo=0;P->SyncRuntime();ReloadPressed();Check(IsReloading(),TEXT("empty reload starts"));Delay=EmptyReloadDuration+.3f;break;
    case 11:Check(!IsReloading()&&MagazineAmmo==MagazineCapacity,TEXT("empty reload completes"));Check(PC->OpenGunsmith(),TEXT("open drum combination"));if(auto* W=Panel()){W->ChooseDrum(true);Check(W->ApplyDraft(),TEXT("apply drum with stock"));}PC->CloseGunsmith();Delay=.5f;break;
    case 12:MagazineAmmo=12;P->SyncRuntime();ReloadPressed();Check(IsReloading()&&HasGunsmithDrum(),TEXT("drum normal reload starts"));Delay=ReloadDuration+.3f;break;
    case 13:Check(!IsReloading()&&MagazineAmmo==MagazineCapacity,TEXT("drum normal reload completes"));MagazineAmmo=0;P->SyncRuntime();ReloadPressed();Check(IsReloading(),TEXT("drum empty reload starts"));Delay=EmptyReloadDuration+.3f;break;
    case 14:Check(!IsReloading()&&MagazineAmmo==MagazineCapacity&&ValidateStockAttachment(),TEXT("drum empty reload completes and stock follows"));Shot(TEXT("hip-drum"));break;
    case 15:Check(PC->OpenGunsmith(),TEXT("open removal"));if(auto* W=Panel()){W->ChooseDrum(false);W->ChooseOption(TEXT("stock"),TEXT("false"));Check(W->ApplyDraft(),TEXT("save factory restoration"));Check(!HasSkeletonStock()&&ValidateStockAttachment(),TEXT("no residual replacement"));W->ChooseOption(TEXT("stock"),TEXT("skeleton"));Check(W->ApplyDraft(),TEXT("save skeleton for reload"));}PC->CloseGunsmith();break;
    case 16:{
        auto S=P->Snapshot();auto Other=P->CreateItem(Def);bool Existing=false;for(const auto& I:S.Items)if(I.Definition==Def&&I.Place==0){Other=I;Existing=true;break;}if(!Existing){Other.Place=0;Other.Cell=4;Other.Magazine=11;S.Items.Add(Other);Check(P->CommitState(S),TEXT("seed unequipped instance"));}
        Check(PC->OpenGunsmith(Other.InstanceId),TEXT("open unequipped workbench"));if(auto* W=Panel()){W->ChooseOption(TEXT("stock"),TEXT("skeleton"));Check(!G->Pending()||W->ApplyDraft(),TEXT("save stock on unequipped instance"));}PC->CloseGunsmith();
        Check(P->ReloadProfile()&&G->Installed(*P->FindItem(Other.InstanceId)).FindRef(TEXT("stock"))==TEXT("skeleton"),TEXT("unequipped stock survives reload"));
        auto* Drop=GetWorld()->SpawnActor<AColdSteelPickup>(GetActorLocation()+FVector(300,0,100),FRotator::ZeroRotator);Drop->InitializeItem(*P->FindItem(Other.InstanceId));TArray<UStaticMeshComponent*> Parts;Drop->GetComponents(Parts);int32 Count=0;for(auto* Part:Parts)if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==TEXT("SM_SkeletonStock"))++Count;Check(Count==1,TEXT("ground weapon has exactly one skeleton stock"));Drop->Destroy();
        GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Request(*P->Equipped());Delay=3;break;}
    case 17:{
        const auto* Brush=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>()->Find(*P->Equipped());auto* Tex=Brush?Cast<UTexture2D>(Brush->GetResourceObject()):nullptr;Check(Tex!=nullptr,TEXT("stock recipe inventory icon generated"));
        if(Tex){const auto& Mip=Tex->GetPlatformData()->Mips[0];const auto* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());TArray<FColor> Copy;Copy.Append(Pixels,Tex->GetSizeX()*Tex->GetSizeY());Mip.BulkData.Unlock();TArray<uint8> PNG;FImageUtils::CompressImageArray(Tex->GetSizeX(),Tex->GetSizeY(),Copy,PNG);FFileHelper::SaveArrayToFile(PNG,*(Dir/TEXT("inventory-icon.png")));}
        Check(ValidateStockAttachment()&&P->SaveNow(),TEXT("final saved mount valid"));Shot(TEXT("final-hip"));break;}
    case 18:{auto S=P->Snapshot();const FString OtherDef=AKM?TEXT("ue_m4a1"):TEXT("ue_akm");bool Found=false;for(const auto& I:S.Items)if(I.Place==1&&I.Cell==6)Found=true;if(!Found){auto I=P->CreateItem(OtherDef);I.Place=1;I.Cell=6;I.Magazine=10;S.Items.Add(I);}S.ActiveWeaponSlot=6;Check(P->CommitState(S),TEXT("switch to other rifle"));Delay=2.f;break;}
    case 19:Check(!HasSkeletonStock()&&ValidateStockAttachment(),TEXT("other rifle factory restored without stale stock"));{auto S=P->Snapshot();S.ActiveWeaponSlot=9;Check(P->CommitState(S),TEXT("switch back to stock rifle"));}Delay=2.f;break;
    case 20:Check(HasSkeletonStock()&&ValidateStockAttachment(),TEXT("equipment action restores stock recipe"));{TArray<UStaticMeshComponent*> Parts;GetComponents(Parts);int32 Count=0;for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetName()==TEXT("SM_SkeletonStock"))++Count;Check(Count==1,TEXT("no duplicate after weapon switch"));}Check(P->SaveNow(),TEXT("save final stock state"));break;
    case 21:
        UE_LOG(LogTemp,Display,TEXT("STOCK_AUDIT: COMPLETE checks=%d failures=%d"),StockAuditChecks,StockAuditFailures);
        FFileHelper::SaveStringToFile(FString::Printf(TEXT("checks=%d failures=%d"),StockAuditChecks,StockAuditFailures),*(Dir/TEXT("result.txt")));PC->ConsoleCommand(TEXT("quit"));return;
    }
    ++StockAuditStage;StockAuditNextTime=GetWorld()->GetTimeSeconds()+Delay;
}
