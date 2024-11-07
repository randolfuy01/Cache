import socket
import threading
import time
from typing import Tuple, List


class Server:
    def __init__(self, host: str, port: int, resuable: bool = True):
        self.server_socket: socket.socket
        self.host = host
        self.port = port
        self.resuable = resuable
        self.store = {}
        self.expire = {}
        self.lock = threading.Lock()

    def start_socket(self) -> None:
        self.server_socket = socket.create_server((self.host, self.port))
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Server started and listening")

    def start_listening(self) -> None:
        while True:
            try:
                connection, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.connection_handler, args=(connection, address)
                )
                client_thread.start()
            except Exception as e:
                print(f"Error: {e}")

    def connection_handler(
        self, connection: socket.socket, address: Tuple[str, int]
    ) -> None:
        with connection:
            print(f"Connected by {address}\n")
            while True:
                data = connection.recv(1024)
                if not data:
                    break
                data = data.decode("utf-8").split("\r\n")
                print(f"Data: {data}")

                if len(data) > 2:
                    command = data[2].lower()
                    if command == "ping":
                        response = self.ping()
                    elif command == "echo":
                        response = self.echo(data)
                    elif command == "set":
                        response = self.set(data)
                    elif command == "get":
                        response = self.get(data)
                    else:
                        response = b"+Invalid command\r\n"
                else:
                    response = b"+Error: incomplete command\r\n"

                connection.sendall(response)

    def ping(self) -> bytes:
        return b"+PONG\r\n"

    def echo(self, data: List[str]) -> bytes:
        response = "\r\n".join(data[3:])
        return bytes(response, "utf-8")

    def set(self, data: List[str]) -> bytes:
        with self.lock:
            if len(data) > 6:
                key = data[4]
                value = data[6]
                self.store[key] = value
                if len(data) >= 11 and data[8].lower() == "px":
                    expiry_time_ms = int(data[10])
                    self.expire[key] = time.time() + (expiry_time_ms / 1000)
                else:
                    self.expire.pop(key, None)
                return b"+OK\r\n"
            else:
                return b"-Error: incomplete set command\r\n"

    def get(self, data: List[str]) -> bytes:
        if len(data) > 4:
            key = data[4]
            with self.lock:
                expiry = self.expire.get(key)
                if expiry and time.time() > expiry:
                    del self.store[key]
                    del self.expire[key]
                    return b"$-1\r\n"

                value = self.store.get(key)
                if value is not None:
                    return bytes(f"${len(value)}\r\n{value}\r\n", "utf-8")
                else:
                    return b"$-1\r\n"
        else:
            return b"-Error: incomplete get command\r\n"

    def clear_key(self, key: str):
        with self.lock:
            self.store.pop(key, None)
            self.expire.pop(key, None)