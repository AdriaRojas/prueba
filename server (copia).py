#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys 
import os 
import traceback 
import optparse
import time
import datetime
import socket
import random
import signal
import threading    
import random

# Variables Globales
DEBUG = False
#server = []
config_file = "server.cfg"
devices_con = "equips.dat"

#Constantes

t = 1
p = 2
q = 3
u = 2
n = 6
o = 2
r = 2
s = 3
w = 3

# Objeto cliente
class clients:
    def __init__(self, id, mac, status='DISCONNECTED',randomnum='000000'):
        self.id = id
        self.mac = mac
        self.status = status
        self.randomnum = randomnum       
        self.ip = ""
        self.incorrect_alive = 0
        self.first_alive = False 
def main():
        try:
            global DEBUG, config_file, devices_con
            server = []
            if len(sys.argv) > 1:
                for i in range(1, len(sys.argv)):
                    if sys.argv[i] == "-c":
                        config_file = sys.argv[i + 1]
                    if sys.argv[i] == "-u":
                        devices_con = sys.argv[i + 1]
                    if sys.argv[i] == "-d":
                        DEBUG = True
                    
                else:
                    config_file = "server.cfg"
            else:
                config_file = "server.cfg"
                devices_con = "equips.dat"
   
            with open(config_file, "r") as file:
                for line in file:
                    line = line.split()
                    server.append(line[1])
            print(server)
            readdevices(devices_con)
            register(server);        
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            exit()

def readdevices(devices_con):
    global allowed_devices
    allowed_devices = []
    with open(devices_con, "r") as file:
        for line in file:
            line = line.split()
            allowed_devices.append(clients(line[0], line[1]) )
           
def read_console(allowed_devices):
    while True:
        console = input()
        if console == "list":
            print("Mostrando la lista de dispositivos permitidos")
            print_list(allowed_devices)
        if console == "quit":
            print("Saliendo...")
           
            os._exit(0)

def print_list( allowed_devices):
    print("|----------------------------------------------------------------------|")
    print("|ID      |  MAC           |  STATUS        |  IP         |  RANDOMNUM  |")
    print("|----------------------------------------------------------------------|")
    for device in allowed_devices:
        try:
            if device.status != "DISCONNECTED":
                print("|"+device.id + "  |  " + device.mac + "  |  " + device.status + "         |  " + device.ip+ "  |  "  + str(device.randomnum)+"     |"  )
                print("|----------------------------------------------------------------------|")
            else:
                print("|"+device.id + "  |  " + device.mac + "  |  DISCONNECTED  |"+"                           |")
                print("|----------------------------------------------------------------------|")
        
        except IndexError:
            pass



def register(server):
    
    console_Thread = threading.Thread(target=read_console, args=(allowed_devices,))
    console_Thread.start()
    config_Thread = threading.Thread(target=config_tcp, args=(server, allowed_devices, ))
    config_Thread.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = int(server[2])    
    address = (("127.0.0.1", port))
    sock.bind(address)
    sock.settimeout(1)
    while True:
        try:
            data, address = sock.recvfrom(78)
            device = take_pdu_info((data, address)) #tipo, nombre, mac, numero recibido
            #print(device)
            if data[0] == 0x00:
                print("alguien se intenta registar")
                thread_register= threading.Thread(target=addcon, args=(device,allowed_devices, server, sock))
                thread_register.start()
            elif data[0] == 0x10:
                print("Pdu alive")
                keep_alive(device, allowed_devices, sock, server)
        except socket.timeout:
            pass
        
def take_pdu_info(package):
    id = package[0][1:7].decode().replace('\x00', '')
    mac = package[0][8:20].decode().replace('\x00', '')
    number = package[0][21:28].decode().replace('\x00', '')
    data = package[0][29:78]
    address = package[1]
    return((id, mac, number, address, data))


