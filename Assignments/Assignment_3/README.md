# ITA0313 - Mobile Computing - Assignment 3 (CO3): Code, Output and Screenshots

Each question folder contains:

| File | Purpose |
|---|---|
| `qN_*.py` | Python program (standard library only) that implements the algorithm(s) of that question |
| `output.txt` | Console output produced by running the program |
| `screenshot_output.png` | Screenshot-style image of the program run in a terminal |
| `screenshot_graph.png` | Graph / topology figure of the results |

| Folder | Question | Program implements |
|---|---|---|
| Q1_Wireless_Mobility | Wireless architecture & mobility | Handoff loss table, Algorithm 1.1 `DecideHandoff` (hysteresis + dwell), delivery ratio, efficiency |
| Q2_Mobile_IP | Mobile IP & mobility management | Agent discovery, Algorithm 2.1 registration with retries, Algorithm 2.2 tunnelling, overhead |
| Q3_Cellular_vs_AdHoc | Cellular vs ad hoc | Algorithm 3.1 `SelectWirelessArchitecture`, failure demo, multi-hop capacity |
| Q4_Mobile_IP_Healthcare | Mobile IP applications (ambulance) | Algorithm 4.1, delay budget, packet delivery, tunnel overhead |
| Q5_DSDV | Proactive routing | DSDV tables before/after link break, sequence numbers, O(N^2) overhead |
| Q6_AODV | Reactive routing | RREQ/RREP/RERR simulation, re-discovery, `SelectRoutingApproach` |
| Q7_Emergency_Network | Emergency network design | AODV zone + Mobile IP gateways + failure handling (Algorithm 7.1) |

## Run
```
python3 Q1_Wireless_Mobility/q1_mobility.py        # same for the other folders
pip install matplotlib pillow
python3 generate_all.py                            # regenerates output.txt + screenshots for all questions
```
Requires Python 3.8+. The programs are simulations written for this report (no NS-2/NS-3 needed); the screenshots are rendered from the real program output.
