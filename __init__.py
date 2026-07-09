# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import threading
import time
from typing import List, TYPE_CHECKING, override
from xml.etree import ElementTree

from PySide6 import QtCore

from vjoy.vjoy import VJoyProxy

from gremlin import device_initialization, error, event_handler, signal, util
from gremlin.base_classes import (
    AbstractActionData,
    AbstractFunctor,
    UserFeedback,
    Value,
)
from gremlin.profile import Library
from gremlin.types import ActionProperty, InputType, PropertyType
from gremlin.ui.action_model import ActionModel, SequenceIndex

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


def gear_to_button(gear: int, reverse_enabled: bool) -> int | None:
    """Maps an internal gear number to the single vJoy button that should be
    held down for that gear:

        Reverse (-1) -> Button 1
        Neutral (0)  -> no button held
        Gear 1..6    -> Button 2..7

    Returns None if no button should be held.
    """
    if gear == -1:
        return 1 if reverse_enabled else None
    if gear == 0:
        return None
    return gear + 1


class VirtualHShifterFunctor(AbstractFunctor):
    """Runtime logic. One instance exists per (action, physical input)
    combination. Gear state is shared across instances via a class-level table.
    """
    _state: dict[int, dict] = {}
    _lock = threading.Lock()

    def __init__(self, action: VirtualHShifterData) -> None:
        super().__init__(action)

    def _get_state(self) -> dict:
        vid = self.data.output_vjoy_id
        with VirtualHShifterFunctor._lock:
            if vid not in VirtualHShifterFunctor._state:
                VirtualHShifterFunctor._state[vid] = {
                    "gear": 0,
                    "button": None,
                    "last_shift": 0.0,
                }
            return VirtualHShifterFunctor._state[vid]

    def _clutch_engaged(self) -> bool:
        cid = self.data.clutch_vjoy_id
        aid = self.data.clutch_axis_id
        if cid is None or aid is None:
            return False
        try:
            raw = VJoyProxy()[cid].axis(aid).value  
        except error.VJoyError:
            return False
        fraction = (raw + 1.0) / 2.0
        return fraction >= self.data.clutch_threshold

    @override
    def __call__(
            self,
            event: event_handler.Event,
            value: Value,
            properties: list[ActionProperty] = []
    ) -> None:
        
        if not self._should_execute(value):
            return

        if not self._clutch_engaged():
            return

        state = self._get_state()

        with VirtualHShifterFunctor._lock:
            now = time.time()
            debounce_s = self.data.debounce_ms / 1000.0
            if (now - state["last_shift"]) < debounce_s:
                return

            min_gear = -1 if self.data.reverse_enabled else 0
            max_gear = self.data.max_gear
            old_gear = state["gear"]

            if self.data.direction == "up":
                new_gear = min(old_gear + 1, max_gear)
            else:
                new_gear = max(old_gear - 1, min_gear)

            if new_gear == old_gear:
                return  

            old_button = gear_to_button(old_gear, self.data.reverse_enabled)
            new_button = gear_to_button(new_gear, self.data.reverse_enabled)

            try:
                vjoy_out = VJoyProxy()[self.data.output_vjoy_id]
                
                
                if old_button is not None and old_button != new_button:
                    vjoy_out.button(old_button).is_pressed = False
                    
                time.sleep(0.04)
                
                if new_button is not None:
                    vjoy_out.button(new_button).is_pressed = True
                    
            except error.VJoyError as e:
                import logging
                logging.getLogger("event").error(
                    f"Virtual H-Shifter: failed to update vJoy button: {e}"
                )
                return

            state["gear"] = new_gear
            state["button"] = new_button
            state["last_shift"] = time.time()


