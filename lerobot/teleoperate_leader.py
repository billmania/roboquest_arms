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

"""Manage the leader, sending actions via a TCP socket."""

import logging
import pickle
import socket
import time
from dataclasses import asdict, dataclass
from pprint import pformat
from select import select

import draccus

from lerobot.common.robots import (  # noqa: F401
    Robot,
    RobotConfig
)
from lerobot.common.teleoperators import (
    Teleoperator,
    TeleoperatorConfig,
    make_teleoperator_from_config,
)
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging, move_cursor_up
from lerobot.common.utils.visualization_utils import _init_rerun

from .common.teleoperators import so101_leader  # noqa: F401

DONT_BLOCK = 0
client = None


@dataclass
class TeleoperateConfig:
    """Provide configuration parameters."""

    teleop: TeleoperatorConfig
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


def get_observations(client):
    """Get the observations from the follower.

    The observations data object is a list of four dictionaries:
        - position
        - load
        - velocity
        - amperage

    The key in each dictionary has the format:
        joint.type
    where "joint" is the name from ('shoulder_pan', 'shoulder_lift',
                                    'elbow_flex', 'wrist_flex',
                                    'wrist_roll', 'gripper')
    where "type" is from the set ('pos', 'load', 'velocity', 'amperage')

    position is a signed float in degrees
    load is an integer in tenth of a percent of the voltage duty cycle
    velocity is a signed integer in steps per second
    amperage is an integer in 6.5 milliamp units
    """
    length_bytes = client.recv(4)
    data_length = int.from_bytes(length_bytes, byteorder='big')
    serialized_data = b''
    while len(serialized_data) < data_length:
        chunk = client.recv(
            data_length - len(serialized_data)
        )
        serialized_data += chunk

    return pickle.loads(serialized_data)


def teleop_loop(
    teleop: Teleoperator,
    fps: int,
    display_data: bool = False,
    duration: float | None = None,
    server_address: str = '0.0.0.0',
    server_port: int = 8888
):
    """Loop through the teleoperation logic."""
    global client
    THROTTLE_COUNT = 10
    observations_throttle = THROTTLE_COUNT

    while True:
        client = setup_socket(server_address, server_port)

        while True:
            loop_start = time.perf_counter()
            action = teleop.get_action()

            action_data = pickle.dumps(action)
            data_length = len(action_data)
            try:
                client.send(data_length.to_bytes(4, byteorder='big'))
                client.send(action_data)

            except Exception as e:
                logging.warning(f'Send to follower failed: {e}')
                client.close()
                break

            observations_to_recv, _, _ = select([client], [], [], DONT_BLOCK)
            if observations_to_recv:
                observations = get_observations(client)
                if observations_throttle <= 0:
                    observations_throttle = THROTTLE_COUNT
                    #
                    # Assume each dictionary contains the same collection
                    # of joints, that there are always four series of
                    # observations, and that the series are always in the
                    # order: (pos, load, velocity, amperage)..
                    # Work through the observations and display the values
                    # grouped by joint instead of by series.
                    #
                    print(
                        f"{' ':13s}  "
                        f"{'deg':^9s} "
                        f"{'load':^6s} "
                        f"{'vel':^5s} "
                        f"{'mAmps':^4s}"
                    )
                    for joint_series in observations[0]:
                        joint = joint_series.split('.')[0]
                        j = joint + '.'
                        print(
                            f'{joint:13s}: '
                            f"{observations[0][j+'pos']:9.3f} "
                            f"{observations[1][j+'load']:6d} "
                            f"{observations[2][j+'velocity']:5d} "
                            f"{observations[3][j+'amperage']:4d} "
                        )
                    move_cursor_up(7)
                else:
                    observations_throttle -= 1

            dt_s = time.perf_counter() - loop_start
            busy_wait(1 / fps - dt_s)


@draccus.wrap()
def teleoperate(cfg: TeleoperateConfig):
    """Run teleoperation."""
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name='teleoperation')

    teleop = make_teleoperator_from_config(cfg.teleop)

    teleop.connect()

    try:
        teleop_loop(
            teleop,
            cfg.fps,
            display_data=cfg.display_data,
            duration=cfg.teleop_time_s
        )

    except KeyboardInterrupt:
        pass

    finally:
        teleop.disconnect()
        client.close()


if __name__ == '__main__':
    teleoperate()
