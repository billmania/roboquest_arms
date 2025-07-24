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

"""Script to manage the follower, reading actions from a TCP socket."""

import pickle
import socket
import time
from dataclasses import dataclass, field
from os import environ
from pathlib import Path

from lerobot.common.robots import (
    Robot,
    RobotConfig,
    make_robot_from_config
)


@dataclass
class Robot_Config:
    """Make config for a follower."""

    type: str = 'so101_follower'  # noqa: A003
    port: str = '/dev/arm_follow'
    id: str = 'arm_follow'  # noqa: A003
    socket_ip: str = environ['LEADER_IP']
    socket_port: int = int(environ['LEADER_PORT'])
    calibration_dir: Path | None = Path(
        '/root/.cache/huggingface/lerobot/calibration/robots/so101_follower'
    )
    use_degrees: bool = False
    cameras: dict = field(default_factory=dict)
    disable_torque_on_disconnect: bool = True
    max_relative_target: int = None


server = None


@dataclass
class TeleoperateConfig:
    """Manage the configuration."""

    robot: RobotConfig
    # Limit the maximum frames per second.
    fps: int = 60
    teleop_time_s: float | None = None
    # Display all cameras on screen
    display_data: bool = False


def setup_socket(server_address: str, server_port: int):
    """Create a socket for communication with the server."""
    tries = 100
    while tries:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server_address, server_port))
            return server_socket

        except Exception:
            time.sleep(5)
            tries -= 1


def teleop_loop(
    robot: Robot,
    fps: int,
    display_data: bool = False,
    duration: float | None = None,
    server_address: str = '0.0.0.0',
    server_port: int = 8888
):
    """Loop through the follower actions."""
    global server

    while True:
        print(f'Connecting to server at {server_address} on {server_port}')
        server = setup_socket(server_address, server_port)

        while True:
            loop_start = time.perf_counter()

            length_bytes = server.recv(4)
            data_length = int.from_bytes(length_bytes, byteorder='big')

            serialized_data = b''
            while len(serialized_data) < data_length:
                try:
                    chunk = server.recv(data_length - len(serialized_data))

                except Exception:
                    server.close()
                    break

                if not chunk:
                    print('Connection lost while receiving data')
                    continue
                serialized_data += chunk

            try:
                action = pickle.loads(serialized_data)

            except Exception:
                server.close()
                break

            robot.send_action(action)
            dt_s = time.perf_counter() - loop_start
            if (1 / fps - dt_s) > 0:
                time.sleep(1 / fps - dt_s)


def teleoperate(robot_config: Robot_Config):
    """Execute the main logic."""
    robot = make_robot_from_config(robot_config)

    robot.connect(calibrate=True)

    try:
        teleop_loop(
            robot,
            60,
            display_data=False,
            duration=0,
            server_address=robot_config.socket_ip,
            server_port=robot_config.socket_port
        )
    except KeyboardInterrupt:
        pass
    finally:
        robot.disconnect()
        if server:
            server.close()


if __name__ == '__main__':
    teleoperate(Robot_Config())
