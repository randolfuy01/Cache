import socket
import threading
import time
from typing import Tuple, List
import secrets


class Server:
    """
    A simple TCP server that listens for client connections and handles
    basic commands like `PING`, `ECHO`, `SET`, and `GET`.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The port on which the server listens.
        resuable (bool): Whether the server socket is reusable. Default is True.
        store (dict): A dictionary for storing key-value pairs.
        expire (dict): A dictionary for storing key-expiry timestamps.
        lock (threading.Lock): A lock to manage concurrent access to shared resources.
    """

    def __init__(
        self, host: str, port: int, role: str = "master", resuable: bool = True
    ):
        """
        Initializes the server with a specified host, port, and reuse setting.

        Args:
            host (str): The server's hostname or IP address.
            port (int): The port number for the server to bind to.
            resuable (bool): If True, the server socket can be reused. Default is True.
        """
        self.server_socket: socket.socket
        self.host = host
        self.port = port
        self.resuable = resuable
        self.store = {}
        self.expire = {}
        self.lock = threading.Lock()
        self.role = role
        self.master_host = None
        self.master_port = None
        
        '''
        replication attributes to track
        '''
        self.master_replid = self.generate_replid()
        self.master_repl_offset = 0
        self.second_repl_offset = -1
        self.repl_backlog_active = 0
        self.repl_backlog_size = 1048576
        self.repl_backlog_first_byte_offset = 0
        self.repl_backlog_histlen = 0

    def generate_replid(self) -> str:
        """
        Generates a unique replication ID for the master server instance.

        Returns:
            str: A unique 40-character hexadecimal replication ID.
        """
        return secrets.token_hex(20)

    def start_socket(self) -> None:
        """
        Starts the server socket and binds it to the host and port.
        """
        self.server_socket = socket.create_server((self.host, self.port))
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Server started and listening")

    def start_listening(self) -> None:
        """
        Continuously listens for incoming client connections and starts a new thread
        to handle each connection.
        """
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
        """
        Handles a single client connection, processing commands received from the client.

        Args:
            connection (socket.socket): The client socket connection.
            address (Tuple[str, int]): The address of the connected client.
        """
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
                    try:
                        match command:
                            case "ping":
                                response = self.ping()
                            case "echo":
                                response = self.echo(data)
                            case "set":
                                response = self.set(data)
                            case "get":
                                response = self.get(data)
                            case "slaveof":
                                response = self.slave_of(data)
                            case "info":
                                response = self.info()
                            case _:
                                response = b"-Error: Invalid command\r\n"
                    except Exception as e:
                        print(f"Error processing command {command}: {e}")
                        response = b"-Error: command failed\r\n"
                else:
                    response = b"-Error: incomplete command\r\n"

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
                self.master_repl_offset += 1
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

    def clear_key(self, key: str) -> None:
        with self.lock:
            self.store.pop(key, None)
            self.expire.pop(key, None)

    def slave_of(self, data: List[str]) -> bytes:
        if len(data) >= 5 and data[4].lower() == "no" and data[5].lower() == "one":
            self.slave_of_no_one()
            return b"+OK\r\n"
        elif len(data) >= 6:
            self.master_host = data[4]
            self.master_port = int(data[5])
            self.role = "slave"
            return b"+OK\r\n"
        else:
            return b"-Error: SLAVEOF requires a host and port\r\n"

    def slave_of_no_one(self):
        self.master_host = None
        self.master_port = None
        self.role = "master"

    def info(self) -> bytes:
        """
        Provides information about the server, including replication details.

        Returns:
            bytes: The server information formatted for the INFO command.
        """
        response = f"+role:{self.role}\r\n"

        if self.role == "master":
            response += f"connected_slaves:{0}\r\n"
            response += f"master_replid:{self.master_replid}\r\n"
            response += f"master_repl_offset:{self.master_repl_offset}\r\n"
            response += f"second_repl_offset:{self.second_repl_offset}\r\n"
            response += f"repl_backlog_active:{self.repl_backlog_active}\r\n"
            response += f"repl_backlog_size:{self.repl_backlog_size}\r\n"
            response += f"repl_backlog_first_byte_offset:{self.repl_backlog_first_byte_offset}\r\n"
            response += f"repl_backlog_histlen:{self.repl_backlog_histlen}\r\n"

        return bytes(response, "utf-8")
