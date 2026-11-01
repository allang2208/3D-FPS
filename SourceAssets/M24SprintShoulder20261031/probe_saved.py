from pathlib import Path
task=Path(__file__).parent
__file__=str(task.parent/'M24SprintArm20261031/setup.py')
exec(compile(Path(__file__).read_text(),'saved_setup','exec'))
ue['profiles']=json.loads((O/'profiles_saved.json').read_text());O=task
code=(O/'diagnose.py').read_text();exec(compile(code[code.index('def mixed'):code.index("\nif __name__=='__main__':")],'runtime','exec'))
exec(compile((O/'probe_body.py').read_text(),'probe','exec'))
