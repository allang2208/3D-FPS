from pathlib import Path
R=Path("D:/FPS3D/FPSGAME/Source/FPSGAME")
def edit(rel,fn):
 p=R/rel;s=p.read_text(encoding="utf8");n=fn(s)
 p.write_text(n,encoding="utf8",newline="")
def include(s):
 return s.replace('#include "M10Mawcrawler.h"','#include "M10Mawcrawler.h"\n#include "HangingBellM09.h"',1)
def combat(s):
 s=include(s)
 clones=[
 ('if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner())){Health=M10->Health;MaxHealth=M10->MaxHealth;Name=FText::FromString(TEXT("沉匣 M-10"));return true;}','if(const auto* M09=Cast<AHangingBellM09>(GetOwner())){Health=M09->Health;MaxHealth=M09->MaxHealth;Name=FText::FromString(TEXT("悬钟 M-09"));return true;}'),
 ('if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->State==EM10State::Stagger;','if(const auto* M09=Cast<AHangingBellM09>(GetOwner()))return M09->State==EM09State::Stagger;'),
 ('if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->BiteTriggerRange-15.f;','if(auto* M09=Cast<AHangingBellM09>(GetOwner()))return 180.f;')
 ]
 for old,new in clones:
  if old not in s:raise RuntimeError("Missing combat context "+old)
  s=s.replace(old,new+"\n "+old,1)
 for old in [
 'if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Dead();',
 'if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Busy();',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->SetTarget(P);',
 'if(const auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->CanAttack(P);',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->StartAttack(P);',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner())){M10->SetLocomotion(Moving,Returning);return;}',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->AggroRadius;',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->LeashRadius;',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))return M10->Home;',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->Health=M10->MaxHealth;',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(FMath::Max(Remaining,Duration));',
 'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->FinishHitReaction();']:
  if old not in s:raise RuntimeError("Missing combat context "+old)
  s=s.replace(old,old.replace("M10","M09").replace("AM09Mawcrawler","AHangingBellM09")+"\n "+old,1)
 for old in ['if(auto* M10=Cast<AM10Mawcrawler>(C))M10->StartHitPresentation();',
             'if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->SetHitPresentationTime(Elapsed,Remaining);']:
  s=s.replace(old,old.replace("M10","M09").replace("AM09Mawcrawler","AHangingBellM09")+"\n else "+old)
 return s
edit("Monsters/MonsterCombatComponent.cpp",combat)
def knock(s):
 s=include(s);old='if(auto* M10=Cast<AM10Mawcrawler>(GetOwner()))M10->InterruptAttack(Seconds);'
 s=s.replace(old,'if(auto* M09=Cast<AHangingBellM09>(GetOwner()))M09->InterruptAttack(Seconds);\n    else '+old)
 s=s.replace('bool Launched=false;','if(auto* M09=Cast<AHangingBellM09>(GetOwner())){M09->InterruptAttack(FMath::Max(.7f,DownSeconds));return true;}\n    bool Launched=false;')
 return s
edit("Monsters/MonsterMeleeKnockback.cpp",knock)
def parry(s):
 s=knock(s);return s.replace('if(KnockbackCM>0.f)','if(KnockbackCM>0.f&&!GetOwner()->ActorHasTag(TEXT("KnockbackImmune")))')
edit("Monsters/MonsterParryReaction.cpp",parry)
edit("Monsters/MonsterCoreStats.cpp",lambda s:include(s).replace('if(const auto* M10=Cast<AM10Mawcrawler>(Target))',
 'if(const auto* M09=Cast<AHangingBellM09>(Target))Fill(M09->PhysicalDefense,M09->MagicalDefense,22,9.0,M09->Level,M09->Rank,EMonsterToughnessClass::Caster);\n    else if(const auto* M10=Cast<AM10Mawcrawler>(Target))',1))
edit("Monsters/MonsterCorpseRagdollComponent.h",lambda s:s.replace('FleshHand, Mawcrawler };','FleshHand, Mawcrawler, HangingBell };'))
edit("Monsters/MonsterCorpseRagdollComponent.cpp",lambda s:s.replace('if (Rig == EMonsterCorpseRig::Maggot && Mesh->GetBodyInstance',
 'if (Rig == EMonsterCorpseRig::HangingBell && Mesh->GetBodyInstance(TEXT("spine_01"))) return TEXT("spine_01");\n    if (Rig == EMonsterCorpseRig::Maggot && Mesh->GetBodyInstance',1).replace('Rig == EMonsterCorpseRig::Mawcrawler) &&','Rig == EMonsterCorpseRig::Mawcrawler || Rig == EMonsterCorpseRig::HangingBell) &&'))
def bt(s):
 s=include(s)
 old='AI->ActiveAction=NodeName;'
 s=s.replace(old,old+'\n if(Action==EMonsterAction::Hold||Action==EMonsterAction::Idle)if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();',1)
 old='const FVector Feet=AI->GetPawn()->GetNavAgentLocation();'
 s=s.replace(old,'if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))\n  {\n   M09->NavigateCeiling(Dest,Returning);\n   if(Elapsed>=.25f)FinishLatentTask(Owner,EBTNodeResult::Succeeded);\n   return;\n  }\n  '+old,1)
 s=s.replace('if(auto* AI=Owner.GetAIOwner())AI->StopMovement();return EBTNodeResult::Aborted;',
 'if(auto* AI=Owner.GetAIOwner()){AI->StopMovement();if(auto* M09=Cast<AHangingBellM09>(AI->GetPawn()))M09->StopCeiling();}return EBTNodeResult::Aborted;')
 return s
