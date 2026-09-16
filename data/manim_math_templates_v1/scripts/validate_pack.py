from pathlib import Path
import json, py_compile, sys
ROOT=Path(__file__).resolve().parents[1]; req=['manifest.json','storyboard.json','rules.json','examples.json','scene.py']; errors=[]
for td in sorted((ROOT/'templates').iterdir()):
    if not td.is_dir(): continue
    for name in req:
        if not (td/name).exists(): errors.append(f'{td.name}: thiếu {name}')
    try:
        m=json.loads((td/'manifest.json').read_text(encoding='utf-8'))
        if m['template_id']!=td.name: errors.append(f'{td.name}: template_id không khớp thư mục')
        for n in ['storyboard.json','rules.json','examples.json']: json.loads((td/n).read_text(encoding='utf-8'))
        py_compile.compile(str(td/'scene.py'),doraise=True)
    except Exception as e: errors.append(f'{td.name}: {e}')
if errors:
    print('FAILED'); print('\n'.join('- '+e for e in errors)); sys.exit(1)
print('OK - JSON hợp lệ và scene.py qua py_compile.')
