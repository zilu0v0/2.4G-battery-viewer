import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import devices as d
def iface(path='receiver-a',vid=0x046d,pid=0xc54d):
    return SimpleNamespace(path=path,vid=vid,pid=pid,usage_page=0xff00,output_len=20,product='USB Receiver')
class Discovery(unittest.TestCase):
    def scan(self,items):
        with patch.object(d.hw,'enumerate_hid',return_value=items),patch.object(d,'read_logitech',side_effect=lambda x:d.Reading('mouse','Actual Model',67)):
            return d.read_local()
    def test_empty(self):self.assertEqual(self.scan([]),[])
    def test_unsupported_not_queried(self):self.assertEqual(self.scan([iface(vid=123,pid=456)]),[])
    def test_only_present(self):
        rows=self.scan([iface()]);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['name'],'Actual Model')
    def test_two_receivers(self):
        rows=self.scan([iface('a'),iface('b')]);self.assertEqual(len(rows),2);self.assertNotEqual(rows[0]['key'],rows[1]['key'])
    def test_duplicate_endpoint(self):self.assertEqual(len(self.scan([iface(),iface()])),1)
    def test_unplug(self):
        self.assertEqual(len(self.scan([iface()])),1);self.assertEqual(self.scan([]),[])
    def test_query_failure_still_present(self):
        with patch.object(d.hw,'enumerate_hid',return_value=[iface()]),patch.object(d,'read_logitech',side_effect=OSError('offline')):
            rows=d.read_local();self.assertEqual(len(rows),1);self.assertIsNone(rows[0]['level']);self.assertEqual(rows[0]['name'],'USB Receiver')
if __name__ == '__main__':
    unittest.main()