def addcon (device, allowed_devices, server, socket):
    #PC Válido -> REGISTERED
    #global allowed_devices, server
    if validation(device[0], device[1]):

        d = not_connected(device[0], device[1],device[2], allowed_devices)

        if d != False:
            changestate(d,"WAIT_DB_CHECK")
            if d.randomnum == "000000":
                number = "%06d"%random.randint(000000, 999999)
                d.randomnum = number
            d.ip = device[3][0]
            for c in allowed_devices:
                if(c.id==d.id):
                    index_cliente = allowed_devices.index(c)
                    break
            allowed_devices[index_cliente] = d
            pdu = ensamble_UDP_PDU(0x02, str(server[0]), str(server[1]), str(d.randomnum), server[3])
            print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(device[0]) + " se ha REGISTRADO")
            socket.sendto(pdu, (device[3]))
            changestate(d,"REGISTRED")
            
        else:
            for device1 in allowed_devices:
                if device1.id == device[0] and device1.mac == device[1]  and device1.ip != device[3][0]:
                    pdu = ensamble_UDP_PDU(0x04, "000000", "000000000000", "000000", "Dirección ip no valida")
                
                elif device1.id == device[0] and device1.mac == device[1] and device1.randomnum != device[2]:
                    pdu = ensamble_UDP_PDU(0x04, "000000", "000000000000", "000000", "Numero aleatorio no valido")  

                elif device1.id == device[0] and device1.mac == device[1] and device1.status == "ALIVE" or device1.status == "REGISTRED":
                    num= takenumber(device[0], device[1], allowed_devices)
                    pdu = ensamble_UDP_PDU(0x02, str(server[0]), str(server[1]), str(num), server[3])    
            
            
            socket.sendto(pdu, device[3])    


    else:
        pdu = ensamble_UDP_PDU(0x06, "000000", "000000000000", "000000", "Paquete de conexión no válido")
        socket.sendto(pdu, device[3])



def keep_alive(device, allowed_devices, socket, server):
    d = connected(device[0], device[1], allowed_devices)
    if d == False:
        pdu = ensamble_UDP_PDU(0x16, "000000", "000000000000", "000000", "Equipo no registrado")
        socket.sendto(pdu, (device[3]))
    else:
        if d.status == "REGISTRED" or d.status == "ALIVE" and d.ip == device[3][0] and d.randomnum == device[2]:
            if d.status == "REGISTRED":
                print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(device[0]) + " se encuentra ALIVE")
                changestate(d,"ALIVE")
                d.first_alive = True
                update_client(d) 
                         
            pdu = ensamble_UDP_PDU(0x12, server[0], server[1], str(d.randomnum), "")
            socket.sendto(pdu, device[3])
            d.incorrect_alive = 0
             
        elif d.randomnum != device[2]:
            pdu = ensamble_UDP_PDU(0x14, "000000", "000000000000", "000000", "Numero aleatorio no valido")
            socket.sendto(pdu, (device[3]))
            d.incorrect_alive += 1
        elif d.ip != device[3][0]:
            pdu = ensamble_UDP_PDU(0x14, "000000", "000000000000", "000000", "Ip no valida")
            socket.sendto(pdu, (device[3]))
            d.incorrect_alive += 1 
        if d.status == "REGISTRED" and d.incorrect_alive==2:
            print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(device[0]) + " se encuentra DISCONNECTED")
            changestate(d,"DISCONNECTED")
            d.incorrect_alive = 0
            update_client(d)
        elif d.status == "ALIVE" and d.incorrect_alive==3:
            print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(device[0]) + " se encuentra DISCONNECTED")
            changestate(d,"DISCONNECTED")
            d.incorrect_alive = 0
            update_client(d)


def update_client(d):
    for device in allowed_devices:
        if device.id == d.id and device.mac == d.mac and device.randomnum == d.randomnum:
            index = allowed_devices.index(device)
            allowed_devices[index] = d

def takenumber(id, mac, list):
    for device in allowed_devices:
        if device.id == id and device.mac == mac:
            return device.randomnum
    return False

def changestate(device, state):
    for device1 in allowed_devices:
        if device1.id == device.id :
            device1.status = state
            index = allowed_devices.index(device1)
            allowed_devices[index] = device1
            
def connected(id, mac, allowed_devices):
    for device in allowed_devices:
        if device.id == id and device.mac == mac and device.status != "DISCONNECTED" :
            return device
    return False 

