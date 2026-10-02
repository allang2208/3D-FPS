"""Remove only this task's completed temporary overlay, without following links."""
import json,os,shutil,stat
from pathlib import Path
O=Path(__file__).resolve().parent;root=O/'PackageStaging'
delivery=json.loads((O/'delivery.json').read_text())
if not delivery.get('saved') or delivery.get('staged') is not False:raise RuntimeError('Preserve unpublished staged packages')
if not root.exists():raise RuntimeError('No owned staging directory')
if root.resolve()!=root.absolute() or not root.resolve().is_relative_to(O):raise RuntimeError('Unexpected staging target')
def remove_links(folder):
 for entry in os.scandir(folder):
  info=entry.stat(follow_symlinks=False)
  if info.st_file_attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT:
   # rmdir removes the directory link itself; it never visits its target.
   if info.st_file_attributes&stat.FILE_ATTRIBUTE_DIRECTORY:os.rmdir(entry.path)
   else:os.unlink(entry.path)
  elif entry.is_dir(follow_symlinks=False):remove_links(Path(entry.path))
remove_links(root)
# The absolute root is still owned and all reparse links have been removed.
if root.resolve()!=O/'PackageStaging':raise RuntimeError('Staging root changed')
shutil.rmtree(root)
print('HK416_TEMPORARY_STAGING_RETIRED')
