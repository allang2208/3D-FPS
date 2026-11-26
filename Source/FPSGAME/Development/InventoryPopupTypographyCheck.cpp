#include "ColdSteelTypographyCheckCommandlet.h"
#if WITH_EDITOR
#include "../UI/ColdSteelInventoryPopup.h"
#include "../UI/ColdSteelInventoryWidget.h"
#include "../UI/ColdSteelItemTooltip.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "Blueprint/WidgetTree.h"
#include "Components/EditableTextBox.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "Fonts/FontCache.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/ScopeExit.h"
#include "Widgets/Text/STextBlock.h"

int32 UColdSteelTypographyCheckCommandlet::CheckInventoryPopups()
{
    const FString Original = FCommandLine::Get();
    const FString Profile = TEXT("PopupTypographyAudit_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original + TEXT(" -ColdSteelProfile=") + Profile));
    ON_SCOPE_EXIT { FCommandLine::Set(*Original); };
    TStrongObjectPtr<UGameInstance> GI(NewObject<UGameInstance>(GEngine));
    GI->InitializeStandalone(TEXT("InventoryPopupTypography"));
    UWorld* World = GI->GetWorld();
    ON_SCOPE_EXIT {
        GI->Shutdown();
        if (World) { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); }
    };
    auto* Model = GI->GetSubsystem<UColdSteelStatusModel>();
    if (!World || !Model || !Model->IsAudit() || Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile) return 2;
    auto* Local = NewObject<ULocalPlayer>(GEngine);
    GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));
    auto* PC = World->SpawnActor<APlayerController>();
    PC->Player=Local; Local->PlayerController=PC; World->AddController(PC);

    auto State = Model->Snapshot();
    auto Gun = Model->CreateItem(TEXT("ue_m4a1"));
    auto Equipped = Model->CreateItem(TEXT("ue_m4a1"));
    auto Armor = Model->CreateItem(TEXT("ue_chainmail_shirt"));
    auto Potion = Model->CreateItem(TEXT("hp_potion"),3);
    Equipped.Place=1; Equipped.Cell=6; Gun.Place=0; Gun.Cell=0; Gun.Magazine=7;
    Armor.Place=0; Armor.Cell=24; Potion.Place=0; Potion.Cell=36;
    State.Items={Equipped,Gun,Armor,Potion}; State.ActiveWeaponSlot=6;
    if (!Model->CommitState(MoveTemp(State))) return 2;

    const auto Cache = FSlateApplication::Get().GetRenderer()->GetFontCache();
    const auto Family = ColdSteelUI::TextFont(12.f).CompositeFont;
    bool Passed = true;
    auto Inspect = [&](UUserWidget* View,const TCHAR* Mode,const TMap<FString,FName>& Expected,bool ExpectInput=false)
    {
        View->TakeWidget();
        TArray<UWidget*> Widgets;
        View->WidgetTree->GetAllWidgets(Widgets);
        TSet<FString> Matched;
        int32 Labels=0, Inputs=0;
        for (auto* Widget : Widgets)
        {
            FSlateFontInfo Font;
            FString Text;
            if (auto* Label=Cast<UTextBlock>(Widget))
            {
                const auto Slate=Label->TakeWidget();
                Font=Slate->GetType()==TEXT("STextBlock") ? StaticCastSharedRef<STextBlock>(Slate)->GetFont() : Label->GetFont();
                Text=Label->GetText().ToString(); ++Labels;
            }
            else if (auto* Input=Cast<UEditableTextBox>(Widget)) { Font=Input->GetWidgetStyle().TextStyle.Font; Text=Input->GetText().ToString(); ++Inputs; }
            else continue;
            const FString Filename=Cache->GetDefaultFontData(Font).GetFontFilename();
            bool UsesFamily=Font.CompositeFont==Family && FPaths::GetCleanFilename(Filename).StartsWith(TEXT("NotoSansSC-"));
            for (const TCHAR Ch : Text)
            {
                if (!(FChar::IsAlnum(Ch) || (Ch>=0x3400 && Ch<=0x9FFF))) continue;
                float Scaling=1.f;
                if (Cache->GetFontDataForCodepoint(Font,Ch,Scaling).GetFontFilename()!=Filename) { UsesFamily=false; break; }
            }
            if (!UsesFamily) { Passed=false; UE_LOG(LogTemp,Error,TEXT("POPUP_FONT %s: %s -> %s"),Mode,*Text,*Filename); }
            if (auto* Weight=Expected.Find(Text); Weight && Font.TypefaceFontName==*Weight) Matched.Add(Text);
        }
        const bool AllRoles=Matched.Num()==Expected.Num() && Labels>0 && Inputs==int32(ExpectInput);
        if (!AllRoles)
            for (const auto& Pair:Expected)
                if (!Matched.Contains(Pair.Key)) UE_LOG(LogTemp,Error,TEXT("POPUP_FONT %s missing %s / %s"),Mode,*Pair.Key,*Pair.Value.ToString());
        Passed &= AllRoles;
        UE_LOG(LogTemp,Display,TEXT("POPUP_FONT %s labels=%d inputs=%d expected_roles=%d/%d"),Mode,Labels,Inputs,Matched.Num(),Expected.Num());
    };
    auto* Card=CreateWidget<UColdSteelItemTooltip>(GI.Get());
    auto* Board=CreateWidget<UColdSteelInventoryWidget>(GI.Get());
    auto* Menu=CreateWidget<UColdSteelInventoryPopup>(GI.Get());
    auto* Split=CreateWidget<UColdSteelInventoryPopup>(GI.Get());
    if (!Card || !Board || !Menu || !Split) return 2;
    // The HUD normally keeps a strong reference to the card's Slate widget through its canvas slot.
    const TSharedRef<SWidget> CardSlate=Card->TakeWidget();
    const FString GunName=ColdSteelInventory::Text(Gun,TEXT("name"));
    const FString PotionName=ColdSteelInventory::Text(Potion,TEXT("name"));
    const FName Regular(TEXT("Regular")), SemiBold(TEXT("SemiBold")), Bold(TEXT("Bold"));
    const FVector2D Anchor=FVector2D::ZeroVector;
    Card->ShowItem(Gun.InstanceId,Anchor,false,Board);
    Inspect(Card,TEXT("weapon-hover"),{{GunName,Bold},{TEXT("核心属性"),SemiBold}});
    Card->ShowItem(Gun.InstanceId,Anchor,true,Board);
    Inspect(Card,TEXT("weapon-details-and-comparison"),{{TEXT("详细参数"),SemiBold},{TEXT("完整装备对比"),SemiBold},{TEXT("差值（已装备 → 当前查看）"),Regular}});
    FColdSteelItemTooltipPreview Updated;
    Updated.Item=Gun; Updated.Item.Magazine=9;
    Card->ShowItem(Gun.InstanceId,Anchor,true,Board,&Updated);
    auto* Gunsmith=GI->GetSubsystem<UGunsmithSystem>();
    const auto Data=BuildColdSteelItemTooltip(Updated.Item,Model,Gunsmith);
    if(Data.Cards.IsEmpty()) return 2;
    const auto* Rounds=Data.Cards.Last().Rows.FindByPredicate([](const auto& R){return R.Label==TEXT("子弹数");});
    if(!Rounds || !Rounds->Value.StartsWith(TEXT("9 / "))) return 2;
    Inspect(Card,TEXT("weapon-refreshed"),{{Rounds->Value,Regular},{TEXT("详细参数"),SemiBold}});
    Card->Hide(true);
    Card->ShowItem(Armor.InstanceId,Anchor,false,Board);
    Inspect(Card,TEXT("armor-set-hover"),{{ColdSteelInventory::Text(Armor,TEXT("name")),Bold},{TEXT("增益"),SemiBold}});
    Card->Hide(true);
    Card->ShowItem(Potion.InstanceId,Anchor,true,Board);
    Inspect(Card,TEXT("potion-details"),{{PotionName,Bold},{TEXT("详细参数"),SemiBold}});
    Menu->Open(Board,Model,Potion.InstanceId,Anchor,false);
    Inspect(Menu,TEXT("action-menu"),{{PotionName,SemiBold},{TEXT("查看详情"),Regular}});
    Split->Open(Board,Model,Potion.InstanceId,Anchor,true);
    Inspect(Split,TEXT("split-quantity"),{{TEXT("拆分 · ")+PotionName,SemiBold},{TEXT("确认拆分 · Enter"),Regular}},true);
    Card->Hide(true); Menu->Close(false); Split->Close(false);
    return Passed ? 0 : 1;
}
#endif
