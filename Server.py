import socket
import sys
import threading
import time
import random
from queue import Queue
import select


class bcolors:
    LIGHTBLUE = '\033[36m'
    RED = '\033[31m'
    ENDC = '\033[0m'
    BLUE = '\033[94m'


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
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('', TCP_PORT))
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.clients = set()
        self.offer_thread = threading.Thread(target=self.broadcast_offer)
        self.broadcast = True
        self.server_name = server_name.ljust(32, '\0')  # Ensure server name is 32 characters long

    def start(self):
        print(f"{bcolors.LIGHTBLUE}Server started, listening on IP address", socket.gethostbyname(socket.gethostname()) + f"\n{bcolors.ENDC}")
        self.offer_thread.start()
        self.tcp_socket.listen(5)
        self.accept_clients()

    def broadcast_offer(self):
        while self.broadcast:
            offer_message = MAGIC_COOKIE + b'\x02' + self.server_name.encode() + TCP_PORT.to_bytes(2, 'big')
            self.udp_socket.sendto(offer_message, ('<broadcast>', UDP_PORT))
            time.sleep(OFFER_INTERVAL)

    def game(self):
        # Send welcome message and trivia question
        welcome_msg = f"{bcolors.BLUE}Welcome to the Mystic server, where we are answering trivia questions about Bunnies.\n"
        players_msg = f"{bcolors.BLUE}\n".join([f"Player {i + 1}: {name}" for i, (_, name) in enumerate(self.clients)]) + f"\n"
        for client, _ in self.clients:
            client.sendall((welcome_msg + players_msg).encode())
        random.shuffle(QUESTIONS)
        question_idx = 0
        while True:
            question, real_answer = QUESTIONS[question_idx]
            question_idx += 1
            question_msg = f"{bcolors.BLUE}==\nTrue or false: {question}\n{bcolors.ENDC}"
            for client, _ in self.clients:
                client.sendall(question_msg.encode())

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
                noCorrect_msg = f"{bcolors.BLUE}No correct answer. Choosing another random trivia question...\n{bcolors.ENDC}"
                print(noCorrect_msg)
                for client, _ in self.clients:
                    client.sendall(f"{noCorrect_msg}\n".encode())
            else:
                print(f"{bcolors.BLUE}{winner} is correct! {winner} wins!\n{bcolors.ENDC}")
                for client, _ in self.clients:
                    client.sendall(f"{bcolors.BLUE}{winner} is correct! {winner} wins!\n\n{bcolors.ENDC}".encode())
                    # client.close()
                break
        # Send summary message to all players
        summary_msg = f"{bcolors.BLUE}Game over!\nCongratulations to the winner: {winner}\n{bcolors.ENDC}"
        for client, _ in self.clients:
            client.sendall(summary_msg.encode())

        # Close TCP connections and reset
        for client, _ in self.clients:
            client.close()
        self.clients.clear()
        print(f"{bcolors.BLUE}Game over, sending out offer requests...\n{bcolors.ENDC}")

        # Restart offer broadcasting
        self.broadcast = True
        self.offer_thread = threading.Thread(target=self.broadcast_offer)
        self.offer_thread.start()
        self.accept_clients()

    def client_answer(self, client, name, answer_queue):
        start = time.time()
        try:
            # while time.time() - start < QUESTION_INTERVAL:
            #     ready_to_read, _, _ = select.select([client], [], [], 10)
            #     if ready_to_read:
            client.settimeout(QUESTION_INTERVAL)
            answer = client.recv(1024).decode().strip().lower()
            if answer == 'y' or answer == 't' or answer == '1':
                answer = True
            elif answer == 'n' or answer == 'f' or answer == '0':
                answer = False
            print(f"{bcolors.BLUE}Received answer from {name}: {answer}\n{bcolors.ENDC}")
                    # break
        except:
            answer = None
        time_taken = time.time() - start
        answer_queue.put((name, answer, time_taken))

    def accept_clients(self):
        start = time.time()
        while True:
            try:
                # Set timeout based on remaining time in 10 seconds
                remaining_time = max(0, int(QUESTION_INTERVAL - (time.time() - start)))
                self.tcp_socket.settimeout(remaining_time)
                client_socket, address = self.tcp_socket.accept()
                # Receive player name from client
                player_name = client_socket.recv(1024).decode().strip()
                print(f"{bcolors.LIGHTBLUE}Player {player_name} connected from {address}\n{bcolors.ENDC}")
                self.clients.add((client_socket, player_name))
                # Reset the start time after a client connects
                start = time.time()
            except socket.timeout:
                # Wait for more players or start game after 10 seconds
                if len(self.clients) < TEAM_SIZE:
                    print(f"{bcolors.LIGHTBLUE}Not enough players. Game aborted.\nTrying again.\n{bcolors.ENDC}")
                    if len(self.clients) != 0:
                        client_socket.sendall(f"{bcolors.LIGHTBLUE}Not enough players. Game aborted.\nTrying again.\n{bcolors.ENDC}".encode())
                    self.clients.clear()
                    self.accept_clients()
                else:
                    self.broadcast = False
                    self.game()
            except Exception as e:
                print(f"{bcolors.RED}Error handling client {address}: {e}\n{bcolors.ENDC}")

        # for client, _ in self.clients:
        #     client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"{bcolors.RED}Usage: python client.py <team_name>{bcolors.ENDC}")
        sys.exit(1)

    server_name = sys.argv[1]
    server = TriviaServer(server_name)
    server.start()
