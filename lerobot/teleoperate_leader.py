# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script to manage the leader, sending actions via a TCP socket.
"""

import logging
import pickle
import socket
import time
from dataclasses import asdict, dataclass
from pprint import pformat

import draccus
import numpy as np

from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.common.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.common.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    koch_follower,
    make_robot_from_config,
    so100_follower,
    so101_follower,
)
from lerobot.common.teleoperators import (
    Teleoperator,
    TeleoperatorConfig,
    make_teleoperator_from_config,
)
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging, move_cursor_up
from lerobot.common.utils.visualization_utils import _init_rerun

from .common.teleoperators import gamepad, koch_leader, so100_leader, so101_leader  # noqa: F401

client = None


@dataclass
class TeleoperateConfig:
    teleop: TeleoperatorConfig
    robot: RobotConfig
    # Limit the maximum frames per second.
    fps: int = 60
    teleop_time_s: float | None = None
    # Display all cameras on screen
    display_data: bool = False


def setup_socket(server_address: str, server_port: int):
    """Create a socket to the client."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f'Waiting for a client at {server_address} on {server_port}')
    client_socket.bind((server_address, server_port))
    client_socket.listen(1)
    client, address = client_socket.accept()
    print(f'Connected a client from {address}')

    return client

def teleop_loop(
    teleop: Teleoperator,
    robot: Robot,
    fps: int,
    display_data: bool = False,
    duration: float | None = None,
    server_address: str = '0.0.0.0',
    server_port: int = 8888
):
    global client

    display_len = max(len(key) for key in robot.action_features)
    start = time.perf_counter()
    client = setup_socket(server_address, server_port)

    while True:
        loop_start = time.perf_counter()
        action = teleop.get_action()

        """
        if display_data:
            observations = robot.get_observation()
            for one_observation in observations:
                for obs, val in one_observation.items():
                    if isinstance(val, float):
                        rr.log(f"observation_{obs}", rr.Scalar(val))
                    elif isinstance(val, int):
                        rr.log(f"observation_{obs}", rr.Scalar(val))
                    elif isinstance(val, np.ndarray):
                        rr.log(f"observation_{obs}", rr.Image(val), static=True)

        robot.send_action(action)
        """

        action_data = pickle.dumps(action)
        data_length = len(action_data)
        client.send(data_length.to_bytes(4, byteorder='big'))
        client.send(action_data)

        dt_s = time.perf_counter() - loop_start
        busy_wait(1 / fps - dt_s)

        loop_s = time.perf_counter() - loop_start

        print("\n" + "-" * (display_len + 10))
        print(f"{'NAME':<{display_len}} | {'NORM':>7}")
        for motor, value in action.items():
            print(f"{motor:<{display_len}} | {value:>7.2f}")
        print(f"\ntime: {loop_s * 1e3:.2f}ms ({1 / loop_s:.0f} Hz)")

        if duration is not None and time.perf_counter() - start >= duration:
            return

        move_cursor_up(len(action) + 5)


@draccus.wrap()
def teleoperate(cfg: TeleoperateConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name="teleoperation")

    teleop = make_teleoperator_from_config(cfg.teleop)
    robot = make_robot_from_config(cfg.robot)

    teleop.connect()
#    robot.connect()

    try:
        teleop_loop(teleop, robot, cfg.fps, display_data=cfg.display_data, duration=cfg.teleop_time_s)
    except KeyboardInterrupt:
        pass
    finally:
        teleop.disconnect()
        client.close()
#        robot.disconnect()


if __name__ == "__main__":
    teleoperate()
