"""Trusted snapshot construction and two-source react rendering."""
import math
from .core import db


def attach_reaction(d,pid):
    # Paths and worker-only fields can only be supplied by server-side records.
    d={k:v for k,v in d.items() if k not in ('reactionPath','reactionMeta','kind','media_id')}
    rid=d.get('reactionId')
    if not rid:
        d.pop('reactionId',None)
        return d
    with db() as c: row=c.execute("SELECT * FROM media WHERE id=? AND project_id=? AND role='reaction'",(rid,pid)).fetchone()
    if not row: raise ValueError('Selecione uma reação deste projeto.')
    import json
    meta=json.loads(row['meta'])
    offset=float(d.get('reactionOffset',row['offset']))
    if not math.isfinite(offset): raise ValueError('Sincronização inválida.')
    if d.get('layout')!='combined': raise ValueError('Use Webcam + gameplay para mesclar a reação com o vídeo base.')
    if d['start']<offset-.001 or d['end']>offset+meta['duration']+.001:
        raise ValueError('O corte ultrapassa o trecho coberto pela reação. Ajuste o intervalo ou a sincronização.')
    d['reactionOffset']=offset
    for key,default in (('baseVolume',.35),('reactionVolume',1)):
        value=float(d.get(key,default))
        if not math.isfinite(value) or not 0<=value<=1: raise ValueError('Volume deve ficar entre 0 e 100%.')
        d[key]=value
    return {**d,'reactionPath':row['path'],'reactionMeta':meta}


def audio_filter(d):
    """Keep both gains explicit and mix without automatic volume reduction."""
    filters=[]; labels=[]
    for index,meta,key in ((0,d['meta'],'baseVolume'),(1,d['reactionMeta'],'reactionVolume')):
        if meta['audio'] and d[key]>0:
            label=f'a{index}'
            filters.append(f"[{index}:a:0]asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0,volume={d[key]},apad=whole_dur={d['end']-d['start']}[{label}]")
            labels.append(f'[{label}]')
    if len(labels)==2:
        filters.append(''.join(labels)+'amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.95:latency=1[aout]')
    elif labels:
        filters.append(labels[0]+'alimiter=limit=0.95:latency=1[aout]')
    return ';'.join(filters), bool(labels)
