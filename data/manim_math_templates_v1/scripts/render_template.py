from pathlib import Path
import argparse, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]; TEMPLATES=ROOT/'templates'
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('template_id'); ap.add_argument('--params',default='{}'); ap.add_argument('--quality',default='l',choices=['l','m','h','p','k']); ap.add_argument('--media-dir',default=str(ROOT/'_media')); args=ap.parse_args()
    td=TEMPLATES/args.template_id; mp=td/'manifest.json'; sp=td/'scene.py'
    if not mp.exists(): raise SystemExit(f'Không tìm thấy template: {args.template_id}')
    m=json.loads(mp.read_text(encoding='utf-8')); params=json.loads(args.params); env=dict(os.environ); env['MANIM_TEMPLATE_JSON']=json.dumps(params,ensure_ascii=False)
    cmd=[sys.executable,'-m','manim',f'-q{args.quality}','--format=mp4','--media_dir',args.media_dir,str(sp),m['scene_class']]
    print('Running:',' '.join(cmd)); raise SystemExit(subprocess.call(cmd,env=env))
if __name__=='__main__': main()
