"""Regenerate the Integration patch bundle (off-hand kukri uppercut R3 + single-thrust damage/form R6).

For each shared host this batch touched:
  * revert the R3 edits -> for already-patched hosts this must hash to the
    recorded result sha256 (verifies the reversion is exact).
  * for already-patched hosts additionally revert the earlier batch's edits
    -> must hash to the recorded preimage sha256.
  * for newly-patched hosts the reverted text IS the preimage.
  * emit diff(preimage, current) in the bundle's format: LF structural lines,
    CRLF payload lines. Hashes in integration-prerequisites.json are
    LF-normalized UTF-8.

Every generated patch round-trips: applied onto a CRLF preimage it must hash
to the recorded result (LF-normalized).
"""
import hashlib, json, os, subprocess, sys

REPO = r'D:/FPS3D/FPSGAME'
PKG = os.path.join(REPO, 'Docs/Publication/DualPistolKukri20261025')
SCR = os.path.join(REPO, 'SourceAssets/DualPistolKukri20261025/Work/bundle')


def norm(b):
    return b.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def sha_text(s):
    return hashlib.sha256(norm(s.encode('utf-8'))).hexdigest()


def sha_path(p):
    return hashlib.sha256(norm(open(p, 'rb').read())).hexdigest()


def load(rel):
    with open(os.path.join(REPO, rel), encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n').replace('\r', '\n')


def save(path, text, crlf=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if crlf:
        text = text.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


# (new, old) pairs reverted to reconstruct each file's pre-R3 state.
REVERTS = {
    'Source/FPSGAME/FPSGAMECharacter.cpp': [
        (
            "    // 副手弯刀出刀/上挑进行中同样不接开火（枪随动作走位，结束才恢复）。\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();\n"
            "        OffhandKukri&&(OffhandKukri->IsQuickCombatActive()||OffhandKukri->IsUppercutActive()))return;",
            "    // 副手弯刀出刀进行中同样不接开火（枪随动作走位，结束才恢复）。\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return;",
        ),
        (
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();\n"
            "        OffhandKukri&&(OffhandKukri->IsQuickCombatActive()||OffhandKukri->IsUppercutActive()))return true;",
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return true;",
        ),
        (
            "    if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>()){OffhandKukri->CancelQuickCombat();OffhandKukri->CancelUppercut();}",
            "    if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->CancelQuickCombat();",
        ),
        (
            "        (OffhandKukri && (OffhandKukri->IsQuickCombatActive()||OffhandKukri->IsUppercutActive()));",
            "        (OffhandKukri && OffhandKukri->IsQuickCombatActive());",
        ),
    ],
    'Source/FPSGAME/FPSGAMECharacterActionPriority.cpp': [
        (
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();\n"
            "        OffhandKukri&&(OffhandKukri->IsQuickCombatActive()||OffhandKukri->IsUppercutActive()))return false;",
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return false;",
        ),
        (
            "        if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>()){OffhandKukri->CancelQuickCombat();OffhandKukri->CancelUppercut();}",
            "        if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->CancelQuickCombat();",
        ),
    ],
    'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp': [
        # R6 (2026-10-26): the single off-hand thrust's shared damage formula and blade form.
        (
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n#include "../Weapons/Kukri/OffhandKukriThrust.h"',
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            "    if (Report.AttackMeta & 0x80)\n"
            "    {\n"
            "        // 副手弯刀快速近战（单次突刺）：申报武器是影子档案副手槽位的弯刀且主手是双持手枪时，\n"
            "        // 伤害 = 副手物理面板 200% × 快速近战增伤 + 快速近战技能伤害（客户端同式，OffhandKukriThrust.h）。\n"
            "        if(OffhandKukriThrust::IsOffhandThrust(ShadowModel,Item))\n"
            "            return OffhandKukriThrust::Damage(*Item,ShadowModel);\n"
            "        return ShadowModel ? ShadowModel->QuickCombatStats().Damage : Panel;\n"
            "    }",
            "    if (Report.AttackMeta & 0x80)\n"
            "    {\n"
            "        // 副手弯刀快速近战：申报武器是影子档案副手槽位的弯刀且主手是双持手枪时，\n"
            "        // 伤害 = 该副手武器物理面板（基础+附加）的 200%（客户端同式，OffhandKukriStrike.cpp）。\n"
            "        if(Item&&ShadowModel&&ColdSteelInventory::IsOneHandedMelee(*Item))\n"
            "        {\n"
            "            const auto Snap=ShadowModel->Snapshot();\n"
            "            const auto* Offhand=ShadowModel->Equipped(Snap.ActiveWeaponSlot==6?8:11);\n"
            "            const auto* Primary=ShadowModel->Equipped(Snap.ActiveWeaponSlot);\n"
            "            if(Offhand&&Offhand->InstanceId==Item->InstanceId&&Primary&&ColdSteelInventory::IsDualPistol(*Primary))\n"
            "            {\n"
            "                const auto Melee=ColdSteelMelee::Evaluate(*Item,ShadowModel);\n"
            "                return float(2.*(Melee.DamageParts.BasePhysical+Melee.DamageParts.AddedPhysical));\n"
            "            }\n"
            "        }\n"
            "        return ShadowModel ? ShadowModel->QuickCombatStats().Damage : Panel;\n"
            "    }",
        ),
        (
            "    // The pistol + off-hand kukri F is a blade thrust (OffhandKukriStrike.cpp); every other quick melee is a blunt blow.\n"
            "    if((Report.AttackMeta&0x80)&&OffhandKukriThrust::IsOffhandThrust(ShadowModel,Declared))Shot.AttackForm=EMonsterAttackForm::Blade;\n"
            "    else if((Report.AttackMeta&0x80)||Report.AttackMeta==UnarmedPunch::AttackMeta)Shot.AttackForm=EMonsterAttackForm::Blunt;",
            "    if((Report.AttackMeta&0x80)||Report.AttackMeta==UnarmedPunch::AttackMeta)Shot.AttackForm=EMonsterAttackForm::Blunt;",
        ),
        (
            "        const auto* Item=ShadowModel->Equipped();\n"
            "        // The one-handed kukri shares the uppercut receipt (KukriUppercut.cpp); so does the\n"
            "        // off-hand kukri behind a main-hand dual pistol (OffhandKukriUppercut.cpp).\n"
            "        if(Item&&!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsOneHandedMelee(*Item)\n"
            "            &&ColdSteelInventory::IsDualPistol(*Item))\n"
            "            if(const auto* Off=ShadowModel->Equipped(ShadowModel->Snapshot().ActiveWeaponSlot==6?8:11);\n"
            "                Off&&ColdSteelInventory::IsOneHandedMelee(*Off))Item=Off;",
            "        const auto* Item=ShadowModel->Equipped();\n"
            "        // The one-handed kukri shares the uppercut receipt (KukriUppercut.cpp).",
        ),
    ],
    'Source/FPSGAME/Multiplayer/ColdSteelUppercutAuthority.cpp': [
        (
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n#include "../Weapons/Kukri/OffhandKukriComponent.h"',
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            "    // The kukri's uppercut uses the same release receipt (one-handed melee, KukriUppercut.cpp);\n"
            "    // the off-hand kukri behind a main-hand dual pistol does too (OffhandKukriUppercut.cpp).\n"
            "    if(Model&&Item&&!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsOneHandedMelee(*Item)\n"
            "        &&ColdSteelInventory::IsDualPistol(*Item))\n"
            "        if(const auto* Off=Model->Equipped(Model->Snapshot().ActiveWeaponSlot==6?8:11);\n"
            "            Off&&ColdSteelInventory::IsOneHandedMelee(*Off))Item=Off;",
            "    // The kukri's uppercut uses the same release receipt (one-handed melee, KukriUppercut.cpp).",
        ),
        (
            "    const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;\n"
            "    // Same off-hand resolution as the client request: the declared weapon is the off-hand kukri's id.\n"
            "    if(Item&&!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsOneHandedMelee(*Item)\n"
            "        &&ColdSteelInventory::IsDualPistol(*Item))\n"
            "        if(const auto* Off=ShadowModel->Equipped(ShadowModel->Snapshot().ActiveWeaponSlot==6?8:11);\n"
            "            Off&&ColdSteelInventory::IsOneHandedMelee(*Off))Item=Off;",
            "    const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;",
        ),
        (
            "    const auto* Item=UppercutRewardModel?UppercutRewardModel->Equipped():nullptr;\n"
            "    if(Item&&!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsOneHandedMelee(*Item)\n"
            "        &&ColdSteelInventory::IsDualPistol(*Item))\n"
            "        if(const auto* Off=UppercutRewardModel->Equipped(UppercutRewardModel->Snapshot().ActiveWeaponSlot==6?8:11);\n"
            "            Off&&ColdSteelInventory::IsOneHandedMelee(*Off))Item=Off;",
            "    const auto* Item=UppercutRewardModel?UppercutRewardModel->Equipped():nullptr;",
        ),
        (
            "        if(auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsUppercutActive())Kukri->CancelAction();\n"
            "        if(auto* Offhand=Pawn->FindComponentByClass<UOffhandKukriComponent>();Offhand&&Offhand->IsUppercutActive())Offhand->CancelUppercut();",
            "        if(auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsUppercutActive())Kukri->CancelAction();",
        ),
    ],
    'Source/FPSGAME/UI/ColdSteelQuickBarModel.cpp': [
        (
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n#include "../Weapons/Kukri/OffhandKukriComponent.h"',
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            "        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->BeginUppercut();\n"
            "        // 手枪＋副手弯刀：上挑由副手刀镜像出手（OffhandKukriUppercut.cpp），排在主手弯刀之后、双手剑之前。\n"
            "        if(auto* Offhand=Player->FindComponentByClass<UOffhandKukriComponent>();Offhand&&Offhand->IsEquipped())return Offhand->BeginUppercut();",
            "        if(auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())return Kukri->BeginUppercut();",
        ),
    ],
    'Source/FPSGAME/UI/ColdSteelQuickSlot.cpp': [
        (
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n#include "../Weapons/Kukri/OffhandKukriComponent.h"',
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            "        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;\n"
            "        const auto* Offhand=Player?Player->FindComponentByClass<UOffhandKukriComponent>():nullptr;\n"
            "        Message=HammerItem&&ColdSteelInventory::IsTwoHandedBlunt(*HammerItem)&&Tool?\n"
            "            Tool->UppercutStatusText():Kukri&&Kukri->IsEquipped()?Kukri->UppercutStatusText():\n"
            "            Offhand&&Offhand->IsEquipped()?Offhand->UppercutStatusText():\n"
            "            Ability?Ability->UppercutStatusText():TEXT(\"需近战\");",
            "        const auto* Kukri=Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;\n"
            "        Message=HammerItem&&ColdSteelInventory::IsTwoHandedBlunt(*HammerItem)&&Tool?\n"
            "            Tool->UppercutStatusText():Kukri&&Kukri->IsEquipped()?Kukri->UppercutStatusText():\n"
            "            Ability?Ability->UppercutStatusText():TEXT(\"需近战\");",
        ),
    ],
    'Source/FPSGAME/Skills/ColdSteelHeavyStrikeModel.cpp': [
        (
            "/** The item the uppercut bills and validates against: the melee weapon, or the off-hand kukri behind a dual pistol. */\n"
            "const FColdSteelItem* UppercutItem(const UColdSteelStatusModel* Profile)\n"
            "{\n"
            "    const auto* Item=Profile->Equipped();\n"
            "    if(!Item||ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsOneHandedMelee(*Item))return Item;\n"
            "    if(!ColdSteelInventory::IsDualPistol(*Item))return Item;\n"
            "    // Pistol + offhand kukri (OffhandKukriUppercut.cpp): the cast swings the off-hand blade.\n"
            "    const auto State=Profile->Snapshot();\n"
            "    const auto* Off=Profile->Equipped(State.ActiveWeaponSlot==6?8:11);\n"
            "    return Off&&ColdSteelInventory::IsOneHandedMelee(*Off)?Off:Item;\n"
            "}\n"
            "\n"
            "FMeleeModifiers UppercutModifiers(const UColdSteelStatusModel* Profile)\n"
            "{\n"
            "    const auto* Tool=Profile->ActiveProductionTool();\n"
            "    const auto* Gunsmith=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();\n"
            "    if(Tool&&ColdSteelInventory::IsTwoHandedBlunt(*Tool)&&Gunsmith)\n"
            "        return Gunsmith->Calculate(Tool->Definition,Gunsmith->Installed(*Tool)).Melee;\n"
            "    const auto* Item=UppercutItem(Profile);\n"
            "    return Item&&(ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsOneHandedMelee(*Item))?\n"
            "        ColdSteelMelee::Evaluate(*Item,Profile).Modifiers:ColdSteelMelee::EquippedModifiers(Profile);\n"
            "}",
            "FMeleeModifiers UppercutModifiers(const UColdSteelStatusModel* Profile)\n"
            "{\n"
            "    const auto* Tool=Profile->ActiveProductionTool();\n"
            "    const auto* Gunsmith=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();\n"
            "    return Tool&&ColdSteelInventory::IsTwoHandedBlunt(*Tool)&&Gunsmith?\n"
            "        Gunsmith->Calculate(Tool->Definition,Gunsmith->Installed(*Tool)).Melee:ColdSteelMelee::EquippedModifiers(Profile);\n"
            "}",
        ),
        (
            "    const auto* Tool=ActiveProductionTool();const auto* Item=Tool?Tool:UppercutItem(this);\n"
            "    // Two-handed sword, two-handed blunt tool, the one-handed kukri (KukriUppercut.cpp, 2026-10-23),\n"
            "    // or the off-hand kukri behind a dual pistol (OffhandKukriUppercut.cpp, 2026-10-25).",
            "    const auto* Tool=ActiveProductionTool();const auto* Item=Tool?Tool:Equipped();\n"
            "    // Two-handed sword, two-handed blunt tool, or the one-handed kukri (KukriUppercut.cpp, 2026-10-23).",
        ),
    ],
    # R8 (2026-10-26): melee catalog tuning re-synced on load for every melee weapon (was zhenyue reach + zhanmadao
    # clock only). The R1 hunks of this host are recovered by reverse-applying its published patch (PRIOR_PATCH).
    'Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp': [
        (
            "            // Melee base cadence / reach / damage / guard economy are catalog tuning, not instance upgrades: an\n"
            "            // instance keeps the catalog snapshot of the day it was created, so two of the same weapon could swing\n"
            "            // at different speeds after a rebalance (two kukris: attack_seconds 0.8 vs 1.9792, reach 150 vs 220).\n"
            "            // Same field set as SanitizeNetworkItem; forging quality, parts and enhancement stay instance state.\n"
            "            if(ColdSteelInventory::IsMeleeWeapon(I)&&CatalogData&&\n"
            "                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),ItemData)&&ItemData)\n"
            "            {\n"
            "                bool TuningChanged=false;\n"
            "                for(const TCHAR* Key:{TEXT(\"melee_damage\"),TEXT(\"melee_reach_cm\"),TEXT(\"attack_seconds\"),TEXT(\"swing_seconds\"),\n"
            "                    TEXT(\"contact_seconds\"),TEXT(\"melee_stamina\"),TEXT(\"block_stamina\"),TEXT(\"block_reduction\")})\n"
            "                {\n"
            "                    double CatalogValue=0.,StoredValue=0.;\n"
            "                    if(CatalogData->TryGetNumberField(Key,CatalogValue)&&\n"
            "                        (!ItemData->TryGetNumberField(Key,StoredValue)||StoredValue!=CatalogValue))\n"
            "                    {ItemData->SetNumberField(Key,CatalogValue);TuningChanged=true;}\n"
            "                }\n"
            "                if(TuningChanged){I.Data.Reset();FJsonSerializer::Serialize(ItemData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;}\n"
            "            }",
            "            // Zhenyue's base reach is catalog tuning, not an instance upgrade.\n"
            "            // Assign the current value so loading repeatedly never compounds it.\n"
            "            if(I.Definition==TEXT(\"ue_xuanchi_zhenyue\")&&CatalogData&&\n"
            "                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),ItemData)&&ItemData)\n"
            "            {\n"
            "                double CatalogReach=0.,StoredReach=0.;\n"
            "                if(CatalogData->TryGetNumberField(TEXT(\"melee_reach_cm\"),CatalogReach)&&\n"
            "                    (!ItemData->TryGetNumberField(TEXT(\"melee_reach_cm\"),StoredReach)||StoredReach!=CatalogReach))\n"
            "                {\n"
            "                    ItemData->SetNumberField(TEXT(\"melee_reach_cm\"),CatalogReach);\n"
            "                    I.Data.Reset();FJsonSerializer::Serialize(ItemData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;\n"
            "                }\n"
            "            }\n"
            "            // Zhanmadao balance tuning also applies to already owned weapons.\n"
            "            // Only replace the base clock; installed parts and enhancement data\n"
            "            // remain instance state and still contribute their speed modifiers.\n"
            "            if(I.Definition==TEXT(\"ue_zhanmadao\")&&CatalogData&&\n"
            "                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),ItemData)&&ItemData)\n"
            "            {\n"
            "                double CatalogSeconds=0.,StoredSeconds=0.;\n"
            "                if(CatalogData->TryGetNumberField(TEXT(\"attack_seconds\"),CatalogSeconds)&&\n"
            "                    (!ItemData->TryGetNumberField(TEXT(\"attack_seconds\"),StoredSeconds)||StoredSeconds!=CatalogSeconds))\n"
            "                {\n"
            "                    ItemData->SetNumberField(TEXT(\"attack_seconds\"),CatalogSeconds);\n"
            "                    I.Data.Reset();FJsonSerializer::Serialize(ItemData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;\n"
            "                }\n"
            "            }",
        ),
    ],
    # R10 (2026-10-26): the knife hand drops out in 0.30 s (book keeps 0.55 s); client and server price the same time.
    'Source/FPSGAME/Weapons/OffhandReloadHandoff.h': [
        (
            "    static constexpr float RaiseSeconds=.40f;\n"
            "    // A knife hand just drops out of view (OffhandKukriComponent's lowering arc); a book is tucked away.\n"
            "    static constexpr float BladeLowerSeconds=.30f;\n"
            "    static constexpr float BodyReturnTransferFraction=.35f;\n"
            "    static constexpr float BodyLowerTransferStart=.76f;\n"
            "    static bool IsBladeOffhand(const FString& Definition) {return Definition==TEXT(\"ue_kukri\");}\n"
            "    static float LowerSecondsFor(const FString& Definition) {return IsBladeOffhand(Definition)?BladeLowerSeconds:LowerSeconds;}\n",
            "    static constexpr float RaiseSeconds=.40f;\n"
            "    static constexpr float BodyReturnTransferFraction=.35f;\n"
            "    static constexpr float BodyLowerTransferStart=.76f;\n",
        ),
        (
            "    double StartedAt=0.0;\n    float LowerDuration=LowerSeconds;\n",
            "    double StartedAt=0.0;\n",
        ),
        (
            "        if(Phase==EOffhandReloadPhase::Lower)return 1.f/LowerDuration;",
            "        if(Phase==EOffhandReloadPhase::Lower)return 1.f/LowerSeconds;",
        ),
        (
            "        if(Phase==EOffhandReloadPhase::Lower)return Ease(float(Now-StartedAt)/LowerDuration);",
            "        if(Phase==EOffhandReloadPhase::Lower)return Ease(float(Now-StartedAt)/LowerSeconds);",
        ),
    ],
    'Source/FPSGAME/FPSGAMECharacterOffhandReload.cpp': [
        (
            "        ?Native+FOffhandReloadHandoff::LowerSecondsFor(Off->Definition)+FOffhandReloadHandoff::RaiseSeconds:Native;",
            "        ?Native+FOffhandReloadHandoff::LowerSeconds+FOffhandReloadHandoff::RaiseSeconds:Native;",
        ),
        (
            "    OffhandReload.StartedAt=GetWorld()->GetTimeSeconds();\n"
            "    OffhandReload.LowerDuration=FOffhandReloadHandoff::LowerSecondsFor(Off->Definition);\n",
            "    OffhandReload.StartedAt=GetWorld()->GetTimeSeconds();\n",
        ),
        (
            "    if(OffhandReload.Phase==EOffhandReloadPhase::Lower&&Now-OffhandReload.StartedAt>=OffhandReload.LowerDuration)",
            "    if(OffhandReload.Phase==EOffhandReloadPhase::Lower&&Now-OffhandReload.StartedAt>=FOffhandReloadHandoff::LowerSeconds)",
        ),
    ],
    'Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp': [
        # R11 (2026-10-26): the kukri uppercut's stride recovery follows its own (faster) clock.
        (
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n#include "../Weapons/Kukri/KukriRhythm.h"\n',
            '#include "../Weapons/Kukri/KukriWeaponComponent.h"\n',
        ),
        (
            "        // The kukri (main hand or off hand) ends its faster uppercut on its own clock; holding the sword's longer\n"
            "        // recovery would refuse the next stride (e.g. a sprint attack) that the client is already allowed to start.\n"
            "        Recovery=R.Kind==EFPSMeleeMove::Uppercut?(KukriUppercut?\n"
            "            KukriRhythm::UpperRealSeconds(KukriRhythm::UpperLungeStart,KukriRhythm::Swings[KukriRhythm::UppercutStage].Length):\n"
            "            RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart)/ActionRate:\n",
            "        Recovery=R.Kind==EFPSMeleeMove::Uppercut?\n"
            "            (RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart)/ActionRate:\n",
        ),
        (
            "    const auto* Item=Tool?Tool:Profile?Profile->Equipped():nullptr;\n"
            "    // Pistol + off-hand kukri (OffhandKukriUppercut.cpp): the uppercut stride resolves the\n"
            "    // melee in the paired slot, so KukriUppercut below fires for the pair.\n"
            "    if(Item&&!Tool&&!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsOneHandedMelee(*Item)\n"
            "        &&ColdSteelInventory::IsDualPistol(*Item))\n"
            "        if(const auto* Off=Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11);\n"
            "            Off&&ColdSteelInventory::IsOneHandedMelee(*Off))Item=Off;",
            "    const auto* Item=Tool?Tool:Profile?Profile->Equipped():nullptr;",
        ),
    ],
}

# Earlier rounds of THIS batch's edits, reverted on top of the R3 reversion to
# reach the published preimage. Only needed for the three hosts that already
# have a bundle patch; sha256-verified against the recorded preimage.
R2REVERTS = {
    'Source/FPSGAME/FPSGAMECharacter.cpp': [
        (
            '#include "Weapons/Kukri/KukriWeaponComponent.h"\n#include "Weapons/Kukri/OffhandKukriComponent.h"\n#include "Weapons/Kukri/OffhandKukriAuthoredPose.h"',
            '#include "Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            '    CreateDefaultSubobject<UKukriWeaponComponent>(TEXT("Kukri"));\n'
            '    // 副手尼泊尔弯刀（主手手枪双持）：同样按组件类查找。\n'
            '    CreateDefaultSubobject<UOffhandKukriComponent>(TEXT("OffhandKukri"));',
            '    CreateDefaultSubobject<UKukriWeaponComponent>(TEXT("Kukri"));',
        ),
        (
            "    if(QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand())return;\n"
            "    // 副手弯刀出刀进行中同样不接开火（枪随动作走位，结束才恢复）。\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return;\n"
            "    if(IsCastBlockingLeftHandAction())",
            "    if(QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand())return;\n"
            "    if(IsCastBlockingLeftHandAction())",
        ),
        (
            "    if(Spellbook)Spellbook->AdvanceActionBeforeCamera(DeltaSeconds);\n"
            "    if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->AdvanceActionBeforeCamera(DeltaSeconds);",
            "    if(Spellbook)Spellbook->AdvanceActionBeforeCamera(DeltaSeconds);",
        ),
        (
            "    if(const auto* Kukri=FindComponentByClass<UKukriWeaponComponent>())Kukri->GetCameraMotion(KukriCameraLocation,KukriCameraRotation,KukriFOV);\n"
            "    // 副手弯刀出刀：参考视频配准的镜头曲线 + 命中抖动/出刀冲量，与弯刀主武器同一叠加口径。\n"
            "    FVector OffhandKukriLocation=FVector::ZeroVector;FRotator OffhandKukriRotation=FRotator::ZeroRotator;float OffhandKukriFOV=0.f;\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->GetCameraMotion(OffhandKukriLocation,OffhandKukriRotation,OffhandKukriFOV);",
            "    if(const auto* Kukri=FindComponentByClass<UKukriWeaponComponent>())Kukri->GetCameraMotion(KukriCameraLocation,KukriCameraRotation,KukriFOV);",
        ),
        (
            "    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(KukriCameraLocation))*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();\n"
            "    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(OffhandKukriLocation))*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();",
            "    TargetLocation+=GetActorQuat().UnrotateVector(ControlAim.RotateVector(KukriCameraLocation))*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();",
        ),
        (
            "    CameraFeedback+=KukriCameraRotation*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();\n"
            "    CameraFeedback+=OffhandKukriRotation*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();",
            "    CameraFeedback+=KukriCameraRotation*CameraMotionScale*CameraShakeScale.GetValueOnGameThread();",
        ),
        (
            "        + (KukriFOV+OffhandKukriFOV)*CameraMotionScale*CameraShakeScale.GetValueOnGameThread());",
            "        + KukriFOV*CameraMotionScale*CameraShakeScale.GetValueOnGameThread());",
        ),
        (
            "    if(bPistol)if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsEquipped())\n"
            "    {\n"
            "        // Knife-and-gun hip hold: the whole pistol is centred and canted. The cant\n"
            "        // unwinds within the first part of ADS so the native sight line is exact.\n"
            "        // During the quick-melee flourish the authored per-key framing replaces the stance pose.\n"
            "        FTransform Strike;\n"
            "        const bool Striking=OffhandKukri->GetStrikeFraming(Strike);\n"
            "        const FTransform& FramingPose=Striking?Strike:OffhandKukriPose::HipFraming;\n"
            "        const float Framing=Striking?1.f:\n"
            "            OffhandKukri->PistolFramingWeight()*(1.f-FMath::SmoothStep(0.f,OffhandKukriPose::CantUnwindAim,WeaponADSFactor));\n"
            "        if(Framing>UE_SMALL_NUMBER)\n"
            "        {\n"
            "            const FQuat Cant=FQuat::Slerp(FQuat::Identity,FramingPose.GetRotation(),Framing);\n"
            "            TargetLocation=Cant.RotateVector(TargetLocation)+FramingPose.GetLocation()*Framing;\n"
            "            TargetRotation=Cant*TargetRotation;\n"
            "        }\n"
            "    }\n",
            "",
        ),
        (
            "    const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return true;",
            "    const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();",
        ),
        (
            "bool AFPSGAMECharacter::IsLeftHandHeldForCast() const { return HasOffhandPistol()||HasOffhandSpellbook()||IsLoneOffhandPistol()||UOffhandKukriComponent::IsEquippedOn(this); }",
            "bool AFPSGAMECharacter::IsLeftHandHeldForCast() const { return HasOffhandPistol()||HasOffhandSpellbook()||IsLoneOffhandPistol(); }",
        ),
        (
            "    if(QuickCombatPistol)QuickCombatPistol->Cancel();\n"
            "    if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->CancelQuickCombat();\n"
            "    FireReleased();",
            "    if(QuickCombatPistol)QuickCombatPistol->Cancel();\n"
            "    FireReleased();",
        ),
        (
            "    if(const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();Bash&&Bash->IsOccupyingLeftHand())return true;\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return true;",
            "    if(const auto* Bash=FindComponentByClass<UFPSQuickCombatComponent>();Bash&&Bash->IsOccupyingLeftHand())return true;",
        ),
        (
            "    const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();\n"
            "    return IsDoorPushActive() || IsTraversing() || Traversal->IsWeaponRecovering() || (RuneSword && RuneSword->IsBusy()) ||\n"
            "        (Staff && Staff->IsEquipped() && Staff->IsBusy()) || bGunBusy ||\n"
            "        (QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand()) ||\n"
            "        (OffhandKukri && OffhandKukri->IsQuickCombatActive());",
            "    return IsDoorPushActive() || IsTraversing() || Traversal->IsWeaponRecovering() || (RuneSword && RuneSword->IsBusy()) ||\n"
            "        (Staff && Staff->IsEquipped() && Staff->IsBusy()) || bGunBusy ||\n"
            "        (QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand());",
        ),
    ],
    'Source/FPSGAME/FPSGAMECharacterActionPriority.cpp': [
        (
            '#include "Weapons/Kukri/KukriWeaponComponent.h"\n#include "Weapons/Kukri/OffhandKukriComponent.h"',
            '#include "Weapons/Kukri/KukriWeaponComponent.h"',
        ),
        (
            "    if(Kukri && Kukri->IsQuickCombatActive())return false;\n"
            "    if(const auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>();OffhandKukri&&OffhandKukri->IsQuickCombatActive())return false;",
            "    if(Kukri && Kukri->IsQuickCombatActive())return false;",
        ),
        (
            "        if(QuickCombatPistol)QuickCombatPistol->Cancel();\n"
            "        if(auto* OffhandKukri=FindComponentByClass<UOffhandKukriComponent>())OffhandKukri->CancelQuickCombat();",
            "        if(QuickCombatPistol)QuickCombatPistol->Cancel();",
        ),
    ],
    'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp': [
        (
            "    if (Report.AttackMeta & 0x80)\n"
            "    {\n"
            "        // 副手弯刀快速近战：申报武器是影子档案副手槽位的弯刀且主手是双持手枪时，\n"
            "        // 伤害 = 该副手武器物理面板（基础+附加）的 200%（客户端同式，OffhandKukriStrike.cpp）。\n"
            "        if(Item&&ShadowModel&&ColdSteelInventory::IsOneHandedMelee(*Item))\n"
            "        {\n"
            "            const auto Snap=ShadowModel->Snapshot();\n"
            "            const auto* Offhand=ShadowModel->Equipped(Snap.ActiveWeaponSlot==6?8:11);\n"
            "            const auto* Primary=ShadowModel->Equipped(Snap.ActiveWeaponSlot);\n"
            "            if(Offhand&&Offhand->InstanceId==Item->InstanceId&&Primary&&ColdSteelInventory::IsDualPistol(*Primary))\n"
            "            {\n"
            "                const auto Melee=ColdSteelMelee::Evaluate(*Item,ShadowModel);\n"
            "                return float(2.*(Melee.DamageParts.BasePhysical+Melee.DamageParts.AddedPhysical));\n"
            "            }\n"
            "        }\n"
            "        return ShadowModel ? ShadowModel->QuickCombatStats().Damage : Panel;\n"
            "    }",
            "    if (Report.AttackMeta & 0x80)\n"
            "        return ShadowModel ? ShadowModel->QuickCombatStats().Damage : Panel;",
        ),
    ],
}

# Hosts already in the bundle: rel -> (patch, preimage sha, result sha)
EXISTING = {
    'Source/FPSGAME/FPSGAMECharacter.cpp': (
        'Source__FPSGAME__FPSGAMECharacter.cpp.patch',
        'a8c55404510b1357cbdeb8b62ad6cee2b559106a9ef840465e71d7d334493b32',
        '33a2b606e54ad04563d608fd967c459378bb512489e8164acea1fb33fbcbd20d'),
    'Source/FPSGAME/FPSGAMECharacterActionPriority.cpp': (
        'Source__FPSGAME__FPSGAMECharacterActionPriority.cpp.patch',
        '6b4f68e75f888aa691a0fd886ac7b7e92036b82a8a3ab4d94ff1dfcde0766e7e',
        'ed3111f67c202d8cce20e3161959bab8bc1f7af8e86c8e05cd6df54fb2b5016e'),
    'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp': (
        'Source__FPSGAME__Multiplayer__ColdSteelPlayerState.cpp.patch',
        '57569f9cc9573c4756d96485a6609be13ce163953713a741ea3185fc7b8caf78',
        '7db450fe77be46b7978044067523e8276f3ed1ecce0d54d4f0c2b6ea67b1e90a'),
}


# Hosts patched by an earlier round whose edits are not listed above: the preimage is recovered by reverse-applying
# the published patch (LF-normalised) and checked against the recorded preimage hash.
PRIOR_PATCH = set()
# Hosts whose earlier patch no longer matches the tree (parallel sessions edited them since): this round ships as its
# own patch on top, preimage = the current file minus this round's edits (in-flight work included, as the bundle rule).
STANDALONE = {'Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp': 'r8'}


def reverse_published(rel, text):
    tmp = os.path.join(SCR, 'rev')
    save(os.path.join(tmp, rel), text)
    pf = os.path.join(SCR, 'rev.patch')
    save(pf, open(os.path.join(PKG, 'Integration', patch_name(rel)), encoding='utf-8', newline='').read()
         .replace('\r\n', '\n'))
    r = subprocess.run(['patch', '-R', '--no-backup-if-mismatch', '-p1', '-d', tmp, '-i', pf],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise SystemExit(f'{rel}: reverse-apply of the published patch failed: {r.stdout}{r.stderr}')
    return load_abs(os.path.join(tmp, rel))


def load_abs(path):
    with open(path, encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n').replace('\r', '\n')


def patch_name(rel):
    return rel.replace('/', '__') + '.patch'


def revert_pairs(text, pairs, rel):
    for new, old in pairs:
        if new not in text:
            raise SystemExit(f'{rel}: pattern not found: {new[:70]!r}')
        text = text.replace(new, old)
    return text


def to_crlf_patch(diff_text):
    out = []
    for line in diff_text.split('\n'):
        payload = line[:1] in (' ', '\\') or (
            line[:1] in ('+', '-') and not line.startswith(('+++ ', '--- ')))
        out.append(line + ('\r\n' if payload else '\n'))
    return ''.join(out)


def run_patch(patch_file, target_dir):
    r = subprocess.run(
        ['patch', '--no-backup-if-mismatch', '-p1', '-d', target_dir, '-i', patch_file],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise SystemExit(f'patch failed: {r.stdout}{r.stderr}')


def main():
    prereq_path = os.path.join(PKG, 'integration-prerequisites.json')
    prereq = json.load(open(prereq_path, encoding='utf-8'))
    report = []
    # Optional host filter: regenerate only the named hosts (others keep their published patch, e.g. when a
    # parallel session has since edited an untouched host).
    only = set(sys.argv[1:])
    for rel, pairs in REVERTS.items():
        if only and rel not in only:
            continue
        current = load(rel)
        pre = revert_pairs(current, pairs, rel)
        suffix = STANDALONE.get(rel)
        if suffix:
            pass
        elif rel in EXISTING:
            _, want_pre, want_res = EXISTING[rel]
            if sha_text(pre) != want_res:
                raise SystemExit(f'{rel}: R3-reverted hash {sha_text(pre)[:12]} != recorded result {want_res[:12]}')
            pre = revert_pairs(pre, R2REVERTS[rel], rel)
            if sha_text(pre) != want_pre:
                raise SystemExit(f'{rel}: preimage hash {sha_text(pre)[:12]} != recorded {want_pre[:12]}')
        elif rel in PRIOR_PATCH:
            want_pre = prereq[rel]['preimage_sha256_lf_utf8']
            want_res = prereq[rel]['result_sha256_lf_utf8']
            if sha_text(pre) != want_res:
                raise SystemExit(f'{rel}: reverted hash {sha_text(pre)[:12]} != recorded result {want_res[:12]}')
            pre = reverse_published(rel, pre)
            if sha_text(pre) != want_pre:
                raise SystemExit(f'{rel}: preimage hash {sha_text(pre)[:12]} != recorded {want_pre[:12]}')
        preimage = pre
        pre_path = os.path.join(SCR, 'pre', rel)
        cur_path = os.path.join(SCR, 'cur', rel)
        save(pre_path, preimage)
        save(cur_path, current)
        r = subprocess.run(['diff', '-u', '-L', f'a/{rel}', '-L', f'b/{rel}', pre_path, cur_path],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode not in (0, 1) or not r.stdout.strip():
            raise SystemExit(f'diff failed for {rel}: {r.stderr}')
        patch_text = to_crlf_patch(f'diff --git a/{rel} b/{rel}\n' + r.stdout)
        pname = patch_name(rel).replace('.patch', f'.{suffix}.patch') if suffix else patch_name(rel)
        out = os.path.join(PKG, 'Integration', pname)
        save(out, patch_text)
        rt = os.path.join(SCR, 'rt')
        save(os.path.join(rt, rel), preimage)
        rt_patch = os.path.join(SCR, 'rt.patch')
        save(rt_patch, patch_text.replace('\r\n', '\n'))
        run_patch(rt_patch, rt)
        got = sha_path(os.path.join(rt, rel))
        want = sha_text(current)
        if got != want:
            raise SystemExit(f'{rel}: round-trip mismatch {got[:12]} != {want[:12]}')
        entry = {
            'patch': f'Integration/{pname}',
            'preimage_sha256_lf_utf8': sha_text(preimage),
            'result_sha256_lf_utf8': want,
            'runtime_tree_applied': True,
        }
        if suffix:
            entry['apply_after'] = f'Integration/{patch_name(rel)}'
            entry['note'] = 'preimage includes parallel sessions\' in-flight edits made after the earlier patch; merge semantically if hashes differ'
        prereq[f'{rel}#{suffix}' if suffix else rel] = entry
        report.append((rel, patch_text.count('@@') // 2))
    save(prereq_path, json.dumps(prereq, indent=2, ensure_ascii=False) + '\n')
    for rel, hunks in report:
        print(f'{hunks:3d} hunks  {rel}')
    print('OK')


if __name__ == '__main__':
    main()
