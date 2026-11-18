import sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from monitor import Target,check,connect,record,latest,history,load_targets,validate_target

class MonitorTests(unittest.TestCase):
    def test_invalid_protocol(self):
        with self.assertRaises(ValueError):validate_target(Target('x','file:///etc/passwd'))
    def test_private_blocked(self):
        with self.assertRaises(ValueError):validate_target(Target('x','http://127.0.0.1'))
    def test_invalid_timeout(self):
        with self.assertRaises(ValueError):validate_target(Target('x','https://example.com',0))
    def test_failed_request(self):
        r=check(Target('local','http://127.0.0.1:1'),allow_private=True)
        self.assertFalse(r['ok']);self.assertIsNotNone(r['error'])
    def test_storage(self):
        with tempfile.TemporaryDirectory() as d:
            db=connect(Path(d)/'db.sqlite');r=dict(name='a',url='https://example.com',timestamp='2026-01-01',ok=True,status=200,latency_ms=11,error=None)
            record(db,r);record(db,{**r,'ok':False,'status':500})
            self.assertEqual(len(history(db,'a')),2);self.assertEqual(latest(db)[0]['status'],500)
            db.close()
    def test_config(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.json';p.write_text('[{"name":"x","url":"https://example.com"}]')
            self.assertEqual(load_targets(p)[0].name,'x')
if __name__=='__main__':unittest.main()
