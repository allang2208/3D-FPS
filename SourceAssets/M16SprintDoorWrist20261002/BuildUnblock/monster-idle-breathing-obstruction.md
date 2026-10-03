# Monster idle breathing Editor build obstruction

Observed 2026-10-02: the assigned `Source/FPSGAME/Monsters/MonsterIdleBreathingAnimInstance.cpp` and its matching AnimInstance header no longer exist in the current shared source tree. A scoped search of `Source` finds no remaining `DefaultLinkedInstanceInputNode` access or `MonsterIdleBreathingAnimInstance` identifier. The tree currently contains `MonsterIdleBreathingMeshComponent.h` instead, saved at 15:46:08.

The local UE 5.8 `FAnimInstanceProxy::DefaultLinkedInstanceInputNode` is private. No source change is made because the originally reported offending file has been removed by parallel work. Do not recreate the former implementation or overwrite the new mesh-component implementation. Root agent may resume its normal build against the current source state; no build or test was run by this worker.
