# roboquest_arms
Control software for robotic arms associated with the Roboquest project

Supports SO101 arms built with FeeTech servoes, with the leader arm connected to a desktop
machine and the follower connected to a Raspberry Pi (or more capable machine with Docker
support). The follower software id deployed via a Docker image.

# Setup for the follower

1. clone the repo
2. cd to the root of the repo
3. docker build -t registry.q4excellence.com:5678/rq_arms -f Dockerfile.roboquest_arms .

Alternatively:

1. docker pull registry.q4excellence.com:5678/rq_arms

# Run the follower components

In the following command lines, executed on the robot to which
the follower arm is physically connected, replace <FOLLOWER SERIAL PORT>
with the full device file name, usually something like
/dev/ttyACM0.
Replace <IP address of leader> with the IP address where the
leader components are running, something like 192.168.0.12.
Replace <port number of leader> with the port number for the
leader, something like 8888.

```
docker run \
    -it \
    --rm \
    --privileged \
    --network host \
    --ipc host \
    --device <FOLLOWER SERIAL PORT>:/dev/arm_follow \
    -e LEADER_IP='<IP address of leader>' \
    -e LEADER_PORT='<port number of leader>' \
    --name rq_arms \
    registry.q4excellence.com:5678/rq_arms
```

After the Docker container is started, the follower software will
be automatically started.

# Setup for the leader

1. install miniconda
    1. cd ~
    2. wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    3. bash ~/Miniconda3-latest-Linux-x86_64.sh
    4. conda init --all
2. create the virtual environment
    1. conda create -y -n rq_arms python 3.12
3. install the packages
    1. git clone https://github.com/billmania/roboquest_arms.git
    2. cd roboquest_arms
    3. pip install feetech-servo-sdk huggingface-hub pyserial deepdiff numpy draccus

# Run the leader components

```
python -m lerobot.teleoperate_leader \
    --teleop.socket_ip 0.0.0.0 \
    --teleop.socket_port <port number of leader> \
    --teleop.type so101_leader \
    --teleop.port <LEADER SERIAL PORT> \
    --teleop.id arm_lead
```
