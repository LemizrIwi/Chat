# client.py
import socket
import threading

HOST = "https://messengerpublic.onrender.com"  # z. B. 192.168.x.x
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

def receive():
    while True:
        try:
            msg = client.recv(1024).decode('utf-8')
            print(msg)
        except:
            print("Verbindung getrennt.")
            client.close()
            break

def write():
    while True:
        msg = input('')
        client.send(msg.encode('utf-8'))

receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()

