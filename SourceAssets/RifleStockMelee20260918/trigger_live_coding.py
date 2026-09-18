"""让运行中的编辑器把本轮的 C++ 改动编进当前会话（Live Coding 补丁）。

用途：编辑器被占用时不能跑完整 UBT；Live Coding 能把模块补丁打进当前进程，
使 PIE 立刻用上步枪枪托砸击的接入代码。构建结果看 Saved/Logs/FPSGAME.log 的
LogLiveCoding 行。
"""
import unreal as u

u.SystemLibrary.execute_console_command(None, 'LiveCoding.Compile')
u.log('M4_QUICKCOMBAT_LIVE_CODING_REQUESTED')
