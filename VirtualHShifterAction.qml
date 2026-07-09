// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only
//
// Virtual H-Shifter action UI.
//
// NOTE: this deliberately avoids importing anything via a relative path
// like "../../qml" (the pattern used by the core/bundled action plugins).
// Those relative imports resolve relative to this file's location, and
// since this is a USER plugin loaded from an arbitrary external directory
// (see gremlin/plugin_manager.py - user plugin folders are added to
// sys.path directly and are not nested under the app's install root), a
// "../../qml" import would point outside the application entirely and
// fail to resolve. Only globally registered QML modules are used here:
// QtQuick/QtQuick.Controls (built-in), and Gremlin.ActionPlugins /
// Gremlin.Device, which are registered by Python via qmlRegisterType and
// are therefore resolvable regardless of where this file lives on disk.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Device

Item {
    id: _root

    property VirtualHShifterModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 8

        // -- Direction --------------------------------------------------
        RowLayout {
            Label { text: "Shift direction on this button:" }

            ComboBox {
                id: _direction

                Layout.minimumWidth: 260

                model: [
                    "Up  (Neutral \u2192 1 \u2192 ... \u2192 6)",
                    "Down  (6 \u2192 ... \u2192 Neutral \u2192 Reverse)"
                ]

                Component.onCompleted: {
                    currentIndex = (_root.action.direction === "down") ? 1 : 0
                }

                onActivated: (index) => {
                    _root.action.direction = (index === 1) ? "down" : "up"
                }
            }
        }

        // -- Clutch source ------------------------------------------------
        Label {
            text: "<b>Clutch input</b> (axis must exceed the threshold to allow a shift)"
        }

        RowLayout {
            spacing: 10

            ComboBox {
                id: _clutchDevice
                Layout.minimumWidth: 180
                Layout.fillWidth: true
                model: _clutchVjoy.vjoyDevices
                onActivated: () => {
                    _clutchVjoy.setState(_clutchDevice.currentText, _clutchAxis.currentText)
                }
            }
            ComboBox {
                id: _clutchAxis
                Layout.minimumWidth: 150
                Layout.fillWidth: true
                model: _clutchVjoy.inputChoices
                onActivated: () => {
                    _clutchVjoy.setState(_clutchDevice.currentText, _clutchAxis.currentText)
                }
            }
        }

        VJoyDevices {
            id: _clutchVjoy
            validTypes: ["axis"]

            onCurrentSelectionChanged: (vjoyId, inputType, inputId) => {
                _root.action.clutchVjoyId = vjoyId
                _root.action.clutchAxisId = inputId
            }
            onCurrentValuesChanged: (vjoy_name, input_name) => {
                _clutchDevice.currentIndex = _clutchDevice.find(vjoy_name)
                _clutchAxis.currentIndex = _clutchAxis.find(input_name)
            }

            Component.onCompleted: {
                setInitialState(_root.action.clutchVjoyId, "axis", _root.action.clutchAxisId)
            }
        }

        RowLayout {
            Label { text: "Clutch threshold:" }

            SpinBox {
                id: _threshold
                from: 0
                to: 100
                stepSize: 5
                value: _root.action.clutchThresholdPercent

                textFromValue: (value, locale) => value + "%"
                valueFromText: (text, locale) => parseInt(text)

                onValueModified: {
                    _root.action.clutchThresholdPercent = value
                }
            }
        }

        // -- Output device --------------------------------------------------
        Label {
            text: "<b>Output vJoy device</b> (must be the same on both the shift-up and shift-down action)"
        }

        RowLayout {
            spacing: 10

            ComboBox {
                id: _outputDevice
                Layout.minimumWidth: 180
                Layout.fillWidth: true
                model: _outputVjoy.vjoyDevices
                onActivated: () => {
                    _outputVjoy.setState(_outputDevice.currentText, _outputInput.currentText)
                }
            }
            // This combo box has to be shown for the device picker's
            // setState() API to work (it needs a paired device+input
            // selection), but the specific button chosen here is not
            // actually used - the functor computes the button per gear
            // itself (Reverse->1, Neutral->none, Gear N->N+2).
            ComboBox {
                id: _outputInput
                Layout.minimumWidth: 150
                Layout.fillWidth: true
                model: _outputVjoy.inputChoices
                onActivated: () => {
                    _outputVjoy.setState(_outputDevice.currentText, _outputInput.currentText)
                }
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font.pointSize: 9
            font.italic: true
            text: "Only the device on the left matters here - the button " +
                  "shown on the right is ignored, the actual button used " +
                  "per gear is computed automatically (Reverse\u2192Button 1, " +
                  "Neutral\u2192none, Gear N\u2192Button N+2)."
        }

        VJoyDevices {
            id: _outputVjoy
            validTypes: ["button"]

            onCurrentSelectionChanged: (vjoyId, inputType, inputId) => {
                _root.action.outputVjoyId = vjoyId
            }
            onCurrentValuesChanged: (vjoy_name, input_name) => {
                _outputDevice.currentIndex = _outputDevice.find(vjoy_name)
                _outputInput.currentIndex = _outputInput.find(input_name)
            }

            Component.onCompleted: {
                // Button 1 is just a placeholder to satisfy the selector;
                // only the device id is actually used by this action.
                setInitialState(_root.action.outputVjoyId, "button", 1)
            }
        }

        // -- Limits ----------------------------------------------------
        RowLayout {
            spacing: 20

            RowLayout {
                Label { text: "Max gear:" }
                SpinBox {
                    id: _maxGear
                    from: 1
                    to: 6
                    value: _root.action.maxGear

                    onValueModified: {
                        _root.action.maxGear = value
                    }
                }
            }

            Switch {
                id: _reverse
                text: "Reverse enabled"
                checked: _root.action.reverseEnabled

                onToggled: {
                    _root.action.reverseEnabled = checked
                }
            }
        }

        // -- Debounce -----------------------------------------------------
        RowLayout {
            Label { text: "Debounce:" }

            SpinBox {
                id: _debounce
                from: 0
                to: 1000
                stepSize: 10
                value: _root.action.debounceMs

                textFromValue: (value, locale) => value + " ms"
                valueFromText: (text, locale) => parseInt(text)

                onValueModified: {
                    _root.action.debounceMs = value
                }
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font.italic: true
            text: "Add this action once on the shift-up button (Direction = Up) " +
                  "and once on the shift-down button (Direction = Down), both " +
                  "pointed at the same output vJoy device."
        }
    }
}
