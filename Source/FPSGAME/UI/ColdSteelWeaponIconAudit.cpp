#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/ScrollBox.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Serialization/JsonSerializer.h"
using namespace ColdSteelInventory;
void UColdSteelHUDWidget::RunWeaponIconAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!P->IsAudit())return;
    auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    struct FRun{int32 Phase=0,Checks=0,Failures=0,Wait=0,Renders=0;FTimerHandle Timer;TArray<FString> Ids;TObjectPtr<UTexture2D> Factory=nullptr;FString OriginalKey;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("WeaponIconAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto State=P->Snapshot();State.Items.Empty();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    const TCHAR* Muzzles[]={TEXT("false"),TEXT("true"),TEXT("brake"),TEXT("titanium_brake"),TEXT("false")};
    const int32 Variants=Guns->Weapon(TEXT("ue_akm"))?5:4;
    for(int32 N=0;N<Variants;++N){auto I=P->CreateItem(N==4?TEXT("ue_akm"):TEXT("ue_m4a1"));I.Place=N==0?1:0;I.Cell=N==0?6:N==4?36:(N-1)*5;
        if(N>0&&N<4){TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("muzzle"),Muzzles[N]);if(N==1){Parts->SetStringField(TEXT("optic"),TEXT("holographic"));Parts->SetStringField(TEXT("magazine"),TEXT("large_drum"));}Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));}
        R->Ids.Add(I.InstanceId);State.Items.Add(I);
    }
    Check(P->CommitState(State),TEXT("isolated factory modified and AKM inventory fixture"));SetInventoryOpen(true);SetInventoryTab(false);
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,P,Icons,Guns,R,Check]()
    {
        if(!Icons->IsIdle()&&R->Wait++<50)return;
        R->Wait=0;const FString Dir=FPaths::ProjectSavedDir()/TEXT("WeaponIcons");IFileManager::Get().MakeDirectory(*Dir,true);
        const int32 Width=UWidgetLayoutLibrary::GetViewportSize(this).X;
        auto Capture=[&](const TCHAR* Name){GetOwningPlayer()->SetMouseLocation(1,1);HideItemTooltip(true);FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%d.png"),Name,Width),true,false);};
        auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;
        switch(R->Phase++){
        case 0:
            Check(Board&&Icons->IsIdle(),TEXT("icon queue completed in live inventory board"));
            for(int32 N=0;N<R->Ids.Num();++N){const auto* I=P->FindItem(R->Ids[N]);const auto* Brush=I?Icons->Find(*I):nullptr;auto* T=Brush?Cast<UTexture2D>(Brush->GetResourceObject()):nullptr;
                Check(T&&Board&&Board->ItemBrush(*I)==Brush,TEXT("bag and equipment resolve current instance model texture"));if(!T)continue;
                if(N==0){R->Factory=T;R->OriginalKey=Icons->Key(*I);}
                const auto& Mip=T->GetPlatformData()->Mips[0];const FColor* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());
                int32 Visible=0;bool BorderClear=true;TArray<FColor> Copy;Copy.Append(Pixels,T->GetSizeX()*T->GetSizeY());
                for(int32 Y=0;Y<T->GetSizeY();++Y)for(int32 X=0;X<T->GetSizeX();++X){const auto A=Pixels[Y*T->GetSizeX()+X].A;Visible+=A>10;if(X==0||Y==0||X==T->GetSizeX()-1||Y==T->GetSizeY()-1)BorderClear&=A<10;}Mip.BulkData.Unlock();
                Check(Visible>100&&BorderClear,TEXT("transparent model render has visible geometry and unclipped borders"));TArray<uint8> PNG;FImageUtils::CompressImageArray(T->GetSizeX(),T->GetSizeY(),Copy,PNG);FFileHelper::SaveArrayToFile(PNG,*(Dir/FString::Printf(TEXT("variant-%d-%d.png"),N,Width)));
            }
            Check(P->Equipped()&&P->Equipped()->InstanceId==R->Ids[0]&&P->Items().Num()==R->Ids.Num(),TEXT("studio did not equip or alter player inventory"));
            R->Renders=Icons->RenderCount();P->SaveNow();Capture(TEXT("inventory"));break;
        case 1:
            Check(Icons->RenderCount()==R->Renders,TEXT("autosave reuses cached model image"));
            Check(Guns->Begin(R->Ids[2])&&Guns->Select(TEXT("optic"),TEXT("holographic")),TEXT("draft modification on unequipped rifle"));
            {const auto* I=P->FindItem(R->Ids[2]);Check(Icons->Key(*I).Contains(TEXT("optic"))==false,TEXT("unapplied draft does not leak into saved inventory image"));}
            Check(Guns->Apply(),TEXT("apply saved per-instance modification"));Guns->Close();break;
        case 2:
            Check(Icons->RenderCount()==R->Renders+1&&Icons->Find(*P->FindItem(R->Ids[2])),TEXT("applying modifications regenerates exactly changed configuration"));
            Check(Icons->Find(*P->FindItem(R->Ids[0]))->GetResourceObject()==R->Factory,TEXT("same model other instance retains factory appearance"));
            Check(P->MoveItem(R->Ids[1],1,9),TEXT("modified rifle moves to second equipment slot"));Capture(TEXT("equipment"));break;
        case 3:
            Check(Board&&Board->ItemBrush(*P->FindItem(R->Ids[1]))==Icons->Find(*P->FindItem(R->Ids[1])),TEXT("equipped modified rifle uses same per-instance icon"));
            Check(P->ReloadProfile()&&Icons->Key(*P->FindItem(R->Ids[2])).Contains(TEXT("optic=holographic")),TEXT("saved modification survives reload"));
            if(Scroll)Scroll->ScrollToEnd();Capture(TEXT("backpack"));break;
        default:
            SetInventoryOpen(false);GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("WeaponIconAudit: COMPLETE checks=%d failures=%d renders=%d"),R->Checks,R->Failures,Icons->RenderCount());GetOwningPlayer()->ConsoleCommand(TEXT("quit"));break;
        }
    }),1.f,true);
}
