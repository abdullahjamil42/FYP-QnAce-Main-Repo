# Computer Networks and Cloud Computing — Interview Prep Notes

## 1. OSI Model (7 Layers)

| Layer | Name | Function | Protocols / Examples |
|-------|------|----------|---------------------|
| 7 | **Application** | End-user services, interface for apps | HTTP, HTTPS, FTP, SMTP, DNS, SSH, SNMP |
| 6 | **Presentation** | Data format translation, encryption, compression | SSL/TLS, JPEG, MPEG, ASCII, JSON, XML |
| 5 | **Session** | Session management, authentication, dialog control | NetBIOS, RPC, PPTP, SIP |
| 4 | **Transport** | End-to-end delivery, flow control, error recovery | TCP, UDP, QUIC, SCTP |
| 3 | **Network** | Logical addressing, routing between networks | IP, ICMP, ARP, OSPF, BGP, IPsec |
| 2 | **Data Link** | Frame creation, MAC addressing, error detection | Ethernet, Wi-Fi (802.11), PPP, ARP, VLAN |
| 1 | **Physical** | Raw bit transmission over physical medium | Cables, fiber optics, radio signals, hubs |

**Mnemonic (top-down)**: All People Seem To Need Data Processing.

**Interview tip**: Know which layer each protocol operates at and how data encapsulation works — data → segment → packet → frame → bits.

---

## 2. TCP/IP Model

The practical model used on the internet. Maps OSI's 7 layers into 4:

| TCP/IP Layer | OSI Equivalent | Key Protocols |
|--------------|---------------|---------------|
| Application | Layers 5–7 | HTTP, DNS, FTP, SMTP, SSH |
| Transport | Layer 4 | TCP, UDP |
| Internet | Layer 3 | IP, ICMP, ARP |
| Network Access | Layers 1–2 | Ethernet, Wi-Fi |

---

## 3. TCP vs UDP

| Feature | TCP | UDP |
|---------|-----|-----|
| Connection | Connection-oriented (3-way handshake) | Connectionless |
| Reliability | Guaranteed delivery (ACKs, retransmission) | Best-effort, no guarantee |
| Ordering | In-order delivery | No ordering |
| Flow Control | Yes (sliding window) | No |
| Congestion Control | Yes (slow start, AIMD) | No |
| Header Size | 20 bytes minimum | 8 bytes |
| Speed | Slower due to overhead | Faster |
| Use Cases | Web (HTTP), email, file transfer | Video streaming, gaming, DNS queries, VoIP |

**When asked "TCP or UDP?"**: TCP for reliability (web pages, file transfer); UDP for speed and tolerance to loss (live video, gaming, DNS).

---

## 4. TCP Three-Way Handshake

```
Client                    Server
  |                         |
  |--- SYN (seq=x) ------->|     Step 1: Client initiates
  |                         |
  |<-- SYN-ACK (seq=y, -----|     Step 2: Server acknowledges + initiates
  |    ack=x+1)             |
  |                         |
  |--- ACK (ack=y+1) ----->|     Step 3: Client acknowledges
  |                         |
  |===== Connection Open ===|
```

**Connection teardown** uses a **4-way handshake**: FIN → ACK → FIN → ACK (either side can initiate).

**Important concepts**: SYN flooding (DoS attack), TIME_WAIT state (2×MSL to handle delayed packets), sequence number for ordering.

---

## 5. DNS Resolution Process

1. User types `www.example.com` in browser
2. Browser checks **local cache** → OS cache → hosts file
3. Query goes to **recursive DNS resolver** (usually ISP or 8.8.8.8)
4. Resolver queries **root name server** (.) → returns `.com` TLD server address
5. Resolver queries **TLD name server** (.com) → returns authoritative NS for `example.com`
6. Resolver queries **authoritative name server** → returns IP address (e.g., 93.184.216.34)
7. Resolver **caches** the result (respecting TTL) and returns to client
8. Browser initiates TCP connection to the IP address

