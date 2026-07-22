# AGH Space Systems – Rocket Software Recruitment Task (Autumn 2025): Automated Rocket Launch and Landing

## Project Description ```rocket_controller.py```

The program **automatically controls the rocket's launch, flight, and landing sequence**.

It communicates with the rocket's onboard system over a TCP network ```(tcp_proxy.py)```, continuously reading sensor data such as **fuel levels, pressure, and altitude**.

Based on these measurements, the controller operates valves, relays, and the ignition system while reacting to changes in the rocket's state in real time.

If any abnormal condition is detected (e.g., excessive pressure or an incorrect valve activation sequence), the program **immediately aborts the mission**.

All operations and events are logged in the ```rocket.log``` file for safety, debugging, and post-flight analysis.

## Running the Project

1. Start the proxy server: ```python tcp_proxy.py```
2. Start the rocket simulator: ```python tcp_simulator.py --verbose```
3. Run the rocket controller: ```python rocket_controller.py```

## How the Program Works

The controller connects to the proxy server and sends command frames to the simulator according to the predefined launch procedure.

It continuously monitors sensor readings in real time.

All operations are logged in the ```rocket.log``` file.

If a fault is detected (e.g., excessive pressure or an incorrect valve activation order), the controller displays a warning message and safely aborts the mission.

The program **successfully** executes the complete rocket mission, including launch, flight, and landing:

<img width="725" height="417" alt="Rocket launch sequence" src="https://github.com/user-attachments/assets/a33c657e-a069-4fb2-9407-242987807c74" />

## Planned Improvements

- Add unit tests
- Optimize the codebase
- Monitor additional in-flight parameters

Additionally:

- Graphical User Interface (GUI) built with NiceGUI
- Automatic failure risk detection and notifications
