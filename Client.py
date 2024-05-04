import socket
import sys
import threading
import random

# List of client names for randomly selecting a team name
clients_names = ['Jessie', 'Thumper', 'Cotton', 'Hazel', 'Clover', 'Marshmallow', 'Binky', 'Willow', 'Peanut',
                 'Poppy', 'Luna', 'Jasper', 'Oliver']

# ANSI escape codes for colors
class bcolors:
    LIGHTBLUE = '\033[36m'
    RED = '\033[31m'
    ENDC = '\033[0m'
    black = '\033[30m'
    red = '\033[31m'
    green = '\033[32m'
    orange = '\033[33m'
    blue = '\033[34m'
    purple = '\033[35m'
    cyan = '\033[36m'
    lightgrey = '\033[37m'
    darkgrey = '\033[90m'
    lightred = '\033[91m'
    lightgreen = '\033[92m'
    yellow = '\033[93m'
    lightblue = '\033[94m'
    pink = '\033[95m'
    lightcyan = '\033[96m'

# Constants
UDP_PORT = 13117
SERVER_NAME_LENGTH = 32
MAGIC_COOKIE = b'\xab\xcd\xdc\xba'
SERVER_OFFER_TYPE = b'\x02'


class TriviaClient:
    def __init__(self, team_name):
        """
        Initialize the TriviaClient object.

        Args:
            team_name (str): The name of the team.
        """
        self.tcp_socket = None
        self.team_name = team_name
        self.is_playing = False

    def listen_for_offer(self):
        """
        Listen for offer requests from servers.
        """
        print(f"{bcolors.LIGHTBLUE}Client started, listening for offer requests...{bcolors.ENDC}")
        while True:
            try:
                # Set up a UDP socket to listen for offers
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.udp_socket.bind(('', UDP_PORT))
                data, address = self.udp_socket.recvfrom(1024)
                # Check if the received data is a valid offer
                if data.startswith(MAGIC_COOKIE) and data[4:5] == SERVER_OFFER_TYPE:
                    server_name = data[5:5 + SERVER_NAME_LENGTH].decode().strip('\0')
                    server_port = int.from_bytes(data[37:39], 'big')
                    print(f"{bcolors.LIGHTBLUE}Received offer from server \"{server_name}\" at address {address[0]}, attempting to connect...{bcolors.ENDC}")
                    self.connect_to_server(address[0], server_port)
                    break  # Stop listening for offers after connecting to a server
            except Exception as e:
                print(f"{bcolors.RED}Error: {e}{bcolors.ENDC}")

    def connect_to_server(self, server_ip, server_port):
        """
        Connect to the server.

        Args:
            server_ip (str): IP address of the server.
            server_port (int): Port number of the server.
        """
        try:
            # Set up a TCP socket to connect to the server
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((server_ip, server_port))
            # Send team name to the server
            self.tcp_socket.sendall((self.team_name + '\n').encode())
            print(f"{bcolors.LIGHTBLUE}Connected to the server successfully!\n{bcolors.ENDC}")
            self.is_playing = True
            # Start separate threads for receiving and sending messages
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
        """
        Receive messages from the server.
        """
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
                    print(f"{bcolors.lightgrey}Server disconnected, listening for offer requests...\n{bcolors.ENDC}")
                    self.is_playing = False
                    self.listen_for_offer()
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                print(f"{bcolors.LIGHTBLUE}Server disconnected, listening for offer requests...\n{bcolors.ENDC}")
                self.is_playing = False
                self.listen_for_offer()

    def send_user_input(self):
        """
        Send user input to the server.
        """
        while self.is_playing:
            try:
                user_input = input().strip()
                self.tcp_socket.sendall(user_input.encode())
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                print(f"{bcolors.LIGHTBLUE}Server disconnected, listening for offer requests...\n{bcolors.ENDC}")
                self.is_playing = False
                self.listen_for_offer()


if __name__ == "__main__":
    # Randomly select a team name from the list of client names
    team_name = random.choice(clients_names)
    # Create a TriviaClient object with the chosen team name
    client = TriviaClient(team_name)
    # Start listening for offer requests
    client.listen_for_offer()