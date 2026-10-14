#include "ColdSteelAuthorityContext.h"
#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
namespace { thread_local UColdSteelStatusModel* ActingModel=nullptr; }
ColdSteelAuthority::FScope::FScope(UColdSteelStatusModel* M):Previous(ActingModel){ActingModel=M;}
ColdSteelAuthority::FScope::~FScope(){ActingModel=Previous;}
UColdSteelStatusModel* ColdSteelAuthority::Model(const UObject* Context)
{
    if(ActingModel)return ActingModel;
    const auto* W=Context?Context->GetWorld():nullptr;
    return W&&W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
UColdSteelStatusModel* ColdSteelAuthority::ForPawn(const APawn* Pawn)
{
    if(!Pawn)return nullptr;
    if(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
        if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())return PS->GetShadowModel();
    if(!Pawn->IsLocallyControlled())return nullptr;
    const auto* GI=Pawn->GetGameInstance();return GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
}
