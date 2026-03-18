import json
from queue import Queue

import main


def build_monitor():
    monitor = main.Monitor(Queue())
    monitor.add_entity_queue("ControlSystem", Queue())
    monitor.add_entity_queue("LightsGPIO", Queue())
    return monitor


def test_modechecker_allows_known_configuration():
    monitor = build_monitor()
    mode = {"direction_1": "red", "direction_2": "green"}
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    assert monitor.authorize_and_route(event) is True


def test_modechecker_blocks_two_greens():
    monitor = build_monitor()
    mode = {"direction_1": "green", "direction_2": "green"}
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters=json.dumps(mode),
    )
    assert monitor.authorize_and_route(event) is False


def test_modechecker_blocks_invalid_json():
    monitor = build_monitor()
    event = main.Event(
        source="ControlSystem",
        destination="LightsGPIO",
        operation="set_mode",
        parameters="{not-json}",
    )
    assert monitor.authorize_and_route(event) is False
