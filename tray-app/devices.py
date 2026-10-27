"""Only known battery/name queries for this PC. No device settings are written."""
import json
import time
import hashlib
from dataclasses import dataclass, asdict
import hid_win as hw

@dataclass
class Reading:
    key: str
    name: str
    level: int | None = None
    charging: bool | None = None
    detail: str = '接收器未连接'
    source: str = ''
    kind: str = 'device'

def exchange(dev, packet, match, timeout=.5):
    dev.drain()  # Opens a separate OVERLAPPED reader before sending the query.
    dev.write_output(bytes(packet), use_hidd=False)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        reply = dev.read_input(max(1, min(100, int((deadline-time.monotonic())*1000))))
        if reply and match(reply):
            return reply
    return None

def parse_logitech(reply):
    if len(reply) < 8 or reply[4] > 100:
        raise ValueError('罗技电量回复无效')
    # HID++ 0x1004 GetStatus: state-of-charge, level, charging-status, external-power.
    return reply[4], {0:False, 1:True, 2:True, 3:False}.get(reply[6])

def parse_asus(reply):
    if len(reply) < 10 or reply[:3] != b'\x02\x12\x01' or reply[6] > 100:
        raise ValueError('键盘电量回复无效')
    return reply[6], {0:False, 1:True}.get(reply[9])

def parse_razer(reply, command):
    # Xbox 0A49 verified on hardware: command/ACK/length/data at 12/13/14/15.
    # Bytes beyond the declared frame contain padding/undefined firmware data.
    if (len(reply) < 16 or reply[0] != 2 or reply[2:5] != b'PI\x08'
            or reply[12] != command or reply[13] != 1 or reply[14] != 1
            or reply[1] != 14):
        return None
    value = reply[15]
    if command == 0x21 and value <= 100:
        return value
    if command == 0x2a and value in (0,1):
        return value
    return None

def read_logitech(ifaces):
    r = Reading('mouse', '罗技无线设备', source='LIGHTSPEED · HID++')
    iface = next((d for d in ifaces if (d.vid,d.pid,d.usage_page,d.output_len)==(0x046d,0xc54d,0xff00,20)), None)
    if not iface:return r
    r.detail = '未收到有效回复，请移动鼠标唤醒后刷新'
    with hw.HidDevice(iface.path, True) as dev:
        def call(feature, function, params=()):
            body = ([0x11,1,feature,(function<<4)|9]+list(params)+[0]*20)[:20]
            return exchange(dev,body,lambda b:len(b)>=8 and b[:4]==bytes(body[:4]))
        name_feature=call(0,0,(0,5))
        if name_feature and name_feature[4]:
            feature=name_feature[4]
            length=call(feature,0)
            if length and 0 < length[4] <= 80:
                raw=b''
                while len(raw)<length[4]:
                    part=call(feature,1,(len(raw),))
                    if not part:break
                    raw+=part[4:]
                if len(raw)>=length[4]:
                    r.name=raw[:length[4]].decode('utf-8',errors='replace').strip() or r.name
        for _ in range(3):
            answer=call(0,0,(0x10,4))
            if not answer or not answer[4]:continue
            answer=call(answer[4],1)
            if answer:
                r.level,r.charging=parse_logitech(answer)
                r.detail='接收器实时读取'
                return r
    return r

def read_asus(ifaces):
    r=Reading('keyboard','ROG OMNI 无线设备',source='ROG OMNI · 2.4G')
    iface=next((d for d in ifaces if (d.vid,d.pid,d.usage_page)==(0x0b05,0x1ace,0xff00)),None)
    if not iface:return r
    r.detail='未收到有效回复，请按一下键盘后刷新'
    with hw.HidDevice(iface.path,True) as dev:
        for _ in range(3):
            answer=exchange(dev,[2,0x12,1]+[0]*61,lambda b:len(b)>=10 and b[:3]==b'\x02\x12\x01')
            if answer:
                r.level,r.charging=parse_asus(answer)
                r.detail='接收器实时读取'
                return r
    return r

