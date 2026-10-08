"""Public reproducibility archive: git-visible source only, never local runtime state."""
import subprocess
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
output=root/'public/source/opspilot-source.zip'
output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for rel in sorted(set(paths)):
        if not rel or rel.startswith(('public/source/','verification/worker.json')) or rel.endswith('tsbuildinfo') or rel.startswith('.env'):
            continue
        p=root/rel
        if p.is_file():
            z.write(p,'opspilot/'+rel)
print('Public source archive created:',output.stat().st_size,'bytes')
