import socket
import sys
import threading
import os
from datetime import datetime
import time

# Represents a client for file exchange with a server.
#
# Attributes:
#     server_ip (str): The IP address of the server.
#     port (int): The port number to connect to.
#     handle (str): The client's handle.
#     client_socket (socket.socket): The client's socket for communication with the server.
class FileExchangeClient:
    
    # Initializes a new instance of the FileExchangeClient class.
    #
    # Args:
    #     host (str): The IP address of the server.
    #     port (int): The port number to connect to.
    def __init__(self, host, port):
        self.server_ip = host
        self.port = port
        self.handle = ""
        self.is_connected = False
        self.is_left = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

    # Connects to the file exchange server and starts the communication loop.
    def connect_to_server(self):
        self.is_connected = True
        try:
            with self.client_socket:
                self.client_socket.connect((server_ip_add, int(port)))
                print("Connection to the File Exchange Server is successful!")

                receive_thread = threading.Thread(target=self.receive_data)
                receive_thread.start()

                while True:
                    if self.is_connected == False:
                        print("Error: Connection to the server lost.")
                        return
                    
                    time.sleep(0.1)
                    user_input = input("\nEnter a command: ")
                    command, *args = user_input.split()
                    
                    if self.handle and command == "/register" and len(args) == 1:
                        print("Error: You are already registered with the server.")
                    
                    elif not self.handle and command in ['/dir', '/store', '/get', '/broadcast', '/message']:
                        print("Error: You are not registered with the server. Please register first. Type /? for help.")
                        
                    elif command == "/?":
                        help_info = """
                        Register with the server: /register <handle>
                        """
                        print(help_info)
                        
                    else:
                        self.send_command(user_input)
                    
                    time.sleep(0.1)
                    if self.is_left:
                        return

        except ConnectionRefusedError:
            print("Error: Connection to the Server has failed! Please check IP Address and Port Number.")

        except socket.timeout:
            print("Error: Connection to the Server has failed! Please check IP Address and Port Number.")
        
        except Exception:
            print("Error: Connection to the Server has failed! Please check IP Address and Port Number.")

    # Checks if the given input is a valid command.
    #
    # Args:
    #     input (str): The user input.
    #
    # Returns:
    #     bool: True if the input is a valid command, False otherwise.
    def is_command(self, input):
        
        command, *args = input.split()

        if (command in ['/leave', '/dir', '/?'] and len(args) == 0) or (command in ['/register', '/store', '/get'] and len(args) == 1) or (command == '/join' and len(args) == 2) or (command in ['/broadcast', '/message']):
            return True

        elif (command in ['/leave', '/dir', '/?'] and len(args) != 0) or (command in ['/register', '/store', '/get'] and len(args) != 1) or (command == '/join' and len(args) != 2):
            print("Error: Command parameters do not match or is not allowed.")
            return False

        else:
            print('Error: Command not found.')
            return False

    # Sends a command to the server.
    #
    # Args:
    #     command (str): The command to send.
    def send_command(self, command):
        if self.is_command(command) == True:
            self.client_socket.send(command.encode('utf-8'))

            if command.startswith('/store'):
                filename = command.split()[1]
                self.send_file(filename)

    # Receives data from the server.
    def receive_data(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')

                if data.startswith('Welcome') and self.handle == "":
                    print(data)
                    self.handle = data.split()[1]
                    self.handle = self.handle[:-1]
                    
                elif data.startswith('Connection closed.'):
                    print(data)
                    self.is_left = True
                    print(self.is_left)
                    self.client_socket.close()
                    break
                    
                elif not data.startswith('File received from Server:'):
                    print(data)
                    
                else:
                    filename = data.split()[4]
                    self.receive_file(filename)

            except ConnectionResetError:
                self.is_connected = False
                self.server_ip = ""
                self.port = ""
                self.handle = ""
                self.client_socket.close()
                break

    # Sends a file to the server.
    #
    # Args:
    #     filename (str): The name of the file to send.
    def send_file(self, filename):
        try:
            with open(filename, 'rb') as file:
                self.client_socket.send(f"/store {filename}".encode('utf-8'))  # Start of file transmission

                file_data = file.read(1024)
                while file_data:
                    self.client_socket.send(file_data)
                    file_data = file.read(1024)

                # Add an end-of-file marker
                self.client_socket.send(b'<<EOF>>')

            file.close()

            print(f"{self.handle}<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}>: Uploaded {filename}")

        except FileNotFoundError:
            print('Error: File not found.')

    # Receives a file from the server.
    #
    # Args:
    #     filename (str): The name of the file to receive.
    def receive_file(self, filename):
        try:
            with open(filename, 'wb') as file:
                while True:
                    file_data = self.client_socket.recv(1024)

                    # Check for end-of-file marker
                    if b'<<EOF>>' in file_data:
                        file.write(file_data[:-len(b'<<EOF>>')])
                        break

                    file.write(file_data)

            print(f"File received: {filename}")

        except ConnectionResetError:
            print("Connection to the server lost.")

        except Exception as e:
            print(f"Error receiving file: {str(e)}")

    def send_broadcast(self, message):
        self.client_socket.send(f'/broadcast {message}'.encode('utf-8'))

    def send_unicast(self, recipient_handle, message):
        self.client_socket.send(f'/unicast {recipient_handle} {message}'.encode('utf-8'))
    
if __name__ == "__main__":
    while True:
        command = input("Enter a command: ")
        
        if command.startswith('/join') and len(command.split()) == 3:
            _, server_ip_add, port = command.split()
            client = FileExchangeClient(server_ip_add, int(port))
        
        elif command.startswith('/join') and len(command.split()) != 3:
            print("Error: Command parameters do not match or is not allowed.")
            
        elif command == "/?":
            help_info = """
            Connect to the server application: /join <server_ip_add> <port>
            """
            print(help_info)
        
        elif command in ['/leave', '/dir', '/register', '/store', '/get']:
            print("Error: Please connect to the server before entering a command. Enter /? for help.")
            
        else:
            print("Error: Invalid Input. Enter /? for help.")  
    