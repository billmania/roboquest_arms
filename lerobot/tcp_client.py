#!/usr/bin/env python3
import socket
import pickle

def create_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    host = '192.168.0.10'
    port = 8888

    try:
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")

        object_count = 0
        while True:
            length_bytes = client_socket.recv(4)
            if not length_bytes:
                print("Connection closed by server")
                break

            data_length = int.from_bytes(length_bytes, byteorder='big')

            serialized_data = b''
            while len(serialized_data) < data_length:
                chunk = client_socket.recv(data_length - len(serialized_data))
                if not chunk:
                    print("Connection lost while receiving data")
                    return
                serialized_data += chunk

            received_object = pickle.loads(serialized_data)

            object_count += 1
            print(f"Received object {object_count}: {received_object}")
            print(f"Object type: {type(received_object)}")

            if isinstance(received_object, dict):
                print(f"  Dictionary keys: {list(received_object.keys())}")
            elif isinstance(received_object, list):
                print(f"  List length: {len(received_object)}")
            elif isinstance(received_object, tuple):
                print(f"  Tuple length: {len(received_object)}")

            print("-" * 50)

        print(f"Total objects received: {object_count}")

    except ConnectionRefusedError:
        print("Could not connect to server. Make sure the server is running.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    create_client()
