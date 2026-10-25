"""Ordered concatenation of server-owned rendered results."""
import json
from .core import FFMPEG, probe


def dependencies(c, *, job_id=None, project_id=None):
    for row in c.execute("SELECT snapshot FROM jobs WHERE state IN ('aguardando','processando') OR running=1"):
        for source in json.loads(row['snapshot']).get('sources',[]):
            if source.get('id')==job_id or source.get('project_id')==project_id:
                return True
    return False


def command(d,tmp):
    cmd=[FFMPEG,'-hide_banner','-nostdin','-y'];filters=[];labels=[]
    for i,source in enumerate(d['sources']):
        meta=probe(source['path']);duration=source['duration']
        cmd+=['-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm','-i',source['path']]
        filters.append(f'[{i}:v:0]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,trim=duration={duration},setpts=PTS-STARTPTS,format=yuv420p[v{i}]')
        if meta['audio']:
            filters.append(f'[{i}:a:0]aresample=48000:async=1:first_pts=0,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]')
        else:
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]')
        labels.append(f'[v{i}][a{i}]')
    filters.append(''.join(labels)+f'concat=n={len(labels)}:v=1:a=1[final][audio]')
    return cmd+['-filter_complex',';'.join(filters),'-map','[final]','-map','[audio]','-t',str(d['end']),'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-filter_complex_threads','1','-c:a','aac','-b:a','160k','-movflags','+faststart','-progress','pipe:1',str(tmp)]
