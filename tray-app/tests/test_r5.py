import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from providers import attackshark_r5 as r
def reply(level=74,charging=0):
    return r.PREFIX+bytes([charging,level])+bytes(56)
class Fake:
    replies=[]
    writes=[]
    def open_path(self,path):pass
    def close(self):pass
    def send_feature_report(self,data):
        self.writes.append(data);return len(data)
    def get_feature_report(self,*args):return self.replies.pop(0)
class R5Tests(unittest.TestCase):
    def test_level_and_charging(self):
        self.assertEqual(r.parse_reply(reply()),(74,False))
        self.assertEqual(r.parse_reply(reply(100,1)),(100,True))
        self.assertEqual(r.parse_reply(reply(0)),(0,False))
    def test_missing_report_id(self):self.assertEqual(r.parse_reply(reply()[1:]),(74,False))
    def test_reject_bad_frames(self):
        for data in [b'',bytes(65),r.REQUEST,reply(101),reply(50,2),r.PREFIX,bytes.fromhex('00a10002020084')+bytes(58)]:
            self.assertIsNone(r.parse_reply(data))
    def test_busy_followup_battery_only(self):
        Fake.replies=[r.BUSY+bytes(58),reply(63,1)];Fake.writes=[]
        with patch.object(r.hid,'device',Fake),patch.object(r.time,'sleep'):
            self.assertEqual(r.AttackSharkR5Provider()._read(b'p'),(63,True))
        self.assertEqual(Fake.writes,[r.REQUEST])
    def test_busy_bounded(self):
        Fake.replies=[r.BUSY+bytes(58)]*3;Fake.writes=[]
        with patch.object(r.hid,'device',Fake),patch.object(r.time,'sleep'):
            self.assertIsNone(r.AttackSharkR5Provider()._read(b'p'))
        self.assertEqual(len(Fake.writes),1)
    def test_match_exact_receiver_no_false_devices(self):
        infos=[dict(product_id=p,usage_page=page,usage=0,path=str(p).encode()) for p,page in [(0x47,0xffff),(0x46,0xffff),(0x48,0xffff),(0x47,1)]]
        p=r.AttackSharkR5Provider()
        with patch.object(r.hidlist,'enumerate',return_value=infos),patch.object(p,'_read',return_value=(30,False)) as read:
            rows=p.poll();self.assertEqual(len(rows),2);self.assertEqual(read.call_count,2)
        with patch.object(r.hidlist,'enumerate',return_value=[]):self.assertEqual(p.poll(),[])
    def test_failure_unknown_not_zero(self):
        p=r.AttackSharkR5Provider()
        with patch.object(r.hidlist,'enumerate',return_value=[dict(product_id=0x47,usage_page=0xffff,usage=0,path=b'a')]),patch.object(p,'_read',return_value=None):
            self.assertIsNone(p.poll()[0].level)
if __name__=='__main__':unittest.main()
