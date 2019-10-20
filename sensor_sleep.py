#!/usr/bin/env python3

import serial

def main():
    ser = serial.Serial('/dev/ttyUSB0') # initialize receiver USB
    bytes = [b'\xaa', #head
    b'\xb4', #command 1
    b'\x06', #data byte 1
    b'\x01', #data byte 2 (set mode)
    b'\x00', #data byte 3 (sleep)
    b'\x00', #data byte 4
    b'\x00', #data byte 5
    b'\x00', #data byte 6
    b'\x00', #data byte 7
    b'\x00', #data byte 8
    b'\x00', #data byte 9
    b'\x00', #data byte 10
    b'\x00', #data byte 11
    b'\x00', #data byte 12
    b'\x00', #data byte 13
    b'\xff', #data byte 14 (device id byte 1)
    b'\xff', #data byte 15 (device id byte 2)
    b'\x05', #checksum
    b'\xab'] #tail
    
    for b in bytes:
        ser.write(b)

if __name__ == '__main__':
    main()
