'use strict';
const {app,BrowserWindow,Tray,Menu,ipcMain,nativeImage,screen,nativeTheme,powerMonitor,session}=require('electron');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const readline=require('node:readline');
const {flyoutBounds}=require('./geometry');
const BASE=path.resolve(__dirname,'..');
const runtime=app.isPackaged?null:{python:process.env.BATTERY_PYTHON || path.join(BASE,'.venv','Scripts','python.exe')};
const reader=app.isPackaged?path.join(process.resourcesPath,'reader','battery-reader.exe'):runtime.python;
const readerArgs=app.isPackaged?['--serve']:[path.join(BASE,'devices.py'),'--serve'];
app.setName('我的设备电量');
app.setPath('userData',path.join(app.getPath('appData'),'LuckyBattery'));
app.setAppUserModelId('LuckyLu.Battery.Desktop');
let flyout,tray,timer,child,quitting=false,hideAt=0;
const settings={interval:60,theme:'light',reducedMotion:false};
let state={rows:[],busy:false,updatedAt:null,error:null};
function snapshot(){return {...state,settings,dark:nativeTheme.shouldUseDarkColors};}
function broadcast(){for(const w of [flyout])if(w&&!w.isDestroyed())w.webContents.send('state',snapshot());}
function schedule(){clearTimeout(timer);timer=setTimeout(refresh,settings.interval*1000);}
function updateTray(){
  if(!tray)return;
  tray.setToolTip('我的设备电量\n'+state.rows.map(r=>`${r.name}：${r.level===null?'未读到':r.level+'%'}${r.charging?' · 充电中':''}`).join('\n'));
}
let readDeadline;
function finishRead(payload){
  clearTimeout(readDeadline);
  try{
    if(payload.error)throw Error(payload.error);
    const rows=payload.rows,keys=new Set();
    if(!Array.isArray(rows))throw Error('设备回复格式异常');
    state.rows=rows.map(row=>{
      if(!row||typeof row.key!=='string'||keys.has(row.key)||typeof row.name!=='string'||
        !(row.level===null||(Number.isInteger(row.level)&&row.level>=0&&row.level<=100)))throw Error('设备电量格式异常');
      keys.add(row.key);return row;
    });
    state.error=null;
  }catch(e){state.rows=[];state.error=e.message;}
  state.updatedAt=Date.now();state.busy=false;updateTray();broadcast();schedule();
}
function refresh(){
  if(state.busy||quitting)return;
  clearTimeout(timer);state.busy=true;state.error=null;broadcast();
  if(!child){
    const worker=child=spawn(reader,readerArgs,{cwd:app.isPackaged?path.dirname(reader):BASE,windowsHide:true,stdio:['pipe','pipe','pipe']});
    worker.stderr.on('data',()=>{});
    worker.stdin.on('error',()=>{if(worker===child&&!quitting){child=null;worker.kill();finishRead({error:'电量读取连接已断开，请刷新重试'});}});
    const lines=readline.createInterface({input:worker.stdout});
    lines.on('line',line=>{if(worker!==child||quitting)return;try{finishRead(JSON.parse(line));}catch{finishRead({error:'设备回复格式异常'});}});
    worker.on('error',()=>{if(worker===child){child=null;finishRead({error:'无法启动电量读取程序'});}});
    worker.on('exit',()=>{if(worker===child){child=null;if(!quitting&&state.busy)finishRead({error:'读取程序已退出，请刷新重试'});}});
  }
  readDeadline=setTimeout(()=>{const old=child;child=null;if(old)old.kill();finishRead({error:'设备读取超时，请稍后刷新'});},90000);
  child.stdin.write('refresh\n');
}
function makeWindow(){
  const win=new BrowserWindow({width:424,height:512,minWidth:320,minHeight:420,
    frame:false,transparent:true,backgroundColor:'#00000000',show:false,
    resizable:false,maximizable:false,fullscreenable:false,skipTaskbar:true,alwaysOnTop:true,
    hasShadow:false,icon:path.join(__dirname,'assets','app.png'),title:'设备电量',
    webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true,backgroundThrottling:true,
      additionalArguments:process.argv.includes('--verify')?['--verify']:[]}});
  win.setMenu(null);
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',event=>event.preventDefault());
  win.loadFile(path.join(__dirname,'index.html'),{query:{view:'flyout'}});
  win.webContents.on('did-finish-load',()=>win.webContents.send('state',snapshot()));
  win.on('close',e=>{if(!quitting){e.preventDefault();win.hide();}});
  win.on('blur',()=>{hideAt=Date.now();win.hide();});
  return win;
}
function showFlyout(toggle=true){
  if(toggle&&(flyout.isVisible()||Date.now()-hideAt<180)){flyout.hide();return;}
  const bounds=tray.getBounds();
  const display=screen.getDisplayNearestPoint({x:bounds.x+Math.round(bounds.width/2),y:bounds.y+Math.round(bounds.height/2)});
  flyout.setBounds(flyoutBounds(bounds,display.workArea));
  flyout.show();flyout.focus();flyout.webContents.send('reveal');
  if(!state.updatedAt||Date.now()-state.updatedAt>15000)refresh();
}
const lock=app.requestSingleInstanceLock();
if(!lock){app.quit();}else{
  app.on('second-instance',()=>{if(flyout)showFlyout(false);});
  app.whenReady().then(async()=>{
    session.defaultSession.setPermissionRequestHandler((_w,_p,cb)=>cb(false));
    session.defaultSession.webRequest.onBeforeRequest({urls:['http://*/*','https://*/*','ws://*/*','wss://*/*']},(_d,cb)=>cb({cancel:true}));
    flyout=makeWindow();
    tray=new Tray(nativeImage.createFromPath(path.join(__dirname,'assets','tray.png')),'4d2284d9-3b89-4d88-aaf3-92bd5b896d79');
    tray.on('click',()=>showFlyout());
    tray.on('right-click',()=>tray.popUpContextMenu(Menu.buildFromTemplate([
      {label:'查看全部电量',click:()=>showFlyout(false)},
      {label:'立即刷新',click:refresh},
      {type:'separator'},{label:'退出',click:()=>app.quit()}])));
    updateTray();
    ipcMain.handle('get-state',()=>snapshot());
    // Local verification mode only; captures hidden windows without interrupting foreground apps.
    if(process.argv.includes('--verify'))ipcMain.handle('verify-capture',async(_event,options)=>{
      const win=flyout;
      if(options.width)win.setSize(options.width,options.height);
      const image=await win.webContents.capturePage(undefined,{stayHidden:true,stayAwake:true});
      fs.writeFileSync(path.join(app.getPath('temp'),'battery-verify-flyout.png'),image.toPNG());
      return {bounds:win.getBounds(),visible:win.isVisible(),trayBounds:tray.getBounds(),windows:BrowserWindow.getAllWindows().length};
    });
    ipcMain.handle('refresh',()=>{refresh();return true;});
    ipcMain.handle('action',(event,action)=>{
      const win=BrowserWindow.fromWebContents(event.sender);
      if(action==='flyout')showFlyout(false);
      else if(action==='hide')win.hide();
      else if(action==='quit')app.quit();
    });
    nativeTheme.on('updated',broadcast);
    powerMonitor.on('resume',()=>setTimeout(refresh,1500));
    screen.on('display-metrics-changed',()=>{if(flyout.isVisible())showFlyout(false);});
    flyout.once('ready-to-show',()=>{if(!process.argv.includes('--hidden'))showFlyout(false);});
    refresh();
  });
  app.on('window-all-closed',()=>{});
  app.on('before-quit',()=>{quitting=true;clearTimeout(timer);clearTimeout(readDeadline);if(child)child.kill();if(tray)tray.destroy();});
}
