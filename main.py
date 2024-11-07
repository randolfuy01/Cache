import argparse
from server import Server


def main():
    print("Logs from the server will be displayed here.")

    parse = argparse.ArgumentParser()
    parse.add_argument("--dir")
    parse.add_argument("--dbfilename")
    parse.add_argument("--port")
    args = parse.parse_args()

    port = int(args.port) if args.port else 6379
    
    my_server = Server(host="localhost", port=port, resuable=True)
    
    try:
        my_server.start_socket()
        my_server.start_listening()
    except Exception as e:
        print(f"Error starting the server: {e}")


if __name__ == "__main__":
    main()