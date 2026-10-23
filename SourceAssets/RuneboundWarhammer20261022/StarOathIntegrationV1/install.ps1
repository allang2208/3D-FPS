$ErrorActionPreference='Stop'
# This authors an independent engine-only project, not the shared editor world.
# The installer only creates absent package files in this task's new directory.
& py -3.11 (Join-Path $PSScriptRoot 'author_isolated.py')
exit $LASTEXITCODE