def razer_frame(command=None,remote=None):
    b=bytearray(64)
    b[:3]=bytes([2,0x80,7 if remote is not None else 8])
    b[5:8]=b'PA'+bytes([0x0e if remote is not None else 8])
    if remote is not None:b[9:12]=bytes([2,0xe1,int(remote)])
    else:
        if command not in (0x21,0x2a):raise ValueError('Only battery queries allowed')
        b[9:11]=bytes([3,command])
    return bytes(b)

def read_razer(ifaces):
    r=Reading('headset','雷蛇旋风黑鲨 V2 Pro Xbox',source='BlackShark · 2.4G')
    iface=next((d for d in ifaces if (d.vid,d.pid,d.usage_page)==(0x1532,0x0a49,0xff00)),None)
    if not iface:return r
    r.detail='接收器已连接，耳机未回复；请确认耳机开机'
    with hw.HidDevice(iface.path,True) as dev:
        def remote(on):
            dev.write_output(razer_frame(remote=on),False)
            time.sleep(.04)
        def query(cmd):
            dev.drain()
            remote(True)
            for _ in range(3):
                remote(True)
                dev.write_output(razer_frame(cmd),False)
                deadline=time.monotonic()+.3
                while time.monotonic()<deadline:
                    b=dev.read_input(50)
                    if b:
                        value=parse_razer(b,cmd)
                        if value is not None:return value
            return None
        try:
            r.level=query(0x21)
            if r.level is not None:
                charge=query(0x2a)
                r.charging=None if charge is None else bool(charge)
                r.detail='接收器实时读取'
        finally:
            remote(False)  # Restore the temporary query session even on errors.
    return r

# Adapter selection is based on interfaces actually present in each scan.
# Each matching endpoint is read independently, including identical receivers.
def read_local():
    out=[]
    seen=set()
    for iface in hw.enumerate_hid():
        identity=(iface.vid,iface.pid,iface.usage_page)
        if identity==(0x046d,0xc54d,0xff00) and iface.output_len==20:
            kind,reader='mouse',read_logitech
        elif identity==(0x0b05,0x1ace,0xff00):
            kind,reader='keyboard',read_asus
        elif identity==(0x1532,0x0a49,0xff00):
            kind,reader='headset',read_razer
        else:
            continue
        endpoint=iface.path.lower()
        if endpoint in seen:continue
        seen.add(endpoint)
        name=iface.product.strip() or f'无线设备 {iface.vid:04X}:{iface.pid:04X}'
        try:
            r=reader([iface])
            # A receiver ID identifies the receiver, not the paired keyboard model.
            # Logitech name comes from the wireless device when it responds.
            if kind=='keyboard' or (kind=='mouse' and r.name=='罗技无线设备'):
                r.name=name
        except Exception as e:
            r=Reading('',name,detail='读取失败：'+str(e))
        r.key=hashlib.sha256(endpoint.encode()).hexdigest()[:20]
        r.kind=kind
        out.append(asdict(r))
    return out

def read_all():
    import broad_protocols as broad
    # Preserve the locally validated Xbox headset / OMNI paths.
    automatic=broad.scan()
    local=read_local()
    logi_names={r['name'] for r in automatic if r['source'].startswith('logitech')}
    local=[r for r in local if not(r['kind']=='mouse' and r['name'] in logi_names)]
    results=local+automatic
    results+=broad.extra(hw.enumerate_hid(),results)
    return list({r['key']:r for r in results}.values())

if __name__=='__main__':
    import sys
    if '--serve' in sys.argv:
        for line in sys.stdin:
            if line.strip()!='refresh':continue
            try: print(json.dumps({'rows':read_all()},ensure_ascii=True),flush=True)
            except Exception as e: print(json.dumps({'rows':[],'error':str(e)}),flush=True)
    else:
        print(json.dumps(read_all(),ensure_ascii=True))
