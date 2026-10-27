import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from devices import parse_razer,parse_asus,parse_logitech,razer_frame,read_razer

class ProtocolTests(unittest.TestCase):
    sample=bytes.fromhex('02 0e 50 49 08 d9 a9 59 01 00 04 00 21 01 01 39')+bytes(48)
    def test_real_razer_capture(self):self.assertEqual(parse_razer(self.sample,0x21),57)
    def test_wrong_command_and_truncated(self):
        self.assertIsNone(parse_razer(self.sample,0x2a))
        self.assertIsNone(parse_razer(self.sample[:15],0x21))
    def test_remote_ack_is_not_battery(self):
        b=bytes.fromhex('02 0d 50 49 01 c0 5b da 21 00 03 00 0e 80 00 20')+bytes(48)
        self.assertIsNone(parse_razer(b,0x21))
    def test_invalid_and_zero_level(self):
        b=bytearray(self.sample);b[15]=255
        self.assertIsNone(parse_razer(b,0x21))
        b[15]=0;self.assertEqual(parse_razer(b,0x21),0)
    def test_asus_real_capture(self):
        b=bytes.fromhex('02 12 01 00 00 00 13 04 01 01')
        self.assertEqual(parse_asus(b),(19,True))
    def test_logi_real_capture(self):
        b=bytes.fromhex('11 01 06 19 43 04 00 00')
        self.assertEqual(parse_logitech(b),(67,False))
    def test_command_allowlist(self):
        with self.assertRaises(ValueError):razer_frame(0x93)
        self.assertEqual(razer_frame(0x21)[9:11],bytes([3,0x21]))
    def test_disconnected_not_zero(self):
        self.assertIsNone(read_razer([]).level)

if __name__=='__main__':unittest.main()
