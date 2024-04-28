import socket
import sys
import threading


class bcolors:
    LIGHTBLUE = '\033[36m'
    RED = '\033[31m'
    ENDC = '\033[0m'


# Constants
UDP_PORT = 13117
SERVER_NAME_LENGTH = 32
MAGIC_COOKIE = b'\xab\xcd\xdc\xba'
SERVER_OFFER_TYPE = b'\x02'


class TriviaClient:
    def __init__(self, team_name):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', UDP_PORT))
        self.tcp_socket = None
        self.team_name = team_name
        self.is_playing = False

    def listen_for_offer(self):
        print(f"{bcolors.LIGHTBLUE}Client started, listening for offer requests...{bcolors.ENDC}")
        while True:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                if data.startswith(MAGIC_COOKIE) and data[4:5] == SERVER_OFFER_TYPE:
                    server_name = data[5:5 + SERVER_NAME_LENGTH].decode().strip('\0')
                    server_port = int.from_bytes(data[37:39], 'big')
                    print(f"{bcolors.LIGHTBLUE}Received offer from server \"{server_name}\" at address {address[0]}, attempting to connect...{bcolors.ENDC}")
                    self.connect_to_server(address[0], server_port)
                    break  # Stop listening for offers after connecting to a server
            except Exception as e:
                print(f"{bcolors.RED}Error: {e}{bcolors.ENDC}")

    def connect_to_server(self, server_ip, server_port):
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((server_ip, server_port))
            self.tcp_socket.sendall((self.team_name + '\n').encode())
            print(f"{bcolors.LIGHTBLUE}Connected to the server successfully!\n{bcolors.ENDC}")
            self.is_playing = True
            receiver = threading.Thread(target=self.receive_messages)
            sender = threading.Thread(target=self.send_user_input)
            receiver.start()
            sender.start()
            receiver.join()
            sender.join()
        except Exception as e:
            print(f"{bcolors.RED}Error connecting to server: {e}{bcolors.ENDC}")
            if self.tcp_socket:
                self.tcp_socket.close()

    def receive_messages(self):
        while self.is_playing:
            try:
                self.tcp_socket.settimeout(1)
                message = self.tcp_socket.recv(1024).decode()
                if message:
                    print(message)
                    expected_message = f"{bcolors.LIGHTBLUE}Not enough players. Game aborted.\nTrying again.\n{bcolors.ENDC}"
                    if message == expected_message:
                        self.is_playing = False
                        self.listen_for_offer()
                else:
                    print(f"{bcolors.LIGHTBLUE}Server disconnected, listening for offer requests...\n{bcolors.ENDC}")
                    self.is_playing = False
                    self.listen_for_offer()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"{bcolors.RED}Error receiving message: {e}{bcolors.ENDC}")
                self.is_playing = False

    def send_user_input(self):
        while self.is_playing:
            try:
                user_input = input().strip()
                self.tcp_socket.sendall(user_input.encode())
            except Exception as e:
                print(f"{bcolors.RED}Error sending user input: {e}{bcolors.ENDC}")
                self.is_playing = False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"{bcolors.RED}Usage: python client.py <team_name>{bcolors.ENDC}")
        sys.exit(1)

    team_name = sys.argv[1]
    client = TriviaClient(team_name)
    client.listen_for_offer()
