"""Source/data contracts only; does not execute UE, gameplay or network tests."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parents[2]
OUT = P / "SourceAssets/PlantingMultiplayer20261022"
OUT.mkdir(parents=True, exist_ok=True)
def read(path):
    return (P / path).read_text(encoding="utf-8-sig")
checks = []
def check(name, passed):
    checks.append({"name": name, "passed": bool(passed)})

core = read("Source/FPSGAME/Building/ColdSteelPlantingSystem.cpp")
net = read("Source/FPSGAME/Building/ColdSteelPlantingNetwork.cpp")
authority = read("Source/FPSGAME/Multiplayer/ColdSteelPlantingAuthority.cpp")
shared = read("Source/FPSGAME/Multiplayer/ColdSteelSharedInventorySubsystem.h")
requests = read("Source/FPSGAME/Multiplayer/ColdSteelInventoryRequests.cpp")
types = read("Source/FPSGAME/Multiplayer/ColdSteelInventoryRequestTypes.h")
stream = read("Source/FPSGAME/Multiplayer/ColdSteelWorldNetwork.cpp")
ui = read("Source/FPSGAME/UI/ColdSteelPlantingWorkbench.cpp")
ps = read("Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp")
check("planting intent registered in existing inventory channel", "Shop,\n    Planting" in types and "Shared->PlantingAction" in requests)
check("intent carries real bed and expected plant identities", "FGuid PlantingBedId" in types and "FGuid ExpectedPlantId" in types)
check("existing sequence revision pawn and health guards retained", all(x in requests for x in ["LastInventoryRequestSequence", "Request.Revision!=Before.CampfireInventoryRevision", "Request.Pawn!=Pawn", "Health->IsDead()"]))
check("authority authenticates current pawn and guest shadow", all(x in authority for x in ["Request.Pawn!=Pawn", "Guest->GetShadowModel()!=Model", "Guest->CampfireGuestSlot().IsEmpty()", "!PC->IsLocalController()", "Pawn->HasAuthority()", "Request.Action!=EColdSteelInventoryAction::Planting"]))
check("authority validates actual world bed identity and visibility", all(x in net for x in ["World->IsReady()", "Piece!=Request.Target", "World->PrefabInstanceIdentity(Request.Anchor)!=Request.PlantingBedId", "PC->LineOfSightTo(Piece)"]))
check("distance measured from authority pawn not request vectors", "Operator->RuntimePawn()" in core and "FMath::Square(350.f)" in core and "Request.Eye" not in net and "Request.Origin" not in net)
check("maturity and yield taken from server plant or rule", "Existing->Stage(NowTicks(World))" in core and "Existing->OutputCount" in core and "Rule->GrowthSeconds" in core and "Request.Count" not in authority)
check("new requests cannot reuse occupied or harvested plant", "Existing->PlantId!=Request.ExpectedPlantId" in net and "Existing!=nullptr" in net)
check("authority requests rate limited", "Now-*Last<.15" in authority)
check("planting rejects unacknowledged owner inventory instead of uploading it with the request", "Request.Action==EColdSteelInventoryAction::Planting&&(Baseline.IsEmpty()||Baseline!=AcknowledgedInventoryBaseline)" in requests)
check("full backpack validated on proposal before committing", "ColdSteelInventory::Insert(Proposed.Items,Product)" in core and "auto Profile=Model->Snapshot();auto After=Current;" in authority)
check("shared planting uses existing two-file inventory receipt transaction", "return Commit(Model,Guest,MoveTemp(Profile),MoveTemp(After),Reason);" in authority and "After.PlantingCrops" in authority)
check("bed anchor durable before paid mutation", "World->FlushCampfirePersistence()" in authority)
check("world planting saved alongside existing shared data", "UPROPERTY() TArray<FColdSteelCropPlant> PlantingCrops;" in shared and "UPROPERTY() int64 PlantingRevision=0;" in shared)
check("world-only seeding and cleanup reuse full redo recovery envelope", "UColdSteelSharedFoodJournal" in authority and "CommitPlantingWorld" in authority and "bBlocked=true" in authority)
check("only host solo data seed once never guest uploaded data", "NM_ListenServer" in authority and "PlantingSeededWorlds.Contains(Key)" in authority and "Host->PlantingCrops()" in authority)
check("single-player profile path retained", "World->GetNetMode()==NM_Standalone" in net and "M->CommitState(MoveTemp(Proposed))" in core)
check("public mirror stays outside client profile", "Mirror=State" in net and "Mirror.WorldKey==World->BuildingWorldKey()" in net and "AdoptNetMirror" not in net and "CommitState" not in net)
check("late join uses existing world chunk stream", "State->Planting=Planting->NetworkState(*It)" in stream and "PendingWorldState->Planting" in stream and "ClientWorldChunk" in stream)
check("owner result returns world state and reason immediately", "Reply->Planting=Planting->NetworkState(World)" in requests and "NetworkFinished(PendingInventoryRequest" in requests)
check("older bulk snapshots cannot rewind a newer receipt", "State.Revision<Mirror.Revision" in net)
check("oversized receipt fallback drops bulk planting view and retains result delivery", "Reply->Planting={};Reply->bPlantingView=false;" in requests)
check("growth clock uses owner-only server UTC and monotonic elapsed", "PlantingUtcTicks,COND_OwnerOnly" in ps and "ObserveServerClock" in stream and "ObservedUtcTicks+int64" in net and "FPlatformTime::Seconds()-ObservedUtcAt" in net)
check("client missing/replaced actors retry without deleting or attaching old crops to a new bed", "if(Client)Unresolved=true;else Orphans.Add" in core and "bVisualDirty=Unresolved" in core and "if(!Piece||World->PrefabInstanceIdentity(Plant.BedCell)!=Plant.BedId||!Rule)continue;" in core)
check("variant yaw scale created only at planting not in network request", core.count("FRandomStream Random(")==1 and "Plant.YawDegrees=Random.FRandRange" in core and "Random" not in net)
check("same shared workbench controls network pending and feedback", "System->Pending()" in ui and "System->StateSerial()" in ui and "System->NetworkNotice()" in ui and "ColdSteelUI::ButtonStyle" in ui)
check("asset requests remain bounded and asynchronous", "RequestAsyncLoad(Paths" in core and "MeshCache.Num()==36" in core and "LoadSynchronous" not in net)
rules = json.loads(read("Content/ColdSteelData/planting_rules.json"))
catalog = json.loads(read("Content/ColdSteelData/crop_models_v3.json"))
paths = [path for crop in catalog["crops"].values() for variant in crop["variants"].values() for path in variant["stages"].values()]
check("four crops still use 36 V3 packages", len(rules["crops"])==4 and len(paths)==36 and all((P/"Content"/(path.split(".")[0].removeprefix("/Game/")+".uasset")).is_file() for path in paths))
report = {"checks": len(checks), "failures": sum(not x["passed"] for x in checks), "results": checks, "ue_started": False, "game_or_server_started": False, "runtime_tests_executed": False, "source_sha256": {path: hashlib.sha256((P/path).read_bytes()).hexdigest() for path in ["Source/FPSGAME/Building/ColdSteelPlantingSystem.cpp", "Source/FPSGAME/Building/ColdSteelPlantingNetwork.cpp", "Source/FPSGAME/Multiplayer/ColdSteelPlantingAuthority.cpp"]}}
(OUT/"static-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in ("results", "source_sha256")}))
if report["failures"]:
    print(json.dumps([x for x in checks if not x["passed"]],ensure_ascii=False))
    raise SystemExit(1)
