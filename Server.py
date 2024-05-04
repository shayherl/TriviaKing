import socket
import threading
import time
import random
from queue import Queue

# List of server names for randomly selecting a server name
server_names = ['Bunny Hopscotch', 'Carrot Chase', 'Floppy Fun Run', 'Rabbit Rumble', 'Hopping Hurdles', 'Burrow Blast',
                'Bunny Bonanza', 'Carrot Caper', 'Hoppy Trails', 'Fluffy Frenzy', 'Rabbit Rally', 'Whisker Whirlwind',
                'Bounce Brigade', 'Flop & Dash', 'Burrow Bounce-off', 'Furry Fiesta']

# ANSI escape codes for colors
class bcolors:
    LIGHTBLUE = '\033[36m'
    RED = '\033[31m'
    ENDC = '\033[0m'
    BLUE = '\033[94m'
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
    WHITE = '\033[97m'
    LIGHTYELLOW = '\033[93m'
    LIGHTMAGENTA = '\033[95m'
    LIGHTCYAN = '\033[96m'
    DARKCYAN = '\033[36m'


# Constants
UDP_PORT = 13117
TCP_PORT = 5555
MAGIC_COOKIE = b'\xab\xcd\xdc\xba'
OFFER_INTERVAL = 1  # Offer broadcast interval in seconds
QUESTION_INTERVAL = 10  # Time to wait for additional players before starting game
TEAM_SIZE = 2
QUESTIONS = [
    ("Bunnies are nocturnal animals.", False),
    ("A group of bunnies is called a herd.", False),
    ("Bunnies can see color.", True),
    ("Bunnies are rodents.", False),
    ("Bunnies are born blind.", True),
    ("Bunnies communicate through singing.", False),
    ("Bunnies have 28 teeth.", True),
    ("Bunnies can jump higher than the average house.", False),
    ("Bunnies have a high reproductive rate.", True),
    ("All bunnies have floppy ears.", False),
    ("Bunnies are social animals.", True),
    ("Bunnies can only eat carrots.", False),
    ("Bunnies have a great sense of smell.", True),
    ("Bunnies are a type of rodent.", False),
    ("Bunnies are lagomorphs.", True),
    ("Bunnies live in groups called colonies.", True),
    ("Bunnies have a lifespan of up to 5 years.", False),
    ("Bunnies can purr like cats.", True),
    ("Bunnies are born with fur.", True),
    ("Bunnies hibernate during the winter.", False)
]


