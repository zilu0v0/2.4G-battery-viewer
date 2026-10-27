"""Protocol providers pinned to HaloBattery 2251f05 (MIT), plus upstream HID strategies."""
import hashlib
import re
import logging
import providers
from providers import hidlist
import hid
import hid_win as hw
import upstream_battery as upstream
# The upstream debug helper also labels RF signal strength as battery; exclude it.
hw.BATTERY_USAGES=[x for x in hw.BATTERY_USAGES if x[:2] in ((0x0006,0x0020),(0x000d,0x003b))]

EXCLUDED={(0x0b05,0x1ace),(0x1532,0x0a49)}
_original_enumerate=hidlist.enumerate
def filtered_enumerate(vid=0):
    return [x for x in _original_enumerate(vid) if (x['vendor_id'],x['product_id']) not in EXCLUDED]
hidlist.enumerate=filtered_enumerate

# Keep provider objects alive: passive receivers (e.g. JBL) listen between refreshes.
PROVIDERS=[]
for name in providers.__dict__:
    cls=getattr(providers,name)
    if name.endswith('Provider') and name not in ('Provider','BluetoothProvider'):
        PROVIDERS.append(cls(listen_first=1.0) if name=='JblProvider' else cls())
# Record which receivers a provider actually opens; unknown receivers never receive
# invented commands and can still be shown as unsupported.
_original_device=hid.device
OPENED=set()
COVERED=set()
PAIR_CACHE={}
class TrackedDevice:
    def __init__(self,*args,**kwargs):self._dev=_original_device(*args,**kwargs)
    def __getattr__(self,name):return getattr(self._dev,name)
    def open_path(self,path,*args,**kwargs):
        text=path.decode(errors='replace') if isinstance(path,bytes) else path
        m=re.search(r'vid_([0-9a-f]{4})&pid_([0-9a-f]{4})',text.lower())
        if m:OPENED.add(tuple(int(x,16) for x in m.groups()))
        return self._dev.open_path(path,*args,**kwargs)
    def open(self,vid,pid,*args,**kwargs):
        OPENED.add((vid,pid));return self._dev.open(vid,pid,*args,**kwargs)
hid.device=TrackedDevice
DIAGNOSTICS={}
def row(st):
    valid=isinstance(st.level,int) and not isinstance(st.level,bool) and 0<=st.level<=100
    level=st.level if valid and st.online else None
    return dict(key='auto-'+hashlib.sha256(st.key.encode()).hexdigest()[:20],
        name=st.name,level=level,charging=bool(st.charging) if level is not None else None,
        kind=st.kind or ('headset' if st.source in ('razer','jbl','audeze','astro','hyperx','corsair','barracuda','logitech_centurion') else 'mouse'),
        source=st.source+' · '+('蓝牙' if st.via=='bluetooth' else '设备协议'),
        detail='设备实时上报' if level is not None else '设备未回复或休眠',
        approximate=bool(st.approx),supported=True)

def scan():
    out=[]
    COVERED.clear()
    # Only documented provider selection paths are invoked; no raw report-ID brute force.
    for provider in PROVIDERS:
        try:
            OPENED.clear()
            results=[st for st in provider.poll() if st.online or st.level is None]
            PAIR_CACHE.setdefault(provider.name,set()).update(OPENED)
            if results:COVERED.update(PAIR_CACHE[provider.name])
            out.extend(row(st) for st in results)
            DIAGNOSTICS[provider.name]=provider.diagnostics()
        except Exception as e:
            DIAGNOSTICS[provider.name]=[str(e)]
            logging.getLogger(__name__).warning('%s: %s',provider.name,e)
    return out

def _extra(ifaces,existing):
    out=[]
    # Retain the original project's published protocols; require its stated HID collection.
    # No generic nRF vendor write: VID 1915 alone identifies a chip vendor, not a protocol.
    allowed={(0x373b,0x1216,0xff05)}
    seen=set()
    for d in ifaces:
        pair=(d.vid,d.pid)
        if pair in EXCLUDED or d.vid==0x046d:continue
        sig=(d.path.lower())
        result=None
        if (d.vid,d.pid,d.usage_page) in allowed:
            result=upstream.strategy_vendor_protocol(d)
        elif (d.vid,d.pid,d.usage_page,d.output_len)==(0x3654,0x6901,0xff02,65):
            result=upstream.strategy_darkrim(d)
        elif d.feature_len:
            # Descriptor-declared battery fields only, never guessing bytes of other reports.
            result=upstream.strategy_standard_battery_usage(d)
        if result and result.ok and isinstance(result.level,int) and 0<=result.level<=100:
            token=(pair,d.serial or d.path.split('#')[2] if '#' in d.path else d.path)
            if token in seen:continue
            seen.add(token)
            out.append(dict(key='hid-'+hashlib.sha256(sig.encode()).hexdigest()[:20],
                name=result.extra.get('name') or d.product or d.display_name,
                level=result.level,charging=True if result.status=='charging' else False if result.status in ('discharging','full') else None,
                detail=result.detail,source=result.source,kind='headset' if d.vid==0x3654 else 'mouse',supported=True))
    return out

def extra(ifaces,existing):
    out=[]
    handled=set(COVERED)|EXCLUDED|{(0x046d,0xc54d)}
    for iface in ifaces:
        # Do not duplicate devices that a provider already owns.
        if (iface.vid,iface.pid) in handled:continue
        try:
            rows=_extra([iface],existing)
            if rows:
                out.extend(rows);handled.add((iface.vid,iface.pid))
        except Exception as e:
            DIAGNOSTICS['hid:'+iface.path]=[str(e)]
    # Display unidentified receiver candidates rather than pretending they are one of
    # the user's three devices. Generic USB peripherals are not battery candidates.
    seen=set()
    for iface in ifaces:
        pair=(iface.vid,iface.pid)
        if pair in handled or pair in seen:continue
        name=iface.product.strip()
        if not re.search(r'receiver|dongle|wireless|2[.]4|接收器|无线',name,re.I):continue
        seen.add(pair)
        out.append(dict(key=f'unsupported-{iface.vid:04x}-{iface.pid:04x}',
            name=name,level=None,charging=None,kind='device',supported=False,
            source=f'USB {iface.vid:04X}:{iface.pid:04X}',
            detail='已检测到无线接收器，尚未取得可用电量；型号或固件可能尚未适配'))
    return out