**DNS Record Types**:
- **A**: Maps domain to IPv4 address
- **AAAA**: Maps domain to IPv6 address
- **CNAME**: Alias — points one domain to another
- **MX**: Mail exchange server
- **NS**: Authoritative name server
- **TXT**: Arbitrary text (used for SPF, DKIM, domain verification)
- **SOA**: Start of Authority — primary NS and zone metadata

---

## 6. HTTP Versions

### HTTP/1.1
- **Persistent connections** (keep-alive) — reuse TCP connection
- **Pipelining** (rarely used) — send multiple requests without waiting for responses
- **Problem**: Head-of-line blocking — must process responses in order
- **One request/response per connection** in practice

### HTTP/2
- **Binary framing** — more efficient parsing than text-based HTTP/1.1
- **Multiplexing**: Multiple streams over a **single TCP connection** — no head-of-line blocking at HTTP level
- **Header compression** (HPACK) — reduces overhead
- **Server push**: Server can proactively send resources
- **Stream prioritization**: Client can hint which resources matter most
- **Still over TCP** — suffers from TCP-level head-of-line blocking

### HTTP/3
- Built on **QUIC** (UDP-based) instead of TCP
- **Eliminates TCP head-of-line blocking** — lost packets in one stream don't block others
- **0-RTT connection establishment** (vs TCP's 1-RTT + TLS's 1-2 RTT)
- **Built-in encryption** (TLS 1.3 by default)
- **Connection migration**: Survive IP changes (mobile switching from Wi-Fi to cellular)

---

## 7. HTTPS and TLS

### TLS Handshake (TLS 1.3 — 1-RTT)
1. **Client Hello**: Supported cipher suites, TLS version, client random, key share
2. **Server Hello**: Chosen cipher suite, server random, key share, certificate
3. **Client verifies** server certificate via CA chain
4. **Both derive session keys** from shared secret (ECDHE key exchange)
5. **Encrypted communication** begins

**Key concepts**:
- **Symmetric encryption** (AES-256-GCM) for data — fast
- **Asymmetric encryption** (RSA/ECDSA) for key exchange and authentication — slow, used only initially
- **Certificate Authority (CA)**: Trusted third party that signs certificates
- **Certificate pinning**: App hardcodes expected certificate to prevent MITM
- **Perfect Forward Secrecy (PFS)**: Ephemeral keys ensure past sessions can't be decrypted if long-term key is compromised

---

## 8. IP Addressing

### IPv4
- **32-bit** address → ~4.3 billion addresses (exhausted)
- Format: `192.168.1.1` (dotted decimal, 4 octets)
- **Private ranges**: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- **Loopback**: 127.0.0.1

### IPv6
- **128-bit** address → 3.4 × 10³⁸ addresses
- Format: `2001:0db8:85a3:0000:0000:8a2e:0370:7334`
- **No NAT needed** — enough addresses for every device
- **Built-in IPsec**, auto-configuration (SLAAC)

### Subnetting and CIDR
- **CIDR notation**: `192.168.1.0/24` — the /24 means 24 bits for network, 8 bits for hosts
- **Subnet mask**: /24 → 255.255.255.0 → 2⁸ - 2 = **254 usable hosts**
- **Formula**: Usable hosts = 2^(32 - prefix) - 2 (subtract network and broadcast)

| CIDR | Subnet Mask | Hosts |
|------|------------|-------|
| /24 | 255.255.255.0 | 254 |
| /25 | 255.255.255.128 | 126 |
| /26 | 255.255.255.192 | 62 |
| /27 | 255.255.255.224 | 30 |
| /28 | 255.255.255.240 | 14 |

**Interview tip**: Practice calculating the network address, broadcast address, and valid host range for a given CIDR block.

---

## 9. Routing Protocols

### RIP (Routing Information Protocol)
- **Distance-vector** algorithm (Bellman-Ford)
- Metric: **hop count** (max 15 hops, 16 = unreachable)
- Updates every 30 seconds — slow convergence
- **Use case**: Small networks only

