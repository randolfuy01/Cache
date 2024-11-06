import socket
import threading
from typing import Tuple

class Server:
    def __init__(self, host: str, port: int, resuable: boolean = True):  
        self.server_socket: socket.socket
        self.host = host
        self.port = port
        self.resuable = resuable
   
    def start_socket(self) -> None:
        self.server_socket = socket.create_server((self.host, self.port), reuse_port = self.resuable)
        print("Connection established")
    
    def start_listening(self) -> None:
        while True:
            try:
                connection: socket.socket
                address: Tuple[str, int]
                connection, address = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(connection, address))
                client_thread.start()
            except Exception as e:
                print(f"Error: {e}")

    def handle_client(self, connection: socket.socket, address: Tuple[str, int]) -> None:
        with connection:
            print(f"Connected by {address}\n")

            while True:
                data: bytes = connection.recv(1024)
                if not data:
                    break
                if "ping" in data.decode().lower():
                    pong: str = "+Pong\r\n"
                    connection.sendall(pong.encode())
                elif "echo" in data.decode().lower():
                    echo: str = data.decode().split("\r\n")[-2]
                    length: int = len(echo)
                    repsonse: str = f"+Echo {length}\r\n{echo}\r\n"
                    connection.sendall(response.encode())
