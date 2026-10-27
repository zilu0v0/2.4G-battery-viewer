import sys,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import broad_protocols as b
from providers.base import DeviceStatus
class Bridge(unittest.TestCase):
    def test_offline_never_uses_cached_percent(self):
        self.assertIsNone(b.row(DeviceStatus('k','n',80,False,False)).get('level'))
    def test_range(self):
        for x in (-1,101,True):
            self.assertIsNone(b.row(DeviceStatus('k','n',x))['level'])
    def test_zero_and_coarse(self):
        self.assertEqual(b.row(DeviceStatus('k','n',0))['level'],0)
        self.assertTrue(b.row(DeviceStatus('k','n',50,approx='medium'))['approximate'])
    def test_one_provider_failure_does_not_hide_others(self):
        bad=SimpleNamespace(name='bad',poll=lambda:(_ for _ in ()).throw(OSError('offline')),diagnostics=lambda:[])
        good=SimpleNamespace(name='good',poll=lambda:[DeviceStatus('k','n',60)],diagnostics=lambda:[])
        with patch.object(b,'PROVIDERS',[bad,good]):
            self.assertEqual(b.scan()[0]['level'],60)
    def test_unknown_receiver_displayed_without_vendor_writes(self):
        d=SimpleNamespace(vid=0x1234,pid=0x5678,path='unknown',serial='',product='Test Wireless Receiver',feature_len=0,usage_page=0xff00,output_len=64)
        with patch.object(b,'COVERED',set()):
            out=b.extra([d],[])
            self.assertEqual(len(out),1);self.assertFalse(out[0]['supported']);self.assertIsNone(out[0]['level'])
    def test_no_receivers_no_phantoms(self):
        self.assertEqual(b.extra([],[]),[])
    def test_radio_strength_is_not_battery(self):
        self.assertNotIn((6,0x29),[x[:2] for x in b.hw.BATTERY_USAGES])
    def test_provider_registry(self):
        names={x.name for x in b.PROVIDERS}
        for name in ('logitech','razer','corsair','steelseries','keychron','mchose'):
            self.assertIn(name,names)
if __name__=='__main__':unittest.main()