def not_connected(id, mac,randnum, list):
    for device in allowed_devices:
        if device.id == id and device.mac == mac and device.status == "DISCONNECTED" and device.randomnum == randnum:
            return device
    return False        
        
def validation(id, mac): #modificar
    for devices in allowed_devices:
        if devices.id == id and devices.mac == mac:
            return True
    return False

def ensamble_UDP_PDU(pack_type, device_name, mac, number, data): #modificar
    byte_pdu = [chr(0)]*78
    byte_pdu[0] = chr(pack_type)
    byte_pdu[1: 1 + len(device_name)] = device_name
    byte_pdu[8:8 + len(mac)] = mac
    byte_pdu[21:21 + len(number)] = number
    byte_pdu[28:28 + len(data)] = data
    byte_pdu = ''.join(byte_pdu).encode()
    return byte_pdu

def config_tcp(server, allowed_devices): #modificar
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    port = int(server[3])    
    address = (("127.0.0.1", port))
    sock.bind(address)
    sock.listen(5)
    while(True):
        connection_prueba, client_address = sock.accept()
        print(datetime.datetime.now().strftime("%H:%M:%S") + " => Solicitud TCP recibida. Preparando conexión.")

        command_thread = threading.Thread(target=control_tcp_package, args=(connection_prueba, allowed_devices, server, ))
        command_thread.start()

def control_tcp_package(connection_prueba, connected_devices, config): #modificar
    try:
        package = connection_prueba.recv(178)
        if package[0] == 0x20:
            print("Reciviendo configuración del usuario")
            recive_user_config(connection_prueba, package, connected_devices, config)

        # if package[0] == 0x30:
        #     print("Not implemented")
        #     send_user_config(connection, package,connected_devices, config)
    except ConnectionResetError:
        print(datetime.datetime.now().strftime("%H:%M:%S") + " => Se ha cerrado la comunicación TCP")
        #print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(connection_prueba[0][0][0]) + " ha cerrado la comunicación TCP")

def recive_user_config(connection_prueba, package, connected_devices, server_config): #modificar cambiar parametros y sobretodo user por id
    user = take_tcp_sender(package)
    is_connected = connected(user[0], user[1], connected_devices)

    if is_connected != False and is_connected.randomnum == user[2]:
        print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(user[0]) + " va ha realizar un envío TCP.")

        accept_config(connection_prueba, user, server_config)
    else:
        print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + str(user[0]) + " no está conectado")

def take_tcp_sender(package): #modificar
    user = package[1:8].decode().replace('\x00', '')
    mac = package[8:21].decode().replace('\x00', '')
    number = package[21:28].decode().replace('\x00', '')
    return ((user, mac, number))

def accept_config(connection_prueba, user, server_config): #modificar cambiar parametros y sobretodo user por id
    mensage = ensamble_TCP_PDU(0x24,server_config, user[2], user[0])
    connection_prueba.send(mensage)
    write_data(connection_prueba, user[0])

def write_data(connection, name):
    
    config_file = open(name + ".cfg", "w")
    

    while True:
        data = connection.recv(178)
        config_file.write(line_of_data(data[28:]) + '\n')
        if data[0] == 0x2A:
            break

    print(datetime.datetime.now().strftime("%H:%M:%S") + " => El equipo " + name + " ha finalizado su envío TCP")

    config_file.close()
    connection.close()
    print(datetime.datetime.now().strftime("%H:%M:%S") + " => Conexión TPC finalizada.")
    
    
def ensamble_TCP_PDU(pack_type, server,number, data =""): #modificar
    byte_pdu = [chr(0)]*178
    byte_pdu[0] = chr(pack_type)
    byte_pdu[1: 1 + len(server[0])] = server[0]
    byte_pdu[8:8 + len(server[1])] = server[1]
    byte_pdu[21:21 + len(server[2])] = number
    byte_pdu[28:28 + len(data)] = data
    byte_pdu = ''.join(byte_pdu).encode()
    return byte_pdu

def line_of_data(data): #modificar
    string = ""
    for i in data:
        if chr(i) == '\n':
            break
        string = string + chr(i)
    return string

if __name__ == "__main__":
    main()         