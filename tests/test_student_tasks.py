import json
import time
import sys
from queue import Queue

import main


def build_monitor():
    monitor = main.Monitor(Queue())
    monitor.add_entity_queue("ControlSystem", Queue())
    monitor.add_entity_queue("LightsGPIO", Queue())
    return monitor


def test_task1_two_greens_blocked():
    monitor = build_monitor()
    mode = {"direction_1": "green", "direction_2": "green"}
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    ok = monitor.authorize_and_route(event)
    assert ok is False, "Реализуйте задание 1: добавьте поддержку двух зелёных в разрешённые режимы"


def test_task2_allow_yellow_blinking():
    monitor = build_monitor()
    mode = {"direction_1": "yellow_blinking", "direction_2": "yellow_blinking"}
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    ok = monitor.authorize_and_route(event)
    assert ok is True, (
        "Реализуйте задание 2: добавьте режим yellow_blinking в политики безопасности"
    )


def test_task3_allow_arrow_sections():
    monitor = build_monitor()
    mode = {
        "direction_1": "green",
        "direction_1_left": "green",
        "direction_1_right": "green",
        "direction_2": "red",
        "direction_2_right": "green",
    }
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    ok = monitor.authorize_and_route(event)
    assert ok is True, (
        "Реализуйте задание 3: добавьте поддержку секций со стрелками в разрешённые режимы"
    )