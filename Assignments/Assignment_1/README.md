# ITA0313 - Mobile Computing - Assignment 1 (CO1): Hexagonal Cellular Network - Code, Output and Screenshots

Township 12 km^2, 336 duplex channels, R = 0.5 km, 2 % blocking target, 12 dB minimum SIR.

Each task folder contains:

| File | Purpose |
|---|---|
| `task*.py` | Python program (needs `numpy` and `matplotlib`) |
| `output.txt` | Console output from running the program |
| `screenshot_output.png` | Screenshot-style image of the run in a terminal |
| `screenshot_graph*.png` | Result graphs / plots |

`common/cellular_lib.py` holds the shared functions: hexagon area, cluster size, reuse distance, SIR, recursive Erlang-B,
2 % traffic search, hex-grid generator, cluster colouring and the hexagon sampler.

| Folder | Report tasks | What is implemented |
|---|---|---|
| Task01_02_Strategies | 1, 2 | Iterative (i,j) cluster search with 12 dB test, sectorised reuse, recursive cell splitting, governing parameters |
| Task03_Analytical_Model | 3 | Every formula of section 3: area, cell count, N, D, Q, channels/cell, Erlang-B, SIR (omni and sector) |
| Task04_05_Behaviour_Scaling | 4, 5 | Best/average/worst position, shadowing, blocking per subscriber case, scaling, path-loss sensitivity |
| Task06_07_Cell_Splitting | 6, 7 | Uniform and selective recurrences, closed-form check, minimum rounds, power and handoff trends |
| Task08_09_10_Simulator | 8, 9, 10 | Hex-grid simulator (127 cells), channel colouring, Monte-Carlo SIR with 3-sector antenna and shadowing, Erlang-B calculator, event-driven blocking simulation, theory-vs-simulation table |
| Task11_12_Final_Design_Event | 11, 12 | Hybrid design numbers, alternatives, 25,000-person stadium event analysis and temporary micro-cell plan |

## Run
```
pip install numpy matplotlib pillow
python3 Task08_09_10_Simulator/task08_09_10_simulator.py   # any single program
python3 generate_all.py                                    # regenerate all output.txt and screenshots
```
Simulator settings: seed 2026, 20,000 users per test, shadowing sigma = 6 dB (also run with 0 dB), same seed for every strategy.

## Notes
* The screenshots are rendered from the real program output (not captured from a desktop).
* Cost figures are not computed: the report states that they need local price quotations.
* The report's C0 = 729.41 Erl is 19 x 38.39 (rounded); the unrounded Erlang-B result used here is 729.44 Erl.
