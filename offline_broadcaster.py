"""
EvacuMate - Offline Multicast DNS (mDNS) Broadcaster & Port 80 Redirector
-------------------------------------------------------------------------
Enables a single, permanent, fixed URL: http://evacumate.local:8550
Works 100% OFFLINE without any internet connection.
Accessible across all modern devices (iOS Safari, Android Chrome, Windows, Mac, tablets).
"""

import socket
import struct
import threading
import time
import os
import sys

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
DOMAIN_NAME = "evacumate.local"

def get_best_local_ip():
    """Detects active local Wi-Fi or LAN IP address."""
    # Method 1: Connect to dummy address without sending packets
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Method 2: Inspect host name addresses
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def build_dns_response(query_data, ip_str):
    """Builds an RFC 6762 mDNS authoritative response packet for query."""
    if len(query_data) < 12:
        return None
    tid = query_data[:2]
    flags = b'\x84\x00'  # Standard query response, Authoritative
    qdcount = query_data[4:6]
    ancount = b'\x00\x01'  # 1 answer
    nscount = b'\x00\x00'
    arcount = b'\x00\x00'
    header = tid + flags + qdcount + ancount + nscount + arcount

    # Extract question section
    idx = 12
    while idx < len(query_data):
        length = query_data[idx]
        if length == 0:
            idx += 1
            break
        idx += 1 + length

    idx += 4  # Skip QTYPE and QCLASS
    question_section = query_data[12:idx]

    # Answer: pointer to name in question section (offset 12 = 0xc00c)
    name_ptr = b'\xc0\x0c'
    atype = b'\x00\x01'       # A record
    aclass = b'\x80\x01'      # IN + cache-flush bit
    attl = struct.pack('>I', 120)  # 120 seconds TTL
    ardlen = b'\x00\x04'
    ardata = socket.inet_aton(ip_str)

    answer_section = name_ptr + atype + aclass + attl + ardlen + ardata
    return header + question_section + answer_section

def build_mdns_announcement(ip_str):
    """Builds an unsolicited mDNS announcement packet to broadcast to 224.0.0.251."""
    tid = b'\x00\x00'
    flags = b'\x84\x00'
    qdcount = b'\x00\x00'
    ancount = b'\x00\x01'
    nscount = b'\x00\x00'
    arcount = b'\x00\x00'
    header = tid + flags + qdcount + ancount + nscount + arcount

    # \x09evacumate\x05local\x00
    qname = b'\x09evacumate\x05local\x00'
    atype = b'\x00\x01'
    aclass = b'\x80\x01'
    attl = struct.pack('>I', 120)
    ardlen = b'\x00\x04'
    ardata = socket.inet_aton(ip_str)

    return header + qname + atype + aclass + attl + ardlen + ardata

class MdnsBroadcaster:
    def __init__(self, target_port=8550):
        self.target_port = target_port
        self.running = False
        self.sock = None
        self.thread = None
        self.announce_thread = None

    def start(self):
        if self.running:
            return
        self.running = True

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                self.sock.bind(('', MDNS_PORT))
            except Exception as e:
                # If cannot bind to 5353, another mDNS daemon might hold exclusive lock
                return

            mreq = struct.pack('4sl', socket.inet_aton(MDNS_GROUP), socket.INADDR_ANY)
            try:
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                pass

            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()

            self.announce_thread = threading.Thread(target=self._announce_loop, daemon=True)
            self.announce_thread.start()

        except Exception as e:
            pass

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                if len(data) < 12:
                    continue

                # Check if query (QR bit == 0)
                if (data[2] & 0x80) != 0:
                    continue

                # Check if question mentions "evacumate"
                data_lower = data.lower()
                if b'evacumate' in data_lower:
                    current_ip = get_best_local_ip()
                    resp = build_dns_response(data, current_ip)
                    if resp:
                        # Send unicast to requester
                        try:
                            self.sock.sendto(resp, addr)
                        except Exception:
                            pass
                        # Also multicast to group so all clients learn it
                        try:
                            self.sock.sendto(resp, (MDNS_GROUP, MDNS_PORT))
                        except Exception:
                            pass
            except Exception:
                if not self.running:
                    break
                time.sleep(0.1)

    def _announce_loop(self):
        """Periodically broadcast mDNS announcement so devices keep the name cached."""
        while self.running:
            try:
                current_ip = get_best_local_ip()
                if current_ip != "127.0.0.1":
                    announcement = build_mdns_announcement(current_ip)
                    self.sock.sendto(announcement, (MDNS_GROUP, MDNS_PORT))
            except Exception:
                pass
            time.sleep(45)

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

def start_port80_redirector(target_port=8550):
    """Attempts to listen on port 80 to redirect http://evacumate.local -> :target_port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 80))
        s.listen(10)

        def handle_client(conn):
            try:
                conn.recv(1024)
                redirect = (
                    "HTTP/1.1 302 Found\r\n"
                    f"Location: http://evacumate.local:{target_port}/\r\n"
                    "Content-Length: 0\r\n"
                    "Connection: close\r\n\r\n"
                )
                conn.sendall(redirect.encode('utf-8'))
            except Exception:
                pass
            finally:
                conn.close()

        def loop():
            while True:
                try:
                    conn, _ = s.accept()
                    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
                except Exception:
                    break

        threading.Thread(target=loop, daemon=True).start()
        return True
    except Exception:
        return False

# Global instance
_broadcaster = None

def init_offline_broadcaster(target_port=8550):
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = MdnsBroadcaster(target_port=target_port)
        _broadcaster.start()
        start_port80_redirector(target_port=target_port)
    return _broadcaster
