#include "HillsContinuityAudit.h"
#include "HillsContinuitySupport.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "../WorldGeneration/HillsNightPortal.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../FPSWeatherManager.h"
#include "Components/CapsuleComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Net/UnrealNetwork.h"
#include "Dom/JsonObject.h"

AHillsContinuityAudit::AHillsContinuityAudit()
{bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.03f;}
void AHillsContinuityAudit::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AHillsContinuityAudit,Phase);DOREPLIFETIME(AHillsContinuityAudit,Target);DOREPLIFETIME(AHillsContinuityAudit,Point);DOREPLIFETIME(AHillsContinuityAudit,Expected);}
void AHillsContinuityAudit::Tick(float Delta)
{Super::Tick(Delta);if(!HillsContinuity::Enabled())return;if(Director&&HasAuthority())RunHost();else if(!HasAuthority())RunClient();}
void AHillsContinuityAudit::ServerReport_Implementation(int32 Step,bool Pass,const FString& Text)
{if(HillsContinuity::Enabled()&&Step==Phase){Reported=Step;Passed=Pass;Detail=Text;}}
void AHillsContinuityAudit::ClientExit_Implementation()
{if(HillsContinuity::Enabled())FPlatformMisc::RequestExit(false);}
void AHillsContinuityAudit::RunClient()
{
    using namespace HillsContinuity;
    auto* PC=Cast<APlayerController>(GetOwner());auto* P=Character(PC);if(!P||Phase<=0)return;
    if(Previous!=Phase){Previous=Phase;Began=FPlatformTime::Seconds();Requested=SawEnter=SawExit=GroundFloor=Jumped=WalkStarted=false;Reported=0;StartPosition=P->GetActorLocation();}
    if(Reported==Phase)return;const double Age=FPlatformTime::Seconds()-Began;if(Age<2.)return;
    bool OK=false;FString Text;
    auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* Rest=P->FindComponentByClass<UFPSFurnitureRestComponent>();
    const auto S=RestState(P);
    if(Phase==1)
    {
        if(Body&&!Requested&&Body->CanUseBodyType(TEXT("kaitlin")))Requested=Body->SetBodyType(TEXT("kaitlin"));
        OK=Body&&Body->GetBodyType()==TEXT("kaitlin")&&BodyReady(P,&Text);
    }
    else if(Phase==2)
    {
        auto* Move=P->GetCharacterMovement();
        if(!WalkStarted){WalkStarted=true;StartPosition=P->GetActorLocation();}
        GroundFloor|=Move->CurrentFloor.bWalkableFloor&&Move->CurrentFloor.HitResult.GetComponent()
            &&Move->CurrentFloor.HitResult.GetComponent()->ComponentHasTag(TEXT("HillsGround"))&&!P->GetMovementBase();
        if(Age<6.)P->AddMovementInput(Point.GetSafeNormal2D());
        if(Age>3.&&!Requested){P->Jump();Requested=true;}
        Jumped|=Move->IsFalling();if(Age>3.4)P->StopJumping();
        if(Age<8.)return;
        const double Distance=FVector::Dist2D(P->GetActorLocation(),StartPosition);
        OK=GroundFloor&&Jumped&&Move->IsMovingOnGround()&&Distance>120.&&Distance<3500.;
        Text=FString::Printf(TEXT("walk=%.1f generated_floor=%d no_base=%d jumped=%d mode=%d"),FVector::Dist2D(P->GetActorLocation(),StartPosition),GroundFloor,!P->GetMovementBase(),Jumped,int32(Move->MovementMode));
    }
    else if(Phase==3||Phase==5)
    {
        const bool Aimed=!Requested&&Aim(PC,Point);SawEnter|=S.Phase==1||S.Phase==2;
        if(Age<5.)return; // Let the owning view reach the authority before pressing E.
        // Wait until the neighboring player finishes turning through the aisle.
        // A moving body in the approach sweep is a valid physical rejection.
        const bool AisleReady=Phase!=3||(Target&&RestState(Target).Phase==3);
        if(!Requested&&AisleReady&&Aimed&&BodyReady(P)&&Rest&&Rest->UpdateFocus(true).Contains(TEXT("坐下"))){KeyE(PC);Requested=true;}
        OK=Seated(P,Text)&&SawEnter;
        Text=FString::Printf(TEXT("E=%d entered=%d "),Requested,SawEnter)+Text;
        if(!OK&&Age>39.&&Rest)Text+=TEXT(" focus=")+Rest->UpdateFocus(true)+TEXT(" ")+InteractionTrace(PC,Point);
    }
    else if(Phase==4)
    {OK=Seated(Target,Text)&&S.Phase==0;Text=TEXT("late join host idle; own slot released; ")+Text;}
    else if(Phase==6)
    {
        if(!Requested){KeyE(PC);Requested=true;}
        SawExit|=S.Phase==4;
        OK=SawExit&&S.Phase==0&&P->GetCharacterMovement()->IsMovingOnGround()&&!PC->IsMoveInputIgnored();
        Text=FString::Printf(TEXT("E=%d exit_seen=%d phase=%d movement=%d input_ignored=%d"),Requested,SawExit,S.Phase,int32(P->GetCharacterMovement()->MovementMode),PC->IsMoveInputIgnored());
    }
    else if(Phase==7)
    {
        auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();OK=Health&&Health->Health<=Expected+.1f;
        Text=FString::Printf(TEXT("native AI damage replicated health=%.2f authority_after_hit=%.2f"),Health?Health->Health:-1.,Expected);
    }
    else if(Phase==8||Phase==9||Phase==10)
    {
        AChapelShrine* ShrineActor=nullptr;AFPSWeatherManager* Clock=nullptr;AHillsNightPortal* Portal=nullptr;
        for(TActorIterator<AChapelShrine> It(GetWorld());It;++It){ShrineActor=*It;break;}
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){Clock=*It;break;}
        for(TActorIterator<AHillsNightPortal> It(GetWorld());It;++It)if(It->ClosedAt<0){Portal=*It;break;}
        const bool Dawn=Phase==10;
        OK=ShrineActor&&Clock&&Clock->IsWeatherStateReady()&&(Dawn?(!ShrineActor->bRaidNight&&!ShrineActor->IsDormant()&&!Portal):(ShrineActor->IsDormant()&&ShrineActor->bRaidNight&&Portal));
        if(Phase==9)OK&=FMath::Abs(Clock->NormalizedDayTime*24.-Expected)<.2;
        Text=FString::Printf(TEXT("ward=%.1f night=%d portal=%d hour=%.4f"),ShrineActor?ShrineActor->Durability:-1.,ShrineActor&&ShrineActor->bRaidNight,Portal!=nullptr,Clock?Clock->NormalizedDayTime*24.:-1.);
    }
    const double Limit=Phase==1?180.:Phase==7?120.:40.;
    if(!OK&&Age<Limit)return;
    Reported=Phase;auto Json=MakeShared<FJsonObject>();Json->SetBoolField(TEXT("passed"),OK);Json->SetStringField(TEXT("detail"),Text);
    Save(FString::Printf(TEXT("%s-client-%02d"),HillsContinuity::Restart()?TEXT("restart"):TEXT("initial"),Phase),Json);ServerReport(Phase,OK,Text);
}
