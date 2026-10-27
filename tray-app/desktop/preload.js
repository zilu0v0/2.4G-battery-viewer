const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('battery',{
  ...(process.argv.includes('--verify')?{verifyCapture:options=>ipcRenderer.invoke('verify-capture',options)}:{}),
  getState:()=>ipcRenderer.invoke('get-state'),
  refresh:()=>ipcRenderer.invoke('refresh'),
  action:action=>ipcRenderer.invoke('action',action),
  onState:callback=>ipcRenderer.on('state',(_event,state)=>callback(state)),
  onReveal:callback=>ipcRenderer.on('reveal',()=>callback())
});
