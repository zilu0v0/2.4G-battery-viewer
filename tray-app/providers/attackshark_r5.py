"""Attack Shark R5 Ultra battery-only adapter.

Protocol facts: maxboeer/attackshark-battery-bridge, R5 Ultra TOML profile.
65-byte report including ID 0; command 0x83, percent at byte 8, charging at 7.
No firmware/configuration commands are sent.
"""
import hashlib
import time
import hid
from . import hidlist
from .base import Provider,DeviceStatus

VID=0x373e
PIDS={0x0047:'2.4G',0x0046:'USB'}
REQUEST=bytes.fromhex('00000002020083').ljust(65,b'\0')
PREFIX=bytes.fromhex('00a10002020083')
BUSY=bytes.fromhex('00a30202008300')

def normalize(reply):
    data=bytes(reply)
    # Windows/hidapi versions may omit the unnumbered report-ID byte.
    if data and data[0] in (0xa1,0xa3):data=b'\0'+data
    return data

def parse_reply(reply):
    data=normalize(reply)
    if len(data)<9 or not data.startswith(PREFIX):return None
    if data[8]>100 or data[7] not in (0,1):return None
    return data[8],bool(data[7])

class AttackSharkR5Provider(Provider):
    name='attackshark_r5'
    def __init__(self):self._diag=[]
    def _read(self,path):
        dev=hid.device()
        try:
            dev.open_path(path)
            n=dev.send_feature_report(REQUEST)
            if n is not None and n!=len(REQUEST):
                self._diag.append('Incomplete feature write');return None
            for _ in range(3):
                time.sleep(.02)
                reply=normalize(dev.get_feature_report(0,65))
                parsed=parse_reply(reply)
                if parsed is not None:return parsed
                if not reply.startswith(BUSY):break
            self._diag.append('No valid R5 battery reply')
        except (OSError,ValueError) as e:self._diag.append(str(e))
        finally:dev.close()
        return None
    def poll(self):
        self._diag=[]
        out=[]
        seen=set()
        for d in hidlist.enumerate(VID):
            pid=d.get('product_id')
            if pid not in PIDS:continue
            # R5's documented descriptor: usage FFFF:0000, 64-byte feature body.
            if (d.get('usage_page'),d.get('usage'))!=(0xffff,0):continue
            path=d['path']
            if path in seen:continue
            seen.add(path)
            value=self._read(path)
            key='attackshark-r5:'+hashlib.sha256(path if isinstance(path,bytes) else path.encode()).hexdigest()[:20]
            out.append(DeviceStatus(key,'ATTACK SHARK R5 Ultra · '+PIDS[pid],
                value[0] if value else None,value[1] if value else False,
                value is not None,self.name,kind='mouse'))
        return out
    def diagnostics(self):return list(self._diag)
