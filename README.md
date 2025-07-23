# roboquest_arms
Control software for robotic arms associated with the Roboquest project

Supports SO101 arms built with FeeTech servoes, with the leader arm connected to a desktop
machine and the follower connected to a Raspberry Pi (or more capable machine with Docker
support). The follower software id deployed via a Docker image.

# Build the rq_arms image for the follower

1. clone the repo
2. cd to the root of the repo
3. docker build -t registry.q4excellence.com:5678/rq_arms -f Dockerfile.roboquest_arms .

# Setup for the leader

1. install miniconda
2. create the virtual environment
3. install the packages
