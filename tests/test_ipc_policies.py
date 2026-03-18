import json
from queue import Queue

import main


def build_monitor():
    monitor = main.Monitor(Queue())
    monitor.add_entity_queue("ControlSystem", Queue())
    monitor.add_entity_queue("LightsGPIO", Queue())
    return monitor


def test_allow_control_to_lights_set_mode():
    monitor = build_monitor()
    mode = {"direction_1": "red", "direction_2": "green"}
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    assert monitor.authorize_and_route(event) is True


def test_block_wrong_operation():
    monitor = build_monitor()
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="get_status",
        parameters="{}",
    )
    assert monitor.authorize_and_route(event) is False


def test_block_unknown_destination():
    monitor = build_monitor()
    mode = {"direction_1": "red", "direction_2": "green"}
    event = main.Event(
        source="ControlSystem",
        destination="UnknownEntity",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    assert monitor.authorize_and_route(event) is False
