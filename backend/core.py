import json, os, sqlite3, subprocess, uuid, re
from pathlib import Path
from .resources import executable

DATA = Path(os.getenv('ESTEIRA_DATA', str(Path(os.getenv('LOCALAPPDATA', Path.home() / '.local/share')) / 'esteira-videos'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
FFMPEG = executable('ffmpeg')
FFPROBE = executable('ffprobe')
MAX_UPLOAD = int(os.getenv('ESTEIRA_MAX_UPLOAD_GB', '20')) * 1024**3

def db():
    c = sqlite3.connect(DATA / 'esteira.db', timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init():
    with db() as c:
        if c.execute('PRAGMA user_version').fetchone()[0]>2: raise RuntimeError('Banco criado por uma versão mais recente do EsteiraVídeos.')
        c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,path TEXT NOT NULL,meta TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cuts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,snapshot TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'aguardando',progress REAL DEFAULT 0,error TEXT,output TEXT,reviewed INTEGER DEFAULT 0,title TEXT,description TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
''')
        columns={r[1] for r in c.execute('PRAGMA table_info(jobs)')}
        if 'running' not in columns: c.execute('ALTER TABLE jobs ADD COLUMN running INTEGER NOT NULL DEFAULT 0')
        c.execute('PRAGMA user_version=2')

def uid(): return uuid.uuid4().hex

def probe(path):
    r = subprocess.run([FFPROBE,'-v','error','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm','-show_format','-show_streams','-of','json',str(path)], capture_output=True, text=True, timeout=60)
    if r.returncode: raise ValueError('FFprobe não conseguiu validar o vídeo.')
    d=json.loads(r.stdout); v=next((s for s in d['streams'] if s['codec_type']=='video'),None)
    if not v: raise ValueError('Arquivo sem faixa de vídeo.')
    duration=float(d['format'].get('duration',0))
    if duration<=0: raise ValueError('Duração inválida.')
    n,den=map(int,v.get('avg_frame_rate','0/1').split('/'))
    return dict(duration=duration,width=v['width'],height=v['height'],fps=n/max(den,1),audio=any(s['codec_type']=='audio' for s in d['streams']),codec=v['codec_name'])

def validate_cut(d, duration):
    start=float(d.get('start',0)); end=float(d.get('end',0))
    if not 0<=start<end<=duration: raise ValueError('Use 0 ≤ início < fim ≤ duração da gravação.')
    d={**d,'start':start,'end':end,'name':str(d.get('name','Novo corte'))[:150]}
    if d.get('layout','gameplay') not in ('gameplay','combined'): raise ValueError('Layout inválido.')
    for key in ('game','cam'):
        box=d.get(key,dict(x=0,y=0,w=1,h=1))
        box={k:float(box[k]) for k in ('x','y','w','h')}
        if not (0<=box['x']<1 and 0<=box['y']<1 and .01<=box['w']<=1 and .01<=box['h']<=1 and box['x']+box['w']<=1.00001 and box['y']+box['h']<=1.00001): raise ValueError('Região fora dos limites da imagem.')
        d[key]=box
    if len(d.get('subtitles',[]))>5000: raise ValueError('Limite de 5000 blocos de legenda por corte.')
    d['split']=min(.7,max(.2,float(d.get('split',.35))))
    d['fontSize']=min(110,max(20,int(d.get('fontSize',64))))
    d['margin']=min(400,max(20,int(d.get('margin',120))))
    d['outline']=min(8,max(1,int(d.get('outline',3))))
    for s in d.get('subtitles',[]):
        if not 0<=float(s['start'])<float(s['end'])<=end-start: raise ValueError('Legenda fora do intervalo do corte (tempos relativos ao Short).')
        if len(s['text'])>2000: raise ValueError('Legenda muito longa.')
    return d

def stamp(t):
    ms=round(float(t)*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def srt(subtitles):
    return '\n\n'.join(f"{i+1}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text']}" for i,s in enumerate(subtitles))+'\n'

def parse_srt(text):
    out=[]
    def seconds(s):
        h,m,v=s.replace(',','.').split(':'); return int(h)*3600+int(m)*60+float(v)
    for block in re.split(r'\n\s*\n',text.replace('\r','').strip()):
        lines=block.splitlines(); idx=next((i for i,l in enumerate(lines) if '-->' in l),None)
        if idx is None: raise ValueError('Bloco SRT inválido.')
        a,b=lines[idx].split('-->'); out.append(dict(start=seconds(a.strip()),end=seconds(b.strip()),text='\n'.join(lines[idx+1:])))
    return out

def clipped_subtitles(items,start,end):
    return [{**s,'start':max(start,s['start'])-start,'end':min(end,s['end'])-start} for s in items if s['start']<end and s['end']>start]

def geometry(d,meta):
    def crop(key):
        b=d[key]; w=max(2,int(meta['width']*b['w'])//2*2); h=max(2,int(meta['height']*b['h'])//2*2)
        x=min(meta['width']-w,int(meta['width']*b['x'])//2*2); y=min(meta['height']-h,int(meta['height']*b['y'])//2*2)
        return f'crop={w}:{h}:{x}:{y}'
    def fit(w,h): return f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1'
    if d.get('layout')=='combined':
        top=int(1920*d['split'])//2*2
        return f"[0:v]split=2[c][g];[c]{crop('cam')},{fit(1080,top)}[cam];[g]{crop('game')},{fit(1080,1920-top)}[game];[cam][game]vstack=inputs=2[v]"
    return f"[0:v]{crop('game')},{fit(1080,1920)}[v]"

init()


def ass_text(d):
    def esc(text):
        return str(text).replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n','\\N').replace('\r','')
    def ast(t):
        t=round(float(t)*100); h,t=divmod(t,360000); m,t=divmod(t,6000); sec,cs=divmod(t,100)
        return f'{h}:{m:02}:{sec:02}.{cs:02}'
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{d['fontSize']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{d['outline']},0,2,45,45,{d['margin']},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header+'\n'.join(f"Dialogue: 0,{ast(s['start'])},{ast(s['end'])},Default,,0,0,0,,{esc(s['text'])}" for s in d.get('subtitles',[]))
