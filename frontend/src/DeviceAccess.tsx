import {useEffect,useState} from 'react';
export type SessionInfo={paired:boolean;lan:boolean;trusted:boolean;deviceName:string|null;expiresAt:number|null;canManageDevices:boolean;https:boolean};
type Device={id:string;name:string;created:number;lastUsed:number;expires:number;current:boolean};
type Props={session:SessionInfo;request:(path:string,method?:string,body?:unknown)=>Promise<unknown>;onClose:()=>void;onUnpair:()=>void};
const date=(t:number)=>new Date(t*1000).toLocaleString('pt-BR');
export function DeviceAccess({session,request,onClose,onUnpair}:Props){
 const [devices,setDevices]=useState<Device[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function load(){setDevices(await request('/devices') as Device[])}
 useEffect(()=>{if(session.canManageDevices)load().catch(e=>setError(e.message))},[]);
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(e instanceof Error?e.message:'Falha ao atualizar dispositivos.')}finally{setBusy(false)}}
 return <div className="overlay"><div className="dialog panel device-access" role="dialog" aria-modal="true" aria-labelledby="devices-title"><h2 id="devices-title">Dispositivos conectados</h2>
 <p>{session.trusted?`Este navegador é confiável até ${date(session.expiresAt!)}.`:session.lan?'Este navegador usa um pareamento temporário.':'O acesso local deste computador não exige pareamento.'}</p>
 {session.canManageDevices?<><h3>Dispositivos confiáveis</h3><p className="help">A confiança dura 90 dias e permanece após reiniciar ou atualizar o aplicativo. Revogar bloqueia as próximas requisições do dispositivo.</p>
 <div className="trusted-list">{devices.map(d=><article key={d.id}><div><strong>{d.name}{d.current?' (este navegador)':''}</strong><small>Autorizado: {date(d.created)}<br/>Último uso: {date(d.lastUsed)}<br/>Válido até: {date(d.expires)}</small></div><button disabled={busy} onClick={()=>void action(async()=>{await request('/devices/'+d.id,'DELETE');if(d.current)onUnpair();else await load()})}>Revogar</button></article>)}</div>
 {!devices.length&&<p className="help">Nenhum dispositivo confiável cadastrado.</p>}
 <button disabled={busy||!devices.length} onClick={()=>void action(async()=>{await request('/devices','DELETE');if(devices.some(d=>d.current))onUnpair();else await load()})}>Esquecer todos os dispositivos confiáveis</button></>:<p className="help">Para gerenciar os outros dispositivos, abra o aplicativo no próprio computador usando localhost ou 127.0.0.1.</p>}
 {session.lan&&<button disabled={busy} onClick={()=>void action(async()=>{await request('/unpair','POST');onUnpair()})}>{session.trusted?'Esquecer este dispositivo e sair':'Desconectar este navegador'}</button>}
 {error&&<p className="error-text">{error}</p>}<button disabled={busy} onClick={onClose}>Fechar</button></div></div>;
}
