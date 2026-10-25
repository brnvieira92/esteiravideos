"""Project-local cut numbering and matching of actual render definitions."""
import hashlib
import json
import re
from pathlib import Path
from .core import normalize_box


def next_cut_number(c,pid):
    names=[json.loads(r[0]).get('name','') for r in c.execute('SELECT data FROM cuts WHERE project_id=?',(pid,))]
    row=c.execute('SELECT next_number FROM cut_sequences WHERE project_id=?',(pid,)).fetchone()
    return max([row[0] if row else 1,len(names)+1]+[int(m[1])+1 for name in names if (m:=re.search(r' — parte (\d{1,18})$',name))])


def cut_name(project_name,number):
    suffix=f' — parte {number}'
    return project_name[:150-len(suffix)]+suffix


def fingerprint(d):
    if d.get('kind')=='merge':
        return hashlib.sha256(json.dumps([s['id'] for s in d['sources']]).encode()).hexdigest()
    # Whitelist render-affecting fields. Renaming a cut doesn't change its video.
    b=lambda key:{k:float(v) for k,v in normalize_box(d.get(key,dict(x=0,y=0,w=1,h=1))).items()}
    result={'path':d.get('path'),'start':float(d['start']),'end':float(d['end']),
            'size':[d.get('meta',{}).get('width'),d.get('meta',{}).get('height')],
            'layout':d.get('layout','gameplay'),'game':b('game')}
    if result['layout']=='webcam': result.pop('game')
    if result['layout'] in ('combined','webcam'):
        result.update(cam=b('cam'),camFlip=bool(d.get('camFlip',False)))
        if result['layout']=='combined': result['split']=float(d.get('split',.35))
    if d.get('reactionPath'):
        result.update(reactionPath=d['reactionPath'],reactionOffset=float(d.get('reactionOffset',0)),
                      reactionSize=[d.get('reactionMeta',{}).get('width'),d.get('reactionMeta',{}).get('height')],
                      baseVolume=0.0 if result['layout']=='webcam' else float(d.get('baseVolume',.35)),reactionVolume=float(d.get('reactionVolume',1)))
    result['subtitles']=[{'start':float(s['start']),'end':float(s['end']),'text':s['text']} for s in d.get('subtitles',[])]
    if result['subtitles']:
        result.update(fontSize=int(d.get('fontSize',64)),margin=int(d.get('margin',120)),outline=int(d.get('outline',3)))
    return hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def available_jobs(c,pid,kind,repeat=False):
    result={}
    for row in c.execute("SELECT * FROM jobs WHERE project_id=? AND state IN ('aguardando','processando','concluído','excluído') ORDER BY rowid",(pid,)):
        d=json.loads(row['snapshot'])
        if d.get('kind','export')!=kind: continue
        if repeat and row['state'] in ('concluído','excluído'): continue
        try: key=fingerprint(d)
        except (ValueError,KeyError,TypeError): continue
        matched=dict(row)
        if row['state']=='concluído' and (not row['output'] or not Path(row['output']).is_file()): matched['state']='excluído'
        # Prefer a usable result or running job over an older tombstone.
        priority={'excluído':0,'concluído':1,'aguardando':2,'processando':3}
        if key not in result or priority[matched['state']]>=priority[result[key]['state']]: result[key]=matched
    return result
