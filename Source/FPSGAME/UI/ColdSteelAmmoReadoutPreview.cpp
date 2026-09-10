#include "ColdSteelAmmoReadout.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Components/TextBlock.h"
#include "Components/CanvasPanelSlot.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

// Opt-in rendering fixtures only. Never writes weapon state or the player's inventory.
void UColdSteelAmmoReadout::Preview(const AFPSGAMECharacter* Character,const UColdSteelStatusModel* Model)
{
    const float Age=GetWorld()->GetTimeSeconds()-5.f;if(Age<0)return;
    const int32 Phase=FMath::FloorToInt(Age/1.5f);
    const TCHAR* Names[]={TEXT("live"),TEXT("low"),TEXT("reload"),TEXT("empty"),TEXT("exhausted"),TEXT("large"),TEXT("unequipped")};
    if(Phase>=7){UE_LOG(LogTemp,Display,TEXT("AmmoReadoutPreview: COMPLETE failures=%d"),PreviewFailures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    const int32 Magazine[]={30,5,5,0,0,999,0},Reserve[]={90,90,90,90,0,99999,0};
    if(Phase>0)Present(TEXT("M4A1"),TEXT("5.56 mm"),Magazine[Phase],Reserve[Phase],Phase==5?1000:30,Phase==2,Phase!=6);
    if(LastCapture==Phase||FMath::Fmod(Age,1.5f)<.6f)return;LastCapture=Phase;
    bool OK=!GetOwningPlayer()->bShowMouseCursor&&!IsFocusable()&&GetVisibility()==ESlateVisibility::HitTestInvisible;
    if(Phase==0)OK&=Character&&Current->GetText().ToString()==FString::Printf(TEXT("%02d"),Character->GetMagazineAmmo())&&Spare->GetText().ToString()==FString::FromInt(Character->GetReserveAmmo());
    if(Phase==1||Phase==2)OK&=Current->GetText().ToString()==TEXT("05")&&Spare->GetText().ToString()==TEXT("90");
    if(Phase==4)OK&=Current->GetText().ToString()==TEXT("00")&&Spare->GetText().ToString()==TEXT("0");
    if(Phase==5)OK&=Spare->GetText().ToString()==TEXT("99999");
    if(Phase==6)OK&=Current->GetText().ToString()==TEXT("--");
    if(!OK)++PreviewFailures;
    const FString Out=FPaths::ProjectSavedDir()/TEXT("AmmoReadout20260909");IFileManager::Get().MakeDirectory(*Out,true);int32 W,H;GetOwningPlayer()->GetViewportSize(W,H);
    FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("%d-%s.png"),W,Names[Phase]),true,false);
    UE_LOG(LogTemp,Display,TEXT("AmmoReadoutPreview: %s state=%s live=%d/%d profile=%s"),OK?TEXT("PASS"):TEXT("FAIL"),Names[Phase],Character?Character->GetMagazineAmmo():0,Character?Character->GetReserveAmmo():0,*Model->ProfileSlot());
}