### OSPF (Open Shortest Path First)
- **Link-state** algorithm (Dijkstra's)
- Uses **areas** for hierarchy (Area 0 is the backbone)
- Fast convergence, supports VLSM and CIDR
- Metric: **cost** (based on bandwidth)
- **Use case**: Enterprise/campus networks

### BGP (Border Gateway Protocol)
- **Path-vector** protocol — the internet's routing protocol
- Routes between **autonomous systems** (ISPs, large organizations)
- Uses TCP (port 179), policy-based routing decisions
- **eBGP**: Between different AS. **iBGP**: Within same AS
- **Use case**: Internet backbone routing

---

## 10. NAT (Network Address Translation)

Translates private IP addresses to public IPs for internet access.

**Types**:
- **Static NAT**: 1-to-1 mapping (private → public)
- **Dynamic NAT**: Pool of public IPs assigned on demand
- **PAT (Port Address Translation / NAT Overload)**: Many private IPs share one public IP using different port numbers — most common for home routers

**Why**: IPv4 address conservation. Multiple devices share one public IP.

**Limitations**: Breaks end-to-end connectivity, complicates P2P communication, issues with some protocols (FTP, SIP).

---

## 11. Load Balancing

### L4 (Transport Layer) Load Balancing
- Routes based on **IP address and port** (TCP/UDP)
- Faster — doesn't inspect packet content
- Algorithms: Round Robin, Least Connections, IP Hash

### L7 (Application Layer) Load Balancing
- Routes based on **HTTP headers, URL path, cookies, content**
- Can make intelligent routing decisions (send /api to API servers, /static to CDN)
- SSL termination, content-based routing, A/B testing

### Load Balancing Algorithms
| Algorithm | Description | Best For |
|-----------|-------------|----------|
| **Round Robin** | Rotate through servers sequentially | Equal-capacity servers |
| **Weighted Round Robin** | Assign more traffic to stronger servers | Mixed-capacity servers |
| **Least Connections** | Route to server with fewest active connections | Varying request durations |
| **IP Hash** | Hash client IP to same server | Session affinity |
| **Least Response Time** | Route to fastest server | Latency-sensitive apps |
| **Random** | Random selection | Simple load distribution |

### Health Checks
- **Active**: Load balancer pings servers periodically (HTTP 200 check)
- **Passive**: Monitor response codes and latency from real traffic
- Unhealthy servers are removed from the pool and restored when healthy

---

## 12. CDNs (Content Delivery Networks)

**Purpose**: Serve content from geographically closest **edge server** to reduce latency.

**How it works**:
1. User requests `static.example.com/image.jpg`
2. DNS resolves to nearest CDN edge server (anycast or geo-DNS)
3. Edge server checks cache: **hit** → return immediately; **miss** → fetch from origin, cache, then serve
4. Subsequent requests served from cache until TTL expires

**What CDNs cache**: Static assets (images, CSS, JS, videos), sometimes dynamic content with short TTLs.

**Benefits**: Lower latency, reduced origin load, DDoS mitigation, better availability.

**Key providers**: Cloudflare, AWS CloudFront, Akamai, Fastly.

**Cache invalidation strategies**: TTL expiry, purge API, versioned URLs (cache busting via query strings or file hashes).

---

## 13. WebSockets vs Polling vs SSE

### Short Polling
- Client repeatedly sends HTTP requests at intervals
- Simple to implement; wasteful if no updates
- **Use case**: Simple dashboards with infrequent updates

### Long Polling
- Client sends request, server holds it open until data is available or timeout
- More efficient than short polling, but still has HTTP overhead per update
- **Use case**: Chat applications (before WebSockets)

### Server-Sent Events (SSE)
- **Unidirectional**: Server → Client only
- Built on HTTP (text/event-stream), auto-reconnection
- **Use case**: Live feeds, notifications, stock tickers

### WebSockets
- **Full-duplex** bidirectional communication over a single TCP connection
- Starts with HTTP upgrade handshake, then switches to WS protocol
- Low latency, low overhead (2-byte frame header vs HTTP headers)
- **Use case**: Real-time chat, gaming, collaborative editing, live trading

| Feature | Polling | Long Polling | SSE | WebSocket |
|---------|---------|--------------|-----|-----------|
| Direction | Client → Server | Client → Server | Server → Client | Bidirectional |
| Overhead | High | Medium | Low | Very Low |
| Latency | High | Medium | Low | Very Low |
| Complexity | Simple | Moderate | Simple | Moderate |

---

## 14. REST vs gRPC

### REST (Representational State Transfer)
- Uses **HTTP/1.1 or HTTP/2** with JSON payloads
- Human-readable, easy to debug
- Stateless, resource-oriented (CRUD → GET/POST/PUT/DELETE)
- Wide ecosystem, browser-native
- **Use case**: Public APIs, web services, CRUD applications

### gRPC (Google Remote Procedure Call)
- Uses **HTTP/2** with **Protocol Buffers** (binary serialization)
- Much smaller payload size and faster serialization than JSON
- **Strongly typed** via `.proto` schema definitions
- Supports **streaming**: unary, server-stream, client-stream, bidirectional
- Code generation in 10+ languages
- **Use case**: Microservice-to-microservice communication, low-latency internal APIs

| Feature | REST | gRPC |
|---------|------|------|
| Protocol | HTTP/1.1, HTTP/2 | HTTP/2 |
| Format | JSON (text) | Protobuf (binary) |
| Contract | OpenAPI / Swagger (optional) | .proto file (required) |
| Streaming | No (workarounds exist) | Native bidirectional |
| Browser support | Native | Needs gRPC-Web proxy |
| Performance | Good | Excellent |

---

## 15. Network Security

### Firewalls
- **Packet-filtering**: Rules based on IP, port, protocol (L3/L4)
- **Stateful**: Tracks connection state (SYN, ESTABLISHED, etc.)
- **Application-layer (WAF)**: Inspects HTTP content (L7), blocks SQL injection, XSS
- **Next-Gen (NGFW)**: Combines all above + deep packet inspection, IDS/IPS

### VPN (Virtual Private Network)
- Creates an **encrypted tunnel** over public internet
- **Types**: Site-to-site (office-to-office), remote access (user-to-office)
- **Protocols**: IPsec (L3), OpenVPN (SSL/TLS), WireGuard (modern, fast)
- **Split tunneling**: Only route corporate traffic through VPN, internet traffic goes direct

### DMZ (Demilitarized Zone)
- Network segment between external (internet) and internal (private) networks
- Hosts public-facing services (web servers, mail servers, DNS)
- **Architecture**: Internet → Firewall → DMZ → Firewall → Internal Network
- If DMZ is compromised, internal network remains protected

### Additional Security Concepts
- **IDS (Intrusion Detection System)**: Monitors traffic, alerts on suspicious activity
- **IPS (Intrusion Prevention System)**: Monitors AND blocks threats inline
- **DDoS mitigation**: Rate limiting, traffic scrubbing, CDN absorption, anycast routing
- **Zero Trust Architecture**: "Never trust, always verify" — authenticate every request regardless of network location

---

## 16. Socket Programming Basics

```python
# TCP Server
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8080))
server.listen(5)
print("Server listening on port 8080")

conn, addr = server.accept()
print(f"Connection from {addr}")
data = conn.recv(1024)
conn.send(b"Hello from server!")
conn.close()
server.close()
```

```python
# TCP Client
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 8080))
client.send(b"Hello from client!")
response = client.recv(1024)
print(f"Server response: {response.decode()}")
client.close()
```

```python
# UDP (connectionless)
import socket

# Server
udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server.bind(('0.0.0.0', 9090))
data, addr = udp_server.recvfrom(1024)
udp_server.sendto(b"ACK", addr)

# Client
udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_client.sendto(b"ping", ('127.0.0.1', 9090))
response, _ = udp_client.recvfrom(1024)
```

**Key concepts**: `AF_INET` = IPv4, `SOCK_STREAM` = TCP, `SOCK_DGRAM` = UDP. Non-blocking sockets use `select()`, `poll()`, or `asyncio`.

---

## 17. Network Troubleshooting Tools

### ping
Tests reachability and round-trip time using ICMP echo requests.
```bash
ping -c 4 google.com          # Send 4 packets
ping -i 0.5 google.com        # 0.5 second interval
```
**Diagnoses**: Host unreachable, packet loss, latency issues.

### traceroute (tracert on Windows)
Shows each hop between source and destination.
```bash
traceroute google.com
traceroute -T google.com       # Use TCP instead of UDP
```
**Diagnoses**: Where packets are being dropped, routing loops, latency at specific hops.

### netstat / ss
Display network connections, listening ports, routing tables.
```bash
netstat -tlnp                  # TCP listening ports with process
ss -tlnp                       # Modern replacement for netstat
ss -s                          # Summary statistics
```
**Diagnoses**: Which services are listening, connection states, port conflicts.

### tcpdump
Capture and analyze network packets from the command line.
```bash
tcpdump -i eth0 port 80                     # Capture HTTP traffic
tcpdump -i any host 192.168.1.1             # Traffic to/from specific host
tcpdump -i eth0 -w capture.pcap             # Save to file for Wireshark
tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'  # SYN packets only
```
**Diagnoses**: What's actually on the wire — invaluable for debugging protocol issues.

### Wireshark
GUI packet analyzer — reads pcap files from tcpdump.
- **Display filters**: `http.request.method == "GET"`, `tcp.port == 443`, `dns`
- **Follow TCP stream**: Right-click a packet → Follow → TCP Stream
- **Diagnoses**: TLS handshake failures, malformed packets, application-layer issues

### Additional Tools
```bash
nslookup example.com           # DNS lookup (simple)
dig example.com +trace         # DNS lookup (detailed, shows resolution chain)
curl -v https://example.com    # HTTP request with verbose output
mtr google.com                 # Combines ping + traceroute (continuous)
nmap -sT 192.168.1.0/24       # Port scanning (authorized use only)
arp -a                         # ARP table (IP-to-MAC mappings)
ip route show                  # Routing table
iftop                          # Real-time bandwidth monitoring
```

---

## 18. Common Interview Questions

1. **"What happens when you type google.com in a browser?"** → DNS resolution → TCP 3-way handshake → TLS handshake → HTTP GET request → server processes → HTTP response → browser renders HTML/CSS/JS → requests sub-resources.

2. **"TCP vs UDP — when would you choose each?"** → TCP for reliable delivery (web, email, file transfer). UDP for speed with loss tolerance (video, gaming, DNS, VoIP).

3. **"Explain the difference between L4 and L7 load balancing."** → L4 routes by IP/port (fast, protocol-agnostic). L7 routes by HTTP content (smart, can do path-based routing, SSL termination).

4. **"How does HTTPS protect data?"** → TLS handshake establishes encrypted channel. Asymmetric crypto for key exchange, symmetric crypto for data. Certificate verifies server identity.

5. **"What is the difference between HTTP/1.1, HTTP/2, and HTTP/3?"** → HTTP/1.1: text-based, one request per connection. HTTP/2: binary, multiplexed over single TCP. HTTP/3: QUIC/UDP, eliminates TCP head-of-line blocking, 0-RTT.

6. **"How would you debug a service that's not responding?"** → ping (reachability) → traceroute (routing) → curl (HTTP level) → netstat/ss (is it listening?) → tcpdump (what's happening on the wire) → check logs → check DNS → check firewall rules.

7. **"Explain how a CDN works."** → Content cached on edge servers globally. DNS directs users to nearest edge. Cache hit serves immediately. Cache miss fetches from origin, caches, then serves. Reduces latency and origin load.

8. **"What is NAT and why is it used?"** → Translates private IPs to public IPs. Conserves IPv4 addresses. PAT allows many devices to share one public IP using port numbers.

9. **"Explain the OSI model."** → 7 layers from physical to application. Each layer adds headers (encapsulation). Physical = bits, Data Link = frames, Network = packets, Transport = segments, Session/Presentation/Application = data.

10. **"WebSocket vs REST for real-time features?"** → REST is request-response (client initiates). WebSocket is persistent, bidirectional, low-latency. Use WebSocket for real-time features (chat, live updates). Use REST for CRUD operations and stateless APIs.
