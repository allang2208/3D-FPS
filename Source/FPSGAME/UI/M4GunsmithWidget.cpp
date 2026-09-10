#include "M4GunsmithWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "InputCoreTypes.h"

UGunsmithSystem* UM4GunsmithWidget::Model()const{return GetGameInstance()->GetSubsystem<UGunsmithSystem>();}
void UM4GunsmithWidget::Choose(bool bHolo)
{
    ChooseOption(TEXT("optic"),bHolo?TEXT("holographic"):TEXT("false"));
}
bool UM4GunsmithWidget::ApplyDraft(){const bool Result=Model()->Apply();RefreshPresentation();return Result;}
void UM4GunsmithWidget::ChooseDrum(bool bDrum)
{
    ChooseOption(TEXT("magazine"),bDrum?TEXT("large_drum"):TEXT("false"));
}
void UM4GunsmithWidget::ChooseOption(const FString& SlotKey,const FString& Id)
{
    PreviewMotion=1.f;
    const auto* Weapon=Model()->Weapon(Model()->Definition());
    if(!Weapon||!Weapon->Allowed.Contains(SlotKey)||!Model()->Select(SlotKey,Id))return;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance())
        if(auto* C=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn()))
        {
            C->SetGunsmithOptic(Model()->Draft().FindRef(TEXT("optic"))==TEXT("holographic"));
            C->SetGunsmithDrum(Model()->Draft().FindRef(TEXT("magazine"))==TEXT("large_drum"));
            C->SetGunsmithMuzzle(Model()->Draft().FindRef(TEXT("muzzle")));
        }
}
void UM4GunsmithWidget::SetAimPreview(bool bAim)
{
    PreviewMotion=1.f;
    SetSidePreview(false);
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bAim=bAim&&P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance();
    bAimPreview=bAim;if(auto* C=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn()))C->SetGunsmithAimPreview(bAim);
}
void UM4GunsmithWidget::SetSidePreview(bool bSide)
{
    PreviewMotion=1.f;
    if(bSide)PreviewOrbit=FVector2D::ZeroVector;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bSidePreview=bSide&&P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance();
    if(auto* C=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn()))
    {
        if(bSidePreview){bAimPreview=false;C->SetGunsmithAimPreview(false);}
        C->SetGunsmithInspection(bSidePreview);
    }
}
void UM4GunsmithWidget::SelectCategory(const FString& CategorySlot)
{
    if(SelectedCategory==CategorySlot)return;
    if(const auto* W=Model()->Weapon(Model()->Definition()))if(W->Allowed.Contains(CategorySlot)){SelectedCategory=CategorySlot;RefreshPresentation();}
}
void UM4GunsmithWidget::SetCompareFactory(bool bFactory){bCompareFactory=bFactory;RefreshPresentation();}
TSharedRef<SWidget> UM4GunsmithWidget::RebuildWidget(){SetIsFocusable(true);return BuildWorkbench();}
void UM4GunsmithWidget::NativeConstruct()
{
    Super::NativeConstruct();
    GunsmithHandle=Model()->OnChanged.AddUObject(this,&UM4GunsmithWidget::RefreshPresentation);
    ProfileHandle=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->OnChanged.AddUObject(this,&UM4GunsmithWidget::RefreshPresentation);
    SetSidePreview(true);InitializePreview();RefreshPresentation();
}
void UM4GunsmithWidget::NativeDestruct()
{
    Model()->OnChanged.Remove(GunsmithHandle);
    GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->OnChanged.Remove(ProfileHandle);
    SetAimPreview(false);ReleasePreview();Super::NativeDestruct();
}
FReply UM4GunsmithWidget::NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if(E.GetKey()==EKeys::Escape||E.GetKey()==EKeys::Tab||E.GetKey()==EKeys::J)
    {if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseGunsmith();return FReply::Handled();}
    return Super::NativeOnKeyDown(G,E);
}
