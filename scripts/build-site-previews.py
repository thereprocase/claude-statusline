"""Render the website gallery from actual theme functions and synthetic data.

Run from any directory with Python 3.10+. No installed statusline, account,
transcript, Git subprocess, context publisher or state file is consulted.
"""
from pathlib import Path
from unittest.mock import patch
import sys, importlib, importlib.util, random, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'themes'))
# core's import creates its storage directory. Gallery builds need no storage.
with patch('os.makedirs'):
    import core
spec=importlib.util.spec_from_file_location('render_svg',ROOT/'generate-renders.py')
svg=importlib.util.module_from_spec(spec);spec.loader.exec_module(svg)
OUT=ROOT/'docs/assets';OUT.mkdir(parents=True,exist_ok=True)
names=['buddy','monochrome','amber','dracula','lcars','catppuccin','rainbow','outrun','ibm3278','c64','win95','teletext','matrix','skittles']
ctx={
    'model_name':'Op46','model_id':'claude-opus-4-6','model_family':'opus',
    'model_display':'Claude Opus 4.6','cw_size':1000000,'cw_str':'1M',
    'used_pct':42.0,'cwd':'/home/example/project','path_display':'/home/example/project',
    'email':'dev@example.com','user_short':'de','effort':None,
    'rate_limits':[{'key':'five_hour','label':'5h','pct':42,'reset_str':'3p','resets_at':2000000000},
                   {'key':'seven_day','label':'7d','pct':15,'reset_str':'','resets_at':2000000000}],
    'session_dur':'12m','session_elapsed':720,
    'git':{'branch':'main','detached':False,'dirty':2,'ahead':1,'behind':0,'stash':0,'remote_short':'gh:example','worktree':'','operation':''},
    'config':dict(core.DEFAULT_CONFIG),
}
for name in names:
    module=importlib.import_module(name)
    for pct in [42,85]:
        random.seed(42);ctx['used_pct']=float(pct)
        result=module.render(ctx)
        l1,l2=svg.split_lines(result)
        assert l1 and l2,(name,pct)
        rendered=svg.render_hero_svg(l1,l2).replace('rx="6"','rx="0"')
        rendered=rendered.replace('<style>',f'<title>{name} theme / synthetic session at {pct}% context</title><style>',1)
        (OUT/f'{name}-{pct}.svg').write_text(rendered,encoding='utf-8',newline='\n')
manifest={'purpose':'Actual theme output using synthetic session data; no user data.','percentages':[42,85],
          'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'themes/core.py',ROOT/'generate-renders.py',*[ROOT/'themes'/f'{n}.py' for n in names]]}}
(OUT/'preview-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Rendered 28 theme previews from synthetic data.')
