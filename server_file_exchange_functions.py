import socket
import threading
import os
from datetime import datetime

class FileExchangeServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []  # (ip, port, handle)
        self.files = []
        self.folder_path = 'Server_Files'
        self.start_server()

    def start_server(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

        print(f"Server is listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Accepted connection from {client_address}")

            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def is_command(self, client_socket, input):
            command, *args = input.split()
            
            if (command in ['/leave', '/dir', '/?'] and len(args) == 0) or (command in ['/register', '/store', '/get'] and len(args) == 1) or (command == '/join' and len(args) == 2):
                return True

            elif (command in ['/leave', '/dir', '/?'] and len(args) != 0) or (command in ['/register', '/store', '/get'] and len(args) != 1) or (command == '/join' and len(args) != 2):
                client_socket.send("Error: Command parameters do not match or is not allowed.".encode('utf-8'))
                return False

            else:
                client_socket.send("Error: Command not found.".encode('utf-8'))
                return False    
            
    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                if self.is_command(client_socket, data) == False:
                    break

                command, *args = data.split()
                
                if command == '/join':
                    client_socket.send("Error: You are already connected to the server.".encode('utf-8'))
                
                elif command == '/leave':
                    self.remove_client(client_socket)
                    client_socket.send("Connection closed. Thank you!".encode('utf-8'))
                    client_socket.close()
                    break

                elif command == '/register':
                    handle = args[0]
                    if self.is_handle_unique(handle):
                        self.register_client(client_socket, handle)
                    else:
                        client_socket.send("Error: Handle or alias already exists.".encode('utf-8'))

                elif command == '/store':
                    filename = args[0]
                    self.receive_file(client_socket, filename)
                    
                elif command == '/dir':
                    file_list = self.get_directory_listing()
                    client_socket.send(file_list.encode('utf-8'))
                    
                elif command == '/get':
                    filename = args[0]
                    self.send_file(client_socket, filename)
                    
                elif command == '/?':
                    self.print_help(client_socket)
                    
            except ConnectionResetError:
                break

    def is_handle_unique(self, handle):
        for client in self.clients:
            if handle == client[2]:
                return False
        return True

    def register_client(self, client_socket, handle):
        client_address = client_socket.getpeername()
        self.clients.append((client_address[0], client_address[1], handle))
        
        client_socket.send(f"Welcome {handle}!".encode('utf-8'))

    def remove_client(self, client_socket):
        client_address = client_socket.getpeername()
        for client in self.clients:
            if client[0] == client_address[0] and client[1] == client_address[1]:
                self.clients.remove(client)
                break

    def receive_file(self, client_socket, filename):
        file_data = client_socket.recv(1024)

        # Create a folder named 'received_files' if it doesn't exist
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        file_path = os.path.join(self.folder_path, filename)
        
        with open(file_path, 'wb') as file:
            while True:
                file_data = client_socket.recv(1024)

                # Check for end-of-file marker
                if b'<<EOF>>' in file_data:
                    file.write(file_data[:-len(b'<<EOF>>')])
                    break

                file.write(file_data)
        
        file.close()

    def get_directory_listing(self):
        files = os.listdir(self.folder_path)
        return 'Server Directory\n' + '\n'.join(files)

    def send_file(self, client_socket, filename):
        file_path = os.path.join(self.folder_path, filename)
        
        try:
            with open(file_path, 'rb') as file:
                client_socket.send(f"File received from Server: {filename}".encode('utf-8'))
                file_data = file.read(1024)
                while file_data:
                    client_socket.send(file_data)
                    file_data = file.read(1024)
                    
                client_socket.send(b'<<EOF>>')
            
            file.close()
            
        except FileNotFoundError:
            client_socket.send('Error: File not found in the server.'.encode('utf-8'))

    def print_help(self, client_socket):
        help_info = """
        Disconnect to the server application: /leave
        Register a unique handle or alias: /register <handle>
        Send file to server: /store <filename>
        Request directory file list from a server: /dir
        Fetch a file from a server: /get <filename>
        Request command help to output all Input: /?
        """
        client_socket.send(help_info.encode('utf-8'))
        
if __name__ == "__main__":
    server = FileExchangeServer('localhost', 12345)