class TriviaServer:
    def __init__(self, server_name):
        """
           Initialize the TriviaServer object.

           Args:
               server_name (str): The name of the server.
       """
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('', TCP_PORT))
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Set to store connected clients
        self.clients = set()
        self.offer_thread = threading.Thread(target=self.broadcast_offer)
        # Flag to control offer broadcasting
        self.broadcast = True
        self.server_name = server_name.ljust(32, '\0')  # Ensure server name is 32 characters long
        # Flag to indicate if the game is in progress
        self.game_on = False
        # Set to store disconnected clients during the game
        self.disconnected = set()
        # Statistics dictionary of all players play on this server
        self.statistics = {}

    def start(self):
        """
        Start the TriviaServer.
        """
        print(f"{bcolors.LIGHTBLUE}Server started, listening on IP address", socket.gethostbyname(socket.gethostname()) + f"\n{bcolors.ENDC}")
        # Start broadcasting offer messages
        self.offer_thread.start()
        self.tcp_socket.listen(5)
        # Accept incoming client connections
        self.accept_clients()

    def broadcast_offer(self):
        """
        Broadcast offer messages periodically.
        """
        while self.broadcast:
            offer_message = MAGIC_COOKIE + b'\x02' + self.server_name.encode() + TCP_PORT.to_bytes(2, 'big')
            self.udp_socket.sendto(offer_message, ('<broadcast>', UDP_PORT))
            time.sleep(OFFER_INTERVAL)

    def game(self):
        """
        Start the trivia game.
        """
        # Send welcome message and trivia question
        welcome_msg = f"{bcolors.BLUE}Welcome to the {server_name}, where we are answering trivia questions about Bunnies.\n"
        players_msg = f"{bcolors.BLUE}\n".join([f"Player {i + 1}: {name}" for i, (_, name) in enumerate(self.clients)]) + f"\n"
        print(welcome_msg + players_msg)
        for client, name in self.clients:
            try:
                client.sendall((welcome_msg + players_msg).encode())
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                if (client, name) not in self.disconnected:
                    print("client", name, "disconnected\n")
                self.disconnected.add((client, name))
                client.close()
        self.game_on = True
        random.shuffle(QUESTIONS)
        question_idx = 0
        while True:
            question, real_answer = QUESTIONS[question_idx]
            question_idx += 1
            question_msg = f"{bcolors.BLUE}==\nTrue or false: {question}\n{bcolors.ENDC}"
            print(question_msg)
            for client, name in self.clients:
                try:
                    client.sendall(question_msg.encode())
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                    if (client, name) not in self.disconnected:
                        print("client", name, "disconnected\n")
                    self.disconnected.add((client, name))
                    client.close()

            # Receive answers from clients
            thread_list = []
            answer_queue = Queue()
            for client, name in self.clients:
                thread = threading.Thread(target=self.client_answer, args=(client, name, answer_queue))
                thread_list.append(thread)
                thread.start()

            # Wait for all threads to finish
            for thread in thread_list:
                thread.join()

            shortest_time = 11
            winner = ""
            while not answer_queue.empty():
                name, answer, time_taken = answer_queue.get()
                # check if the answer is correct and time is shorter than the current shortest time
                if answer == real_answer and time_taken < shortest_time:
                    shortest_time = time_taken
                    winner = name
            if winner == "":
                if self.disconnected == self.clients:
                    break
                noCorrect_msg = f"{bcolors.purple}No correct answer. Choosing another random trivia question...\n{bcolors.ENDC}"
                print(noCorrect_msg)
                for client, name in self.clients:
                    try:
                        client.sendall(f"{noCorrect_msg}\n".encode())
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                        if (client, name) not in self.disconnected:
                            print("client", name, "disconnected\n")
                        self.disconnected.add((client, name))
                        client.close()

            else:
                print(f"{bcolors.LIGHTMAGENTA}{winner} is correct! {winner} wins!\n{bcolors.ENDC}")
                for client, name in self.clients:
                    try:
                        client.sendall(f"{bcolors.LIGHTMAGENTA}{winner} is correct! {winner} wins!\n\n{bcolors.ENDC}".encode())
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                        if (client, name) not in self.disconnected:
                            print("client", name, "disconnected\n")
                        self.disconnected.add((client, name))
                        client.close()
                break
        if winner != "":
            # Send summary message to all players
            summary_msg = f"{bcolors.LIGHTMAGENTA}Game over!\nCongratulations to the winner: {winner}\n{bcolors.ENDC}"
            print(summary_msg)
            for client, name in self.clients:
                try:
                    client.sendall(summary_msg.encode())
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                    if (client, name) not in self.disconnected:
                        print("client", name, "disconnected\n")
                    self.disconnected.add((client, name))
                    client.close()
            # Update statistics that the player won
            self.statistics[winner][1] += 1

        self.game_on = False

        # Print game statistics
        for name, nums in self.statistics.items():
            per = f'{nums[1] / nums[0] * 100: .2f}'
            stat_msg = f"{bcolors.LIGHTMAGENTA}{name} won {per}% of the games\n{bcolors.ENDC}"
            print(stat_msg)

        # Close TCP connections and reset
        for client, name in self.clients:
            try:
                client.close()
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                if (client, name) not in self.disconnected:
                    print("client", name, "disconnected\n")
                self.disconnected.add((client, name))
                client.close()
        self.clients.clear()
        self.disconnected.clear()
        print(f"{bcolors.lightred}Game over, sending out offer requests...\n{bcolors.ENDC}")

        # Restart offer broadcasting
        self.broadcast = True
        self.offer_thread = threading.Thread(target=self.broadcast_offer)
        self.offer_thread.start()
        self.accept_clients()

    def client_answer(self, client, name, answer_queue):
        """
        Receive and process answers from clients.

        Args:
            client (socket): Client socket.
            name (str): Name of the client.
            answer_queue (Queue): Queue to store answers from clients.
        """
        start = time.time()
        try:
            client.settimeout(QUESTION_INTERVAL)
            while True:
                answer = client.recv(1024).decode().strip().lower()
                if answer == 'y' or answer == 't' or answer == '1':
                    answer = True
                    print(f"{bcolors.blue}Received answer from {name}: {answer}\n{bcolors.ENDC}")
                    break
                elif answer == 'n' or answer == 'f' or answer == '0':
                    answer = False
                    print(f"{bcolors.blue}Received answer from {name}: {answer}\n{bcolors.ENDC}")
                    break
                else:
                    client.sendall(f"{bcolors.RED}Invalid input, please type Y,T,1 for true or N,F,0 for false\n{bcolors.ENDC}".encode())
        except:
            answer = None
        time_taken = time.time() - start
        answer_queue.put((name, answer, time_taken))

    def accept_clients(self):
        """
        Accept client connections and start the game when enough players are connected.
        """
        start = time.time()
        while True:
            try:
                # Set timeout based on remaining time in 10 seconds
                remaining_time = max(0, int(QUESTION_INTERVAL - (time.time() - start)))
                self.tcp_socket.settimeout(remaining_time)
                client_socket, address = self.tcp_socket.accept()
                # Receive player name from client
                player_name = client_socket.recv(1024).decode().strip()
                print(f"{bcolors.yellow}Player {player_name} connected from {address}\n{bcolors.ENDC}")
                self.clients.add((client_socket, player_name))
                # Update how many games the player played
                if player_name in self.statistics:
                    self.statistics[player_name][0] += 1
                else:
                    self.statistics[player_name] = [1, 0]
                # Reset the start time after a client connects
                start = time.time()
            # Wait for more players or start game after 10 seconds
            except socket.timeout:
                for client, name in self.clients:
                    try:
                        client.sendall(b'')
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
                        if (client, name) not in self.disconnected:
                            print("client", name, "disconnected\n")
                        self.disconnected.add((client, name))
                        client.close()
                for (client, name) in self.disconnected:
                    self.clients.remove((client, name))
                if len(self.clients) < TEAM_SIZE:
                    print(f"{bcolors.blue}Not enough players. Game aborted.\nTrying again.\n{bcolors.ENDC}")
                    if len(self.clients) != 0:
                        for client, _ in self.clients:
                            client.sendall(f"{bcolors.blue}Not enough players. Game aborted.\nTrying again.\n{bcolors.ENDC}".encode())
                    self.accept_clients()
                else:
                    self.broadcast = False
                    self.game()
            except Exception as e:
                print(f"{bcolors.RED}Error handling client {address}: {e}\n{bcolors.ENDC}")


if __name__ == "__main__":
    # Randomly select a server name from the list of server names
    server_name = random.choice(server_names)
    # Create a TriviaServer object with the chosen server name
    server = TriviaServer(server_name)
    # Start the server
    server.start()
