from pathlib import Path
import json, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
errors=[]; total=0
for p in sorted((root/'questions').glob('C1_B*.json')):
 d=json.loads(p.read_text())
 for q in d['questions']:
  total+=1
  if not q.get('id'): errors.append((str(p),'missing id'))
  if q['question_type']=='multiple_choice_single' and not q.get('correct_answer'): errors.append((q['id'],'missing MC answer'))
  for a in q.get('assets',[]):
   if not (root/a).exists(): errors.append((q['id'],'missing asset '+a))
print('questions',total,'errors',len(errors))
for e in errors[:100]: print(*e)
raise SystemExit(1 if errors else 0)
