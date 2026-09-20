#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDualPistolQuickCombatRegression,
    "FPSGAME.Weapons.DualPistol.QuickCombatState",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDualPistolQuickCombatRegression::RunTest(const FString& Parameters)
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("DualQuickCombatStateTest"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!TestNotNull(TEXT("isolated world"),World))return false;
    auto* Player=World->SpawnActor<AFPSGAMECharacter>();
    auto* Controller=World->SpawnActor<APlayerController>();
    Controller->Possess(Player);Controller->bShowMouseCursor=false;
    // No BeginPlay/game instance/profile: these probes cannot alter user saves,
    // spend a cooldown, fire a projectile, or interrupt the user's current pawn.
    auto* Dual=Player->DualPistols.Get();Dual->Player=Player;Dual->bActive=true;
    Player->bUseM1911=true;Player->bUseM4Infima=false;Player->bInventoryWeaponReady=true;
    Player->WeaponState=EAKMWeaponState::Idle;
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Dual->Hands[Side];H.Rounds=4;H.Revolver=Side==1;
        H.Mesh=NewObject<USkeletalMeshComponent>(Player);
        H.Anim=NewObject<UFPSGunplayAnimInstance>(H.Mesh);
        const FString Weapon=Side?TEXT("DW715"):TEXT("M1911"),Hand=Side?TEXT("l"):TEXT("r");
        for(const TCHAR* Kind:{TEXT("quickcombat"),TEXT("quickcombat_left"),TEXT("quickcombat_empty"),TEXT("quickcombat_left_empty")})
        {
            if(H.Revolver && FString(Kind).EndsWith(TEXT("_empty")))continue;
            const FString Path=FString::Printf(TEXT("/Game/Weapons/DualPistolQuickCombat20260920/VideoRefV3/%s/%s/Animations/A_Dual_%s_%s_%s"),*Weapon,*Hand,*Weapon,*Hand,Kind);
            H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*Path));
            TestNotNull(*Path,H.Clips.FindRef(Kind).Get());
        }
        for(const TCHAR* Kind:{TEXT("fire"),TEXT("fire_last"),TEXT("equip")})H.Clips.Add(Kind,NewObject<UAnimSequence>(Player));
    }
    TestTrue(TEXT("idle dual mixed pistols ready"),Dual->QuickCombatBlockReason()==nullptr);
    Player->InspectAnimation=NewObject<UAnimSequence>(Player);
    Player->InspectPressed();
    TestTrue(TEXT("L cannot enter inactive single-pistol inspect state"),Player->WeaponState==EAKMWeaponState::Idle);
    Player->WeaponState=EAKMWeaponState::Inspecting;
    TestFalse(TEXT("legacy inspect cannot block dual melee"),Player->IsWeaponBusy());
    Player->UpdateWeaponState(.016f);
    TestTrue(TEXT("existing stuck inspect recovers"),Player->WeaponState==EAKMWeaponState::Idle);
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Dual->Hands[Side];
        for(const TCHAR* Kind:{TEXT("fire"),TEXT("fire_last"),TEXT("equip")})
        {
            H.Action=H.Clips.FindRef(Kind);H.ActionTime=.02f;
            TestTrue(*FString::Printf(TEXT("side%d interrupts %s"),Side,Kind),Dual->QuickCombatBlockReason()==nullptr);
        }
        H.Reloading=true;
        TestTrue(TEXT("reload remains blocking"),Dual->QuickCombatBlockReason()!=nullptr);
        H.Reloading=false;H.Action=NewObject<UAnimSequence>(Player);
        TestTrue(TEXT("unrecognized action remains blocking"),Dual->QuickCombatBlockReason()!=nullptr);
        H.Action=nullptr;H.Rounds=0;
        TestTrue(TEXT("empty pistol/revolver selects a valid clip"),Dual->QuickCombatBlockReason()==nullptr);
        H.Rounds=4;
    }
    Controller->bShowMouseCursor=true;
    TestTrue(TEXT("menu still blocks action input"),Dual->QuickCombatBlockReason()!=nullptr);
    Controller->bShowMouseCursor=false;
    Player->bIsSliding=true;
    TestTrue(TEXT("slide still blocks melee"),Dual->QuickCombatBlockReason()!=nullptr);
    Player->bIsSliding=false;
    Dual->bActive=false;Player->WeaponState=EAKMWeaponState::Inspecting;
    TestTrue(TEXT("single-pistol inspect remains busy"),Player->IsWeaponBusy());
    World->DestroyWorld(false);
    return !HasAnyErrors();
}
#endif