edit("Monsters/MonsterBTNodes.cpp",bt)
def ai(s):
 s=s.replace('#include "BlindSupplicantMonster.h"','#include "BlindSupplicantMonster.h"\n#include "HangingBellM09.h"',1)
 s=s.replace('const auto* M07=Cast<ABlindSupplicantMonster>(GetPawn());',
 'const auto* M07=Cast<ABlindSupplicantMonster>(GetPawn());\n const auto* M09=Cast<AHangingBellM09>(GetPawn());',1)
 s=s.replace('(M07?M07->HasMagicSight(KnownTarget.Get()):LineOfSightTo(KnownTarget.Get()))',
 '(M09?M09->HasAttackSight(KnownTarget.Get()):M07?M07->HasMagicSight(KnownTarget.Get()):LineOfSightTo(KnownTarget.Get()))',1)
 # Ceiling routes use their own path and return handling; the target remains remembered by the same service.
 return s
edit("Monsters/MonsterAIController.cpp",ai)
def f6(s):
 s=s.replace('#include "DevelopmentSpawnComponent.h"','#include "DevelopmentSpawnComponent.h"\n#include "../Monsters/HangingBellM09.h"\n#include "../Monsters/M09CeilingRoute.h"',1)
 anchor='    Add(TEXT("M10Mawcrawler"),'
 at=s.index(anchor)
 s=s[:at]+'    Add(TEXT("HangingBellM09"), TEXT("悬钟 M-09（天花板）"), TEXT("/Script/FPSGAME.HangingBellM09"), 90.f);\n'+s[at:]
 anchor='    const auto* Defaults = Class->GetDefaultObject<ACharacter>();'
 pos=s.index(anchor)
 branch='''    if(Class->IsChildOf(AHangingBellM09::StaticClass()))
    {
        const auto* M09=Class->GetDefaultObject<AHangingBellM09>();
        if(!M09->VisualMesh){Result=FText::FromString(TEXT("悬钟模型资源尚未准备好"));return 0;}
        FVector View;FRotator Look;Player->GetPlayerViewPoint(View,Look);
        const FVector Forward=FRotator(0,Look.Yaw,0).Vector(),Right=FVector::CrossProduct(FVector::UpVector,Forward);
        const FVector Feet=Player->GetPawn()->GetNavAgentLocation();
        const int32 Wanted=FMath::Clamp(Count,1,10);int32 Created=0;Spawned.RemoveAll([](const auto& Item){return !Item.IsValid();});
        for(int32 I=0;I<25&&Created<Wanted;++I)
        {
            const int32 Column=I%5,Side=Column==0?0:(Column%2?(Column+1)/2:-Column/2);
            const FVector Near=Feet+Forward*(FMath::Clamp(DistanceMeters,3.f,15.f)*100.f+(I/5)*180.f)+Right*Side*210.f;
            FVector Ceiling;auto* Route=AM09CeilingRoute::FindPlacement(GetWorld(),Near,Player->GetPawn(),Ceiling);
            if(!Route)continue;
            FActorSpawnParameters Params;Params.Owner=Player;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
            const FVector Position=Ceiling-FVector(0,0,143);
            if(auto* Monster=GetWorld()->SpawnActor<AHangingBellM09>(Class,Position,FRotator(0,(Feet-Position).Rotation().Yaw,0),Params))
            {
                Monster->InitializeHang(Route);Monster->Tags.AddUnique(TEXT("DevelopmentSpawned"));Spawned.Add(Monster);++Created;
            }
        }
        Result=FText::FromString(Created?FString::Printf(TEXT("已在天花板生成 %d / %d 只悬钟"),Created,Wanted):
            TEXT("附近没有可悬挂的天花板或身体净空不足；请进入悬钟测试房并面向有顶区域"));
        return Created;
    }
'''
 return s[:pos]+branch+s[pos:]
edit("Development/DevelopmentSpawnComponent.cpp",f6)
# Fix the M09's own implementation before compiling.
edit("Monsters/HangingBellM09.cpp",lambda s:s.replace('Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("HangingBellM09"));','Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("HangingBellM09"));Tags.Add(TEXT("KnockbackImmune"));')
 .replace('const int32 E=Ref.FindBoneIndex(TEXT("eye_01")),C=Ref.FindBoneIndex(TEXT("eye_crown"));',
 'const int32 E=Ref.FindBoneIndex(TEXT("eye_04")),F=Ref.FindBoneIndex(TEXT("eye_05")),C=Ref.FindBoneIndex(TEXT("eye_crown"));')
 .replace('if(E>=0&&C>=0)Yaw=-(Frames[E].GetLocation()-Frames[C].GetLocation()).Rotation().Yaw;',
 'if(E>=0&&F>=0&&C>=0)Yaw=-((Frames[E].GetLocation()+Frames[F].GetLocation())*.5-Frames[C].GetLocation()).Rotation().Yaw;')
 .replace('bUseControllerRotationYaw=false;AIControllerClass=AMonsterAIController::StaticClass();',
 'bUseControllerRotationYaw=false;static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));AIControllerClass=AI.Class?AI.Class:AMonsterAIController::StaticClass();'))
print("M09 shared gameplay adapters written")
