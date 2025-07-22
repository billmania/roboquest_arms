#!/usr/bin/env python3
import socket
import pickle
import time

def create_server():
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    host = '0.0.0.0'
    port = 8888
    server_socket.bind((host, port))

    print(f"Server listening on {host}:{port}")
    server_socket.listen(1)

    client_socket, address = server_socket.accept()
    print(f"Connection from {address}")

    try:
        # Create some Python objects to send
        objects_to_send = [
            {"name": "Alice", "age": 30, "city": "New York"},
            [1, 2, 3, 4, 5],
            ("tuple", "data", 42),
            {"nested": {"level": 2, "items": [10, 20, 30]}},
            "Simple string message"
        ]

        # Send each object
        for i, obj in enumerate(objects_to_send):
            print(f"Sending object {i + 1}: {obj}")

            serialized_data = pickle.dumps(obj)

            data_length = len(serialized_data)
            client_socket.send(data_length.to_bytes(4, byteorder='big'))

            client_socket.send(serialized_data)

            time.sleep(1)

        print("All objects sent!")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        client_socket.close()
        server_socket.close()

if __name__ == "__main__":
    create_server()
