import json, subprocess, time, signal, os, sys, threading, queue
from pathlib import Path
from .core import *
from .reactions import audio_filter

stopping=False
process=None

def terminate_tree(proc):
    if proc.poll() is not None: return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        try: os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError: pass

def stop(*_):
    global stopping
    stopping=True
    if process and process.poll() is None: terminate_tree(process)

signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
if hasattr(signal,'SIGBREAK'): signal.signal(signal.SIGBREAK,stop)

def lock_worker():
    f=open(DATA/'worker.lock','a+b'); f.seek(0); f.write(b'0'); f.flush(); f.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError: raise SystemExit('Já existe um trabalhador ativo.')
    return f

def run_job(j):
    global process
    d=json.loads(j['snapshot']); folder=DATA/j['project_id']; out=folder/f"{j['id']}.mp4"; tmp=folder/f"{j['id']}.partial.mp4"
    try:
        subs=folder/f"{j['id']}.srt"; subs.write_text(srt(d.get('subtitles',[])),encoding='utf-8')
        ass=folder/f"{j['id']}.ass"; ass.write_text(ass_text(d),encoding='utf-8')
        # Jobs queued by older releases also need dimensions after autorotation.
        if d['meta'].get('orientationVersion')!=1: d['meta']=probe(d['path'])
        if d.get('reactionPath') and d['reactionMeta'].get('orientationVersion')!=1: d['reactionMeta']=probe(d['reactionPath'])
        proxy=d.get('kind')=='proxy'
        filt=('[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1[v]' if proxy else geometry(d,d['meta'])); label='v'
        if d.get('subtitles'):
            # Fixed internally generated basename; cwd keeps user paths out of the filter grammar.
            filt+=f";[v]ass={ass.name}[sub]"; label='sub'
        filt+=f';[{label}]fps=30,format=yuv420p[final]'
        cmd=[FFMPEG,'-hide_banner','-nostdin','-y','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm','-ss',str(d['start']),'-i',d['path']]
        if d.get('reactionPath'):
            cmd+=['-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm','-ss',str(max(0,d['start']-d['reactionOffset'])),'-i',d['reactionPath']]
            audio,has_audio=audio_filter(d)
            if audio: filt+=';'+audio
            audio_map=['-map','[aout]'] if has_audio else []
            audio_extra=[]
        else:
            audio_map=['-map','0:a?']; audio_extra=['-af','aresample=async=1:first_pts=0']
        cmd+=['-t',str(d['end']-d['start']),'-filter_complex',filt,'-map','[final]',*audio_map,'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-filter_complex_threads','1','-c:a','aac','-b:a','160k',*audio_extra,'-movflags','+faststart','-progress','pipe:1',str(tmp)]

        with open(folder/f"{j['id']}.log",'w',encoding='utf-8') as log:
            process=subprocess.Popen(cmd,cwd=folder,stdout=subprocess.PIPE,stderr=log,text=True,**({'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}))
            lines=queue.Queue()
            def read_progress():
                for line in process.stdout: lines.put(line)
            reader=threading.Thread(target=read_progress,daemon=True); reader.start()
            while process.poll() is None:
                with db() as c: state=c.execute('SELECT state FROM jobs WHERE id=?',(j['id'],)).fetchone()['state']
                if state=='cancelado' or stopping:
                    terminate_tree(process)
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
                    raise ValueError('Processamento cancelado ou interrompido.')
                # FFmpeg emits periodic progress while encoding; HTTP server remains independent.
                try: line=lines.get(timeout=.2)
                except queue.Empty: continue
                if line.startswith('out_time_us='):
                    try: p=min(.99,int(line.split('=')[1])/1e6/(d['end']-d['start']))
                    except ValueError: continue
                    with db() as c: c.execute('UPDATE jobs SET progress=? WHERE id=?',(p,j['id']))
            if process.returncode: raise ValueError('FFmpeg falhou. Consulte o log da tarefa.')
        meta=probe(tmp)
        if (not proxy and (meta['width'],meta['height'])!=(1080,1920)) or abs(meta['duration']-(d['end']-d['start']))>.3: raise ValueError('Resultado com duração ou resolução inesperada.')
        with db() as c:
            state=c.execute('SELECT state FROM jobs WHERE id=?',(j['id'],)).fetchone()['state']
            if state=='cancelado' or stopping: raise ValueError('Processamento cancelado ou interrompido.')
            tmp.replace(out); c.execute("UPDATE jobs SET state='concluído',progress=1,output=? WHERE id=?",(str(out),j['id']))
        try:
            subprocess.run([FFMPEG,'-v','error','-nostdin','-y','-i',str(out),'-frames:v','1','-vf','scale=180:-2',str(folder/(j['id']+'.jpg'))],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        except (OSError,subprocess.SubprocessError): pass
    except Exception as e:
        tmp.unlink(missing_ok=True)
        with db() as c: c.execute("UPDATE jobs SET state=CASE WHEN state='cancelado' THEN state ELSE 'falhou' END,error=? WHERE id=?",(str(e),j['id']))
    finally:
        process=None
        with db() as c: c.execute('UPDATE jobs SET running=0 WHERE id=?',(j['id'],))

def main():
    lock=lock_worker()
    with db() as c: c.execute("UPDATE jobs SET state='falhou',running=0,error='Trabalhador interrompido. Tente novamente.' WHERE state='processando'")
    while not stopping:
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); j=c.execute("SELECT * FROM jobs WHERE state='aguardando' ORDER BY created,rowid LIMIT 1").fetchone()
            if j: c.execute("UPDATE jobs SET state='processando',running=1 WHERE id=?",(j['id'],))
        if j: run_job(dict(j))
        else: time.sleep(.4)

if __name__=='__main__': main()
