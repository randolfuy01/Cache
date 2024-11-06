import socket
import threading
from typing import Tuple

def main():
    print("Logs from the server will be displayed here.")
    socket: socket.socket = socket.create_server(("localhost", 12345), resuse_port=True)
    print("Connection established.")

    
if __name__ == "__main__":
    main()
