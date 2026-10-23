import socket
import threading
import unittest

import _path  # noqa: F401
from yeal.core import adblock


class AdblockTests(unittest.TestCase):
    def test_matching(self):
        d = adblock.load_domains()
        self.assertTrue(adblock.is_blocked("ad.doubleclick.net", d))
        self.assertTrue(adblock.is_blocked("doubleclick.net", d))
        self.assertFalse(adblock.is_blocked("www.youtube.com", d))
        self.assertFalse(adblock.is_blocked("rr3---sn.googlevideo.com", d))
        self.assertFalse(adblock.is_blocked("notdoubleclick.net.example.org", d))

    def test_never_list_wins_over_hosts_file(self):
        got = adblock.parse_hosts("0.0.0.0 googlevideo.com\n0.0.0.0 ads.example.com # c\n127.0.0.1 localhost\n")
        self.assertEqual(got, {"googlevideo.com", "ads.example.com"})

    def test_proxy_blocks_and_tunnels(self):
        # tiny upstream echo server
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
        up_port = srv.getsockname()[1]

        def echo():
            c, _ = srv.accept()
            c.sendall(c.recv(100).upper())
            c.close()
        threading.Thread(target=echo, daemon=True).start()
        proxy = adblock.FilterProxy(adblock.load_domains())
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        try:
            def connect(host):
                s = socket.create_connection(("127.0.0.1", proxy.port), timeout=5)
                s.sendall(f"CONNECT {host} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
                return s, s.recv(200)
            s, reply = connect("ads.doubleclick.net:443")
            self.assertIn(b"403", reply); s.close()
            s, reply = connect(f"127.0.0.1:{up_port}")
            self.assertIn(b"200", reply)
            s.sendall(b"hello"); self.assertEqual(s.recv(100), b"HELLO"); s.close()
        finally:
            proxy.shutdown(); proxy.server_close(); srv.close()


if __name__ == "__main__":
    unittest.main()
