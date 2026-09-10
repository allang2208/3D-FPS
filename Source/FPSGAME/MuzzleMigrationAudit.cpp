#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSBallisticsComponent.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/M4GunsmithWidget.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Camera/CameraComponent.h"
#include "AudioMixerBlueprintLibrary.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void AFPSGAMECharacter::RunMuzzleMigrationAudit()
{
    static bool Started=false;if(Started||GetWorld()->GetTimeSeconds()<6.f)return;Started=true;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* PC=Cast<AFPSGAMEPlayerController>(Controller);
    if(!P||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("MuzzleMigrationAudit"))||!PC||!P->Equipped()){FPlatformMisc::RequestExitWithStatus(false,2);return;}
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("MuzzleMigrationAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    auto Counts=MakeShared<FIntPoint>(0,0);auto Lines=MakeShared<FString>();
    auto Check=[Counts,Lines](bool Pass,const FString& Label){++Counts->X;if(!Pass)++Counts->Y;*Lines+=FString::Printf(TEXT("%s %s\n"),Pass?TEXT("PASS"):TEXT("FAIL"),*Label);UE_LOG(LogTemp,Display,TEXT("MUZZLE_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Label);};
    auto Later=[this](float Delay,TFunction<void()> Fn){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[Fn](){Fn();},Delay,false);};
    auto Input=[PC](FKey Key,EInputEvent Event){static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(Key,Event,Event==IE_Released?0.f:1.f));};
    UAudioMixerBlueprintLibrary::StartRecordingOutput(this,26.f);
    const TArray<FString> Variants={TEXT("true"),TEXT("brake"),TEXT("titanium_brake")};
    const float Recoils[]={75,85,70},Shakes[]={75,85,80},ADS[]={.24f,.264f,.24f/.85f};
    for(int32 Index=0;Index<3;++Index)
    {
        const FString V=Variants[Index];const float T=Index*6.f;const float Recoil=Recoils[Index],Shake=Shakes[Index],AimTime=ADS[Index];
        Later(T+.1f,[this,P,G,PC,Check,V,Recoil,Shake,AimTime](){
            Check(PC->OpenGunsmith(),V+TEXT(" opens real workbench"));
            TArray<UUserWidget*> Widgets;UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this,Widgets,UM4GunsmithWidget::StaticClass(),false);
            if(Widgets.IsEmpty()){Check(false,TEXT("workbench widget exists"));return;}
            auto* Panel=Cast<UM4GunsmithWidget>(Widgets[0]);Panel->SelectCategory(TEXT("muzzle"));
            const float Previous=WeaponHandling.RecoilIndex;Panel->ChooseOption(TEXT("muzzle"),V);
            Check(FMath::IsNearlyEqual(WeaponHandling.RecoilIndex,Previous),V+TEXT(" draft does not change live recoil"));
            const auto S=G->Calculate(TEXT("ue_m4a1"),G->Draft());
            Check(FMath::IsNearlyEqual(S.Recoil,double(Recoil),.001)&&FMath::IsNearlyEqual(S.Shake,double(Shake),.001)&&FMath::IsNearlyEqual(S.ADS,double(AimTime),.001),V+TEXT(" source recoil shake ADS migrated"));
            Check(Panel->ApplyDraft(),V+TEXT(" apply and save"));
            Check(MuzzleVariant==V&&MuzzleAttachment&&MuzzleAttachment->IsVisible(),V+TEXT(" upgraded mesh visible"));
            Check(FMath::IsNearlyEqual(WeaponHandling.RecoilIndex,Recoil)&&FMath::IsNearlyEqual(WeaponHandling.ShakeIndex,Shake)&&FMath::IsNearlyEqual(ProjectileSpeedCM,V==TEXT("true")?7200.f:9000.f),V+TEXT(" actual pawn uses final attributes"));
            Check(IsMuzzleSuppressed()==(V==TEXT("true")),V+TEXT(" suppressor mode exclusive"));
            bool Hidden=false;auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();
            for(int32 M=0;M<Rifle->GetMaterials().Num();++M)if(Rifle->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Flash_Hider"))){Hidden=!AKMViewmodel->IsMaterialSectionShown(M,0);Check(MuzzleAttachment->GetMaterial(0)==AKMViewmodel->GetMaterial(M),V+TEXT(" exact rifle muzzle material reused"));}
            Check(Hidden,V+TEXT(" factory muzzle hidden without hiding barrel"));
            Panel->SetCompareFactory(true);Panel->RotatePreview(FVector2D(-22,-14));
        });
        Later(T+.8f,[Dir,V](){FScreenshotRequest::RequestScreenshot(Dir/(V+TEXT("-workbench.png")),true,false);});
        Later(T+1.1f,[PC,Input](){PC->CloseGunsmith();Input(EKeys::RightMouseButton,IE_Pressed);});
        Later(T+1.6f,[this,Check,Dir,V](){
            const FVector Forward=GetEffectiveMuzzleForward();const FVector Original=AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
            const FVector Offset=GetEffectiveMuzzleLocation()-Original;
            const float Extension=FVector::DotProduct(Offset,Forward);const float Error=(Offset-Forward*Extension).Length();
            Check(Error<.15f&&Extension>1.f&&Extension<15.f,V+TEXT(" bore axis and measured tip extension"));
            Check(FVector::DotProduct(Forward,FirstPersonCamera->GetForwardVector())>.98f,V+TEXT(" muzzle points forward in ADS"));
            UE_LOG(LogTemp,Display,TEXT("MUZZLE_FIT %s extension_cm=%.5f axis_error_cm=%.5f tip=%s"),*V,Extension,Error,*GetEffectiveMuzzleLocation().ToString());
            FScreenshotRequest::RequestScreenshot(Dir/(V+TEXT("-ads.png")),true,false);
        });
        Later(T+1.9f,[Input](){Input(EKeys::LeftMouseButton,IE_Pressed);});
        Later(T+2.12f,[this,Check,Input,V](){Input(EKeys::LeftMouseButton,IE_Released);Input(EKeys::RightMouseButton,IE_Released);
            Check(M4FireVoice&&M4FireVoice->Sound==(V==TEXT("true")?SuppressedFireSound:FireSound),V+TEXT(" real fire selects correct sound"));
            Check(Ballistics->ActiveCount()>0||Ballistics->ImpactCount>0,V+TEXT(" real trigger launches swept projectiles"));});
        Later(T+2.7f,[Dir,V](){FScreenshotRequest::RequestScreenshot(Dir/(V+TEXT("-hip.png")),true,false);});
        Later(T+3.f,[Input](){Input(EKeys::R,IE_Pressed);Input(EKeys::R,IE_Released);});
        Later(T+5.6f,[this,P,G,Check,V](){Check(P->ReloadProfile()&&G->Installed(*P->Equipped()).FindRef(TEXT("muzzle"))==V&&MuzzleVariant==V,V+TEXT(" reload and saved instance preserve attachment"));});
    }
    Later(18.2f,[this,P,G,PC,Check](){
        const float Ammo=MagazineAmmo;Check(G->Begin(P->Equipped()->InstanceId)&&G->Select(TEXT("muzzle"),TEXT("false"))&&G->Apply(),TEXT("remove muzzle and save"));G->Close();ApplyColdSteelProfile(P);
        Check(MuzzleVariant.IsEmpty()&&(!MuzzleAttachment||!MuzzleAttachment->IsVisible())&&!IsMuzzleSuppressed(),TEXT("factory model sound and muzzle origin restored"));
        Check(WeaponHandling.RecoilIndex==100&&WeaponHandling.ShakeIndex==100&&ProjectileSpeedCM==9000&&MagazineAmmo==Ammo,TEXT("factory stats and ammo preserved after removal"));
        // Coexistence with optic and drum; additive ADS penalties match source.
        const auto Combo=G->Calculate(TEXT("ue_m4a1"),{{TEXT("muzzle"),TEXT("titanium_brake")},{TEXT("magazine"),TEXT("large_drum")},{TEXT("optic"),TEXT("holographic")}});
        Check(Combo.Capacity==50&&FMath::IsNearlyEqual(Combo.Recoil,70.)&&Combo.ADS>.24, TEXT("muzzle stacks with drum and holographic without replacing their slots"));
    });
    Later(19.f,[this,Check,Later](){
        auto Target=[this](FVector Where){FActorSpawnParameters Params;Params.ObjectFlags=RF_Transient;auto* A=GetWorld()->SpawnActor<AStaticMeshActor>(Where,FRotator::ZeroRotator,Params);auto* M=A->GetStaticMeshComponent();M->SetMobility(EComponentMobility::Movable);M->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));M->SetCollisionEnabled(ECollisionEnabled::QueryOnly);M->SetCollisionResponseToAllChannels(ECR_Ignore);M->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);A->SetActorScale3D(FVector(.02,2,2));auto* H=NewObject<UFPSCombatHealthComponent>(A);H->RegisterComponent();return TPair<AStaticMeshActor*,UFPSCombatHealthComponent*>(A,H);};
        const FVector Start(0,0,50000);auto Fast=Target(Start+FVector(9000,0,0)),Slow=Target(Start+FVector(9000,1000,0)),Moving=Target(Start+FVector(9000,2000,0));
        Ballistics->Launch(Start,FVector::ForwardVector,9000,10000,30,WeaponFX,CriticalHitSound);Ballistics->Launch(Start+FVector(0,1000,0),FVector::ForwardVector,7200,10000,30,WeaponFX,CriticalHitSound);Ballistics->Launch(Start+FVector(0,2000,0),FVector::ForwardVector,7200,10000,30,WeaponFX,CriticalHitSound);
        Check(Fast.Value->Health==100&&Slow.Value->Health==100,TEXT("projectiles do not apply instant damage"));
        Later(.4f,[Moving](){Moving.Key->AddActorWorldOffset(FVector(0,600,0));});
        Later(.9f,[Fast,Slow,Check](){Check(Fast.Value->Health==100&&Slow.Value->Health==100,TEXT("no hit before 90m flight completes"));});
        Later(1.1f,[Fast,Slow,Check](){Check(Fast.Value->Health<100&&Slow.Value->Health==100,TEXT("90m target hit at 90m/s but not yet at 72m/s"));});
        Later(1.45f,[Fast,Slow,Moving,Check](){Check(Slow.Value->Health<100,TEXT("suppressed round reaches target after longer flight"));Check(Moving.Value->Health==100,TEXT("flight checks current target position instead of delaying a precomputed hit"));Fast.Key->Destroy();Slow.Key->Destroy();Moving.Key->Destroy();});
    });
    Later(22.f,[this,Counts,Lines,Dir](){UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("MuzzleAudio"),Dir+TEXT("/"));FFileHelper::SaveStringToFile(*Lines,*(Dir/TEXT("assertions.log")));UE_LOG(LogTemp,Display,TEXT("MUZZLE_MIGRATION_COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);});
    Later(24.f,[Counts](){FPlatformMisc::RequestExitWithStatus(false,Counts->Y?1:0);});
}
