#!/usr/bin/python3
# coding: utf-8

'''
Description:
Test a (Adafruit) AMG8833 IR Thermal Camera using python 3.

Background:
Reduce the need for other libraries (like adafruit_amg88xx)
for easier integration with other devices on the same i2c bus.

Sources:
https://www.adafruit.com/product/3538
https://learn.adafruit.com/adafruit-amg8833-8x8-thermal-camera-sensor
https://wiki.seeedstudio.com/Grove-Infrared_Temperature_Sensor_Array-AMG8833/
https://github.com/Seeed-Studio/Seeed_AMG8833_Raspberry_Python
https://industry.panasonic.eu/components/sensors/industrial-sensors/grid-eye/grid-eye-high-performance-type/amg8833-amg8833

Requirements (other than python 3):
sudo apt install i2c-tools python3-smbus

Excute with: python3 test_amg8833_smbus.py

Register and coordinate layout along line of sight, 
if board is rotated so lens is nearest the lower side:
	01------08		x1,y1-------x8,y1
	|		|			|		|
	|		|			|		|
	|		|			|		|
	57------64		x1,y8-------x8,y8

Updates:
2020-10-24: Tested on Raspberry Pi with Raspberry Pi OS (Debian 10 Buster)
2020-10-23: Created by Per Stenebo
'''
#-----------------------------------------------------------------------
# Import modules
#-----------------------------------------------------------------------
import sys, signal, os, time

# Installed modules
import smbus


#-----------------------------------------------------------------------
# Config
#-----------------------------------------------------------------------
# Check bus number:
# ls -l /dev/i2c*
# Usually 0 for Raspberry Pi 256 MB models and 1 for 512 MB models
busnr = 1

# Check bus address with i2cdetect -y <busnr>
# By default, the I2C address is 0x69. If you solder the jumper on 
# the back of the board labeled "Addr", the address will change to 0x68.
address = 0x69

# Pixel value to temp conversion factor
PixTempConv = 0.25

REG_PCLT = 0x00
REG_RST	 = 0x01
REG_SCLR = 0x05
REG_T01L = 0x80
REG_T64H = 0xFF

PCLT_normal	= 0x00
SCLR_all	= 0x0E
RST_init	= 0x3F


#-----------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------
# Manage ctrl+c
def signal_handler(signal, frame):
	print ('Script terminated by Ctrl+C')
	# Terminate script
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

''' Convert AMG8833 IR Thermal Camera temperature values
from 12 bit two's complement form with 0.25°C steps to float '''
def AMG88xx_twos_comp_to_float(inp):
	# Swap bytes if using big endian because read_word_data
	# assumes little endian on ARM (little endian) systems.
	if not little_endian:
		b = ((inp << 8) & 0xFF00) + (inp >> 8)
	else:
		b = inp
		
	# Convert two's complement to float
	if  0x7FF & b == b:
		c = float(b)
	else:
		c = float(b - 4096)
		
	return c * PixTempConv

#-----------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------
if __name__ == '__main__':
	# Check system endianess
	if sys.byteorder == 'little':
		little_endian = True
	else:
		little_endian = False
		
	bus = smbus.SMBus(busnr)

	time.sleep(0.1)

	# Set sensor to normal mode (normal, sleep, standby)
	value = PCLT_normal & 0xFF
	bus.write_byte_data(address, REG_PCLT, value)
	print ('Normal mode set. Wrote 0x%02X to register 0x%02X' % (value, REG_PCLT))

	# Clear status
	value = SCLR_all & 0xFF
	bus.write_byte_data(address, REG_SCLR, value)
	print ('Cleared status. Wrote 0x%02X to register 0x%02X' % (value, REG_SCLR))

	# Reset flags
	value = RST_init & 0xFF
	bus.write_byte_data(address, REG_RST, value)
	print ('Reset flags. Wrote 0x%02X to register 0x%02X' % (value, REG_RST))

	# Let the sensor initialize
	time.sleep(0.1)

	# Read temp values
	while True:
		os.system('clear')
		buf = list()
		# Request register number 0x80, 0x82 and onward
		for register in range(REG_T01L, (REG_T64H + 1), 2):
			# Let smbus handle the communication stuff
			twos_comp = bus.read_word_data(address, register)
			
			# Convert two's complement to float
			converted = AMG88xx_twos_comp_to_float(twos_comp)
			
			buf.append(converted)
			#print ('Row 139: Reg 0x%02X returned 0x%04X converted to %s' % (register, twos_comp, converted))
			
		# Statistics
		bufAvg = round(sum(buf) / len(buf), 2)
		bufMin = min(buf)
		bufMax = max(buf)
		hi = bufAvg + ((bufMax - bufAvg) / 2)
		low = bufAvg - ((bufMin - bufAvg) / 2)
		# Colorize with ANSI escape codes
		print ('Min: %s°C\tMax: %s°C\tAvg: %s°C ' % 
		('\033[96m' + str(bufMin) + '\033[0m', '\033[91m' + str(bufMax) + '\033[0m', bufAvg))
		
		# Output pixel window to terminal
		# Pixel array index
		px = 0
		# y coordinate starting on top row
		y = 1
		for r in range(0, 8):
			lstRow = list()
			# x coordinate starting on left column
			x = 1
			for c in range(px, px+8):
				#out = ('x: %d y: %d %s°C' % (x, y, buf[c]))
				#out = ('%s°C' % (buf[c]))
				out = ('%s' % (buf[c]))
				
				if buf[c] == bufMax:
					# Hottest color -red
					lstRow.append('\033[91m' + out + '\033[0m')
					
				elif buf[c] >= hi:
					# Warm color -yellow
					lstRow.append('\033[93m' + out + '\033[0m')
				
				elif buf[c] == bufMin:
					# Coldest color -cyan
					lstRow.append('\033[96m' + out + '\033[0m')
						
				elif buf[c] <= low:
					# Cool color -blue
					lstRow.append('\033[94m' + out + '\033[0m')
				else:
					# Std color
					lstRow.append(out)
					
				x += 1
				
			# Output formatted row
			print ('\t'.join(lstRow))
			print ('')
			px += 8
			y += 1
		
		#sys.exit(0)
		time.sleep(1) # Can do 10 fps (0.1) with these settings

