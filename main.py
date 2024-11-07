from server import Server


def main():
    print("Logs from the server will be displayed here.")
    my_server = Server(host="localhost", port=6379, resuable=True)

    try:
        my_server.start_socket()
        my_server.start_listening()
    except Exception as e:
        print(f"Error starting the server: {e}")


if __name__ == "__main__":
    main()
