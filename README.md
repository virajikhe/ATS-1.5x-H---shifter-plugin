# ATS-1.5x-H---shifter-plugin
A custom Joystick Gremlin plugin that emulates a virtual H-pattern gearbox using vJoy, enabling realistic clutch-based manual shifting in American Truck Simulator with a standard game controller.

Why this project?

ATS provides two controller options:

Sequential Shifting – Easy to use, but it doesn't recreate the experience of a real manual transmission.

H-Shifter Mode – Designed for dedicated H-pattern hardware and expects six independent gear positions plus reverse.

Since a standard controller doesn't have enough buttons to represent every gear position, this project was created to bridge that gap entirely through software.

Instead of dedicating one button to each gear, this plugin maintains an internal gear state and converts simple sequential controller inputs into persistent virtual H-shifter positions.

Features:

🚚 Virtual H-pattern gearbox

🎮 Uses only a standard controller

🔧 Python plugin for Joystick Gremlin

🎯 vJoy output for DirectInput compatibility

🧠 Persistent gear memory

🦶 Clutch interlock before shifting

⬆️ Shift Up / ⬇️ Shift Down controls

↩️ Reverse gear support

⚙️ Configurable maximum gears

🔄 Real-time virtual button mapping


Controller Layout:

Control	Function

LT	Clutch
RT	Accelerator
LB	Shift Down
RB	Shift Up


How it works:

The plugin continuously tracks the currently selected gear.

When the clutch is engaged:

RB increments the gear.

LB decrements the gear.

The plugin updates its internal gear state.

The selected gear is translated into a corresponding vJoy button, allowing games to interpret it as a virtual H-shifter position.


Technologies Used:

Python
Joystick Gremlin Ex
vJoy
DirectInput
State Machine Design
Virtual HID Emulation


Learning Outcomes:

This project involved:

Understanding the Joystick Gremlin plugin architecture

Working with the vJoy API

Designing a gear-state machine

Managing virtual HID inputs

Handling controller event processing

Debugging input timing and synchronisation 

This project demonstrates how software can overcome hardware limitations by emulating dedicated input devices through intelligent controller mapping and virtual device programming.