class VirtualHShifterModel(ActionModel):

    directionChanged = QtCore.Signal()
    clutchVjoyIdChanged = QtCore.Signal()
    clutchAxisIdChanged = QtCore.Signal()
    clutchThresholdChanged = QtCore.Signal()
    outputVjoyIdChanged = QtCore.Signal()
    maxGearChanged = QtCore.Signal()
    reverseEnabledChanged = QtCore.Signal()
    debounceMsChanged = QtCore.Signal()

    def __init__(
            self,
            data: AbstractActionData,
            binding_model: InputItemBindingModel,
            action_index: SequenceIndex,
            parent_index: SequenceIndex,
            parent: QtCore.QObject
    ) -> None:
        super().__init__(data, binding_model, action_index, parent_index, parent)

    def _qml_path_impl(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        qml_path = os.path.join(current_dir, "VirtualHShifterAction.qml")
        return QtCore.QUrl.fromLocalFile(qml_path).toString()

    def _action_behavior(self) -> str:
        return self._binding_model.get_action_model_by_sidx(
            self._parent_sequence_index.index
        ).actionBehavior

    def _get_direction(self) -> str:
        return self._data.direction

    def _set_direction(self, value: str) -> None:
        if value != self._data.direction:
            self._data.direction = value
            self.directionChanged.emit()

    direction = QtCore.Property(
        str, fget=_get_direction, fset=_set_direction, notify=directionChanged
    )

    def _get_clutch_vjoy_id(self) -> int:
        return self._data.clutch_vjoy_id if self._data.clutch_vjoy_id is not None else -1

    def _set_clutch_vjoy_id(self, value: int) -> None:
        if value != self._data.clutch_vjoy_id:
            self._data.clutch_vjoy_id = value
            self.clutchVjoyIdChanged.emit()
            signal.signal.inputItemChanged.emit(
                self._binding_model.parent().enumeration_index
            )

    clutchVjoyId = QtCore.Property(
        int, fget=_get_clutch_vjoy_id, fset=_set_clutch_vjoy_id,
        notify=clutchVjoyIdChanged
    )

    def _get_clutch_axis_id(self) -> int:
        return self._data.clutch_axis_id if self._data.clutch_axis_id is not None else -1

    def _set_clutch_axis_id(self, value: int) -> None:
        if value != self._data.clutch_axis_id:
            self._data.clutch_axis_id = value
            self.clutchAxisIdChanged.emit()

    clutchAxisId = QtCore.Property(
        int, fget=_get_clutch_axis_id, fset=_set_clutch_axis_id,
        notify=clutchAxisIdChanged
    )

    def _get_clutch_threshold_percent(self) -> int:
        return round(self._data.clutch_threshold * 100)

    def _set_clutch_threshold_percent(self, value: int) -> None:
        new_value = value / 100.0
        if new_value != self._data.clutch_threshold:
            self._data.clutch_threshold = new_value
            self.clutchThresholdChanged.emit()

    clutchThresholdPercent = QtCore.Property(
        int, fget=_get_clutch_threshold_percent, fset=_set_clutch_threshold_percent,
        notify=clutchThresholdChanged
    )

    def _get_output_vjoy_id(self) -> int:
        return self._data.output_vjoy_id if self._data.output_vjoy_id is not None else -1

    def _set_output_vjoy_id(self, value: int) -> None:
        if value != self._data.output_vjoy_id:
            self._data.output_vjoy_id = value
            self.outputVjoyIdChanged.emit()
            signal.signal.inputItemChanged.emit(
                self._binding_model.parent().enumeration_index
            )

    outputVjoyId = QtCore.Property(
        int, fget=_get_output_vjoy_id, fset=_set_output_vjoy_id,
        notify=outputVjoyIdChanged
    )

    def _get_max_gear(self) -> int:
        return self._data.max_gear

    def _set_max_gear(self, value: int) -> None:
        if value != self._data.max_gear:
            self._data.max_gear = value
            self.maxGearChanged.emit()

    maxGear = QtCore.Property(
        int, fget=_get_max_gear, fset=_set_max_gear, notify=maxGearChanged
    )

    def _get_reverse_enabled(self) -> bool:
        return self._data.reverse_enabled

    def _set_reverse_enabled(self, value: bool) -> None:
        if value != self._data.reverse_enabled:
            self._data.reverse_enabled = value
            self.reverseEnabledChanged.emit()

    reverseEnabled = QtCore.Property(
        bool, fget=_get_reverse_enabled, fset=_set_reverse_enabled,
        notify=reverseEnabledChanged
    )

    def _get_debounce_ms(self) -> int:
        return self._data.debounce_ms

    def _set_debounce_ms(self, value: int) -> None:
        if value != self._data.debounce_ms:
            self._data.debounce_ms = value
            self.debounceMsChanged.emit()

    debounceMs = QtCore.Property(
        int, fget=_get_debounce_ms, fset=_set_debounce_ms, notify=debounceMsChanged
    )


class VirtualHShifterData(AbstractActionData):

    version = 1
    name = "Virtual H-Shifter"
    tag = "virtual-hshifter"
    icon = "\uF3F6"  

    functor = VirtualHShifterFunctor
    model = VirtualHShifterModel

    properties = (
        ActionProperty.ActivateOnPress,
    )
    input_types = (
        InputType.JoystickButton,
    )

    def __init__(
            self,
            behavior_type: InputType = InputType.JoystickButton
    ) -> None:
        super().__init__(behavior_type)

        devices = device_initialization.output_vjoy_devices()
        default_vjoy_id = devices[0].vjoy_id if devices else None
        default_axis_id = None
        if devices and devices[0].axis_map:
            default_axis_id = devices[0].axis_map[0].axis_index

        self.direction: str = "up"
        self.clutch_vjoy_id: int | None = default_vjoy_id
        self.clutch_axis_id: int | None = default_axis_id
        self.clutch_threshold: float = 0.80
        self.output_vjoy_id: int | None = default_vjoy_id
        self.max_gear: int = 6
        self.reverse_enabled: bool = True
        self.debounce_ms: int = 150

    @classmethod
    @override
    def can_create(cls) -> bool:
        return len(device_initialization.output_vjoy_devices()) > 0

    @override
    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)
        self.direction = util.read_property(
            node, "direction", PropertyType.String
        )
        self.clutch_vjoy_id = util.read_property(
            node, "clutch-vjoy-id", PropertyType.Int
        )
        self.clutch_axis_id = util.read_property(
            node, "clutch-axis-id", PropertyType.Int
        )
        self.clutch_threshold = util.read_property(
            node, "clutch-threshold", PropertyType.Float
        )
        self.output_vjoy_id = util.read_property(
            node, "output-vjoy-id", PropertyType.Int
        )
        self.max_gear = util.read_property(
            node, "max-gear", PropertyType.Int
        )
        self.reverse_enabled = util.read_property(
            node, "reverse-enabled", PropertyType.Bool
        )
        self.debounce_ms = util.read_property(
            node, "debounce-ms", PropertyType.Int
        )

    @override
    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(VirtualHShifterData.tag, self._id)
        node.append(util.create_property_node(
            "direction", self.direction, PropertyType.String
        ))
        node.append(util.create_property_node(
            "clutch-vjoy-id", self.clutch_vjoy_id or 0, PropertyType.Int
        ))
        node.append(util.create_property_node(
            "clutch-axis-id", self.clutch_axis_id or 0, PropertyType.Int
        ))
        node.append(util.create_property_node(
            "clutch-threshold", self.clutch_threshold, PropertyType.Float
        ))
        node.append(util.create_property_node(
            "output-vjoy-id", self.output_vjoy_id or 0, PropertyType.Int
        ))
        node.append(util.create_property_node(
            "max-gear", self.max_gear, PropertyType.Int
        ))
        node.append(util.create_property_node(
            "reverse-enabled", self.reverse_enabled, PropertyType.Bool
        ))
        node.append(util.create_property_node(
            "debounce-ms", self.debounce_ms, PropertyType.Int
        ))
        return node

    @override
    def user_feedback(self) -> List[UserFeedback]:
        feedback = []
        if not self.clutch_vjoy_id or not self.clutch_axis_id:
            feedback.append(UserFeedback(
                UserFeedback.FeedbackType.Error,
                "Virtual H-Shifter: no clutch axis selected."
            ))
        if not self.output_vjoy_id:
            feedback.append(UserFeedback(
                UserFeedback.FeedbackType.Error,
                "Virtual H-Shifter: no output vJoy device selected."
            ))
        else:
            devices = {d.vjoy_id: d for d in device_initialization.vjoy_devices()}
            dev = devices.get(self.output_vjoy_id)
            needed = self.max_gear + 1  
            if dev is not None and dev.button_count < needed:
                feedback.append(UserFeedback(
                    UserFeedback.FeedbackType.Warning,
                    f"Virtual H-Shifter: output device only has "
                    f"{dev.button_count} buttons, needs at least {needed}."
                ))
        return feedback

    @override
    def _valid_selectors(self) -> List[str]:
        return []

    @override
    def _get_container(self, selector: str) -> List[AbstractActionData]:
        raise error.GremlinError(f"{self.name}: has no containers")

    @override
    def _handle_behavior_change(
        self,
        old_behavior: InputType,
        new_behavior: InputType
    ) -> None:
        pass


create = VirtualHShifterData
