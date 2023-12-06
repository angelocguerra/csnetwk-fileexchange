import socket
import threading
from datetime import datetime
import tkinter as tk
import tkinter.scrolledtext as tkst
from queue import Queue


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
        self.server_ip_add = host
        self.port = port
        self.handle = ""
        self.is_connected = False
        self.is_left = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.message_queue = Queue()
        self.update_event = threading.Event()

    # Checks if the given input is a valid command.
    #
    # Args:
    #     input (str): The user input.
    #
    # Returns:
    #     bool: True if the input is a valid command, False otherwise.
    def is_command(self, input):

        command, *args = input.split()

        if (command in ['/leave', '/dir', '/?'] and len(args) == 0) or (
                command in ['/register', '/store', '/get'] and len(args) == 1) or (
                command == '/join' and len(args) == 2) or (command in ['/broadcast', '/message']):
            return True

        elif (command in ['/leave', '/dir', '/?'] and len(args) != 0) or (
                command in ['/register', '/store', '/get'] and len(args) != 1) or (
                command == '/join' and len(args) != 2):
            print("Error: Command parameters do not match or is not allowed.")
            self.message_queue.put("Error: Command parameters do not match or is not allowed.")
            return False

        else:
            print('Error: Command not found.')
            self.message_queue.put('Error: Command not found.')
            return False

    # Sends a command to the server.
    #
    # Args:
    #     command (str): The command to send.
    def send_command(self, command):
        if self.is_command(command):
            if not self.is_connected:
                print("Error: Connection to the server lost. Please reconnect.")
                self.message_queue.put("Error: Connection to the server lost. Please reconnect.")
                return

            try:
                self.client_socket.send(command.encode('utf-8'))

                if command.startswith('/store'):
                    filename = command.split()[1]
                    self.send_file(filename)
            except ConnectionResetError:
                print("Connection to the server lost.")
                self.message_queue.put("Connection to the server lost.")
                self.is_connected = False

    # Receives data from the server.
    def receive_data(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')

                if not data:
                    print("Connection to the server lost.")
                    self.message_queue.put("Connection to the server lost.")
                    self.is_connected = False
                    self.client_socket.close()
                    break

                if data.startswith('Welcome') and self.handle == "":
                    print(data)
                    self.message_queue.put(data)
                    self.handle = data.split()[1]
                    self.handle = self.handle[:-1]

                elif data.startswith('Connection closed.'):
                    print(data)
                    self.message_queue.put(data)
                    self.is_left = True
                    print(self.is_left)
                    self.client_socket.close()
                    break

                elif not data.startswith('File received from Server:'):
                    print(data)
                    self.message_queue.put(data)

                else:
                    filename = data.split()[4]
                    self.receive_file(filename)

            except ConnectionResetError:
                print("Connection to the server lost.")
                self.is_connected = False
                self.server_ip_add = ""
                self.port = ""
                self.handle = ""
                self.client_socket.close()
                break

            except UnicodeDecodeError:
                print("Error: Invalid input received from the server.")
                self.message_queue.put("Error: Invalid data received from the server.")
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
            self.message_queue.put(
                f"{self.handle}<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}>: Uploaded {filename}")

        except FileNotFoundError:
            print('Error: File not found.')
            self.message_queue.put('Error: File not found.')

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
            self.message_queue.put(f"File received: {filename}")

        except ConnectionResetError:
            print("Connection to the server lost.")
            self.message_queue.put("Connection to the server lost.")

        except Exception as e:
            print(f"Error receiving file: {str(e)}")
            self.message_queue.put(f"Error receiving file: {str(e)}")

    def send_broadcast(self, message):
        self.client_socket.send(f'/broadcast {message}'.encode('utf-8'))

    def send_unicast(self, recipient_handle, message):
        self.client_socket.send(f'/unicast {recipient_handle} {message}'.encode('utf-8'))


class FileExchangeGUI:
    def __init__(self):
        self.file_exchange_client = None
        self.root = tk.Tk()
        self.root.title("File Exchange Client")

        self.text_area = tkst.ScrolledText(self.root, wrap=tk.WORD, width=50, height=20)
        self.text_area.pack(padx=10, pady=10)
        self.text_area.insert(tk.END,
                              "Welcome to the File Exchange Client! Connect to the server application using /join <server_ip_add> <port>\n")

        self.entry_command = tk.Entry(self.root, width=50)
        self.entry_command.pack(padx=10, pady=10)

        self.send_button = tk.Button(self.root, text="Send Command", command=self.send_command)
        self.send_button.pack(pady=10)

    def send_command(self):
        command = self.entry_command.get()
        self.text_area.insert(tk.END, f"\n{command}\n")
        self.text_area.yview(tk.END)
        self.entry_command.delete(0, tk.END)
        command, *args = command.split()

        if self.file_exchange_client is None:
            if command.startswith('/join') and len(args) == 2:
                server_ip_add, port = args
                self.file_exchange_client = FileExchangeClient(server_ip_add, int(port))

                try:
                    self.file_exchange_client.client_socket.connect((server_ip_add, int(port)))
                    self.file_exchange_client.is_connected = True

                    receive_thread = threading.Thread(target=self.file_exchange_client.receive_data)
                    receive_thread.start()

                    self.text_area.insert(tk.END, f"Connected to server {server_ip_add} on port {port}\n")
                    self.text_area.yview(tk.END)

                except ConnectionRefusedError:
                    print("Error: Connection to the Server has failed! Please check IP Address and Port Number")
                    self.text_area.insert(tk.END, "Error: Connection to the Server has failed! Please check IP Address and Port Number\n")
                    self.text_area.yview(tk.END)
                    self.file_exchange_client = None

                except socket.timeout:
                    print("Error: Connection to the Server has failed! Please check IP Address and Port Number")
                    self.text_area.insert(tk.END, "Error: Connection to the Server has failed! Please check IP Address and Port Number\n")
                    self.text_area.yview(tk.END)
                    self.file_exchange_client = None

                except Exception:
                    print("Error: Connection to the Server has failed! Please check IP Address and Port Number")
                    self.text_area.insert(tk.END, "Error: Connection to the Server has failed! Please check IP Address and Port Number\n")
                    self.text_area.yview(tk.END)
                    self.file_exchange_client = None

            elif command.startswith('/join') and len(command.split()) != 3:
                print("Error: Command parameters do not match or is not allowed.")
                self.text_area.insert(tk.END, "Error: Command parameters do not match or is not allowed.\n")
                self.text_area.yview(tk.END)

            elif command == "/?":
                help_info = "Connect to the server application: /join <server_ip> <port>\n"
                print(help_info)
                self.text_area.insert(tk.END, help_info)
                self.text_area.yview(tk.END)

            elif command in ['/leave', '/dir', '/register', '/store', '/get']:
                print("Error: Please connect to the server before entering a command. Enter /? for help.")
                self.text_area.insert(tk.END, "Error: Please connect to the server before entering a command. Enter /? for help.\n")
                self.text_area.yview(tk.END)

            else:
                print("Error: Invalid Input. Enter /? for help.")
                self.text_area.insert(tk.END, "Error: Invalid Input. Enter /? for help.\n")
                self.text_area.yview(tk.END)

        elif not self.file_exchange_client.is_connected:
            self.text_area.insert(tk.END, "Error: Connection to the server lost.\n")
            self.text_area.yview(tk.END)

        else:
            if self.file_exchange_client.handle and command.startswith('/register') and len(command.split()) == 2:
                print("Error: You are already registered with the server.")
                self.text_area.insert(tk.END, "Error: You are already registered with the server.\n")
                self.text_area.yview(tk.END)

            elif not self.file_exchange_client.handle and command.startswith(('/dir', '/store', '/get', '/broadcast', '/message')):
                print("Error: You are not registered with the server. Please register first. Type /? for help.")
                self.text_area.insert(tk.END, "Error: You are not registered with the server. Please register first. Type /? for help.\n")
                self.text_area.yview(tk.END)

            elif command == "/?":
                help_info = "Register with the server: /register <handle>\n"
                print(help_info)
                self.text_area.insert(tk.END, help_info)
                self.text_area.yview(tk.END)

            elif command.startswith('/join'):
                print("Error: You are already connected to the server.")
                self.text_area.insert(tk.END, "Error: You are already connected to the server.\n")
                self.text_area.yview(tk.END)

            else:
                self.file_exchange_client.send_command(command)
                self.text_area.yview(tk.END)

            self.root.after(100, self.update_text_area)

    def update_text_area(self):
        if self.file_exchange_client.is_connected:
            while not self.file_exchange_client.message_queue.empty():
                message = self.file_exchange_client.message_queue.get()
                self.text_area.insert(tk.END, f"{message}\n")
                self.text_area.yview(tk.END)
        self.root.after(100, self.update_text_area)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    gui = FileExchangeGUI()
    gui.run()
