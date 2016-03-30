"""
Library to handle all functionalities of the gyro
This includes reading and integrating the reading
"""
import numpy as np
from numpy.linalg import inv
import math
import smbus
import time

bus = None 	
address = None

def get_IMU_reading():
	"""
	Gets the IMU reading based on the circuit diagram
	IMU used is MPU 9255. 
	Please refer to: <link> for more details of our project

	The IMU will comminucate with the raspberry via address 0x68 (for our case)
	Based on data sheet, we write / read from the addresses:
	Accelerometer: 0x3b - 0x3e 
	Gyro: 0x43 - 0x48 

	Once we read the data, we have to scale it based on the proper value

	param: None
	rtype: np.array of reading from (gryo_x, gryo_y, gryo_z, accel_x, accel_y, accel_z)
	"""
        global bus
        global address
	
	power_mgmt_1 = 0x6b
	power_mgmt_2 = 0x6c
	bus = smbus.SMBus(1)            # I2C port 1
	address = 0x68 		        # This is the address value via the i2cdetect command or chip user guide
	SCALEa = 65536.0/4		# Scaling of accel and gyro readings 
	SCALEg = 32.8

	#Now wake the MPU 9255 up as it starts in sleep mode
	bus.write_byte_data(address, power_mgmt_1, 0)

	accel_xout = __read_word_2c(0x3b)
	accel_yout = __read_word_2c(0x3d)
	accel_zout = __read_word_2c(0x3f)

	accel_xout_scaled = accel_xout / SCALEa
	accel_yout_scaled = accel_yout / SCALEa
	accel_zout_scaled = accel_zout / SCALEa	

	gyro_xout = __read_word_2c(0x43)
	gyro_yout = __read_word_2c(0x45)
	gyro_zout = __read_word_2c(0x47)

	gyro_xout_scaled = gyro_xout / SCALEg
	gyro_yout_scaled = gyro_yout / SCALEg
	gyro_zout_scaled = gyro_zout / SCALEg	

	return np.array([gyro_xout_scaled, gyro_yout_scaled, gyro_zout_scaled, accel_xout, accel_yout, accel_zout])

def __read_word(adr):
	high = bus.read_byte_data(address, adr)
	low = bus.read_byte_data(address, adr+1)
	val = (high << 8) + low
	return val

def __read_word_2c(adr):
	val= __read_word(adr)
	if (val >= 0x8000):
		return - ((65535 - val) + 1)
	else:
		return val

def get_integrate_gyro(gyro_reading, smpl_time):
	"""
	Integrates the gyro reading given a sampling time.
	Integration is performed numerically

	param: 	gyro_reading -> numpy.ndarray type that is the reading of the angular velocities
			smpl_time -> float type that is the sampling rate of the IMU

	rtype:	numpy.ndarray type that is the result after performing integration 
	"""
	assert type(gyro_reading) is np.ndarray and type(smpl_time) is float
	return gyro_reading*smpl_time

def get_state_accel(accel_reading):
	"""
	Gets the state of the system based on accelerometer readings
	"""
	pass

def kalman_filter(F, B, R, Q, u_k, x_km1_km1, z_k):
	"""
	Function to implement the Kalman kalman filter.
	Assumptions made are that the distribution of the system is gaussian with mean and variance
	All bias from accelerometer and gyro are assumed to be constant

	Theory:
	Assume that systems true state at time k given state at time k-1 is modelled as:
	>>> x_k_km1 = F*x_km1_km1 + B*u_k + w_k
	Where w_k is the process noise 

	The measured value of the system at time k relates to x_k_km1 by:
	>>> z_k = H*x_k_km1 + v_k
	v_k is the noise 

	Start by calculating x_k_km1 ignoring the noise present
	>>> x_k_km1 = F*x_km1_km1 + B*u_k

	Calculate the innovation (y_k) using
	>>> y_k = z_k - H*x_k_km1

	Calculate the error covariance matrix P_k_km1 using
	>>> P_k_km1 = F *P_km1_km1 *F' + Q

	Calculate the innovation covariance matrix using
	>>> S_k = H *P_k_km1 *H' + R

	Calculate the kalman gain using
	>>> K_k = P_k_km1 *H' *inv(S_k)

	Calculate the true state x_k_k using
	>>> x_k_k = x_k_km1 + K_k *y_k

	Calculate the error covariance matrix at time k 
	>>> P_k_k = (I - K_k *H) *P_k_km1

	param: 	F: State transition matrix 							- 2 x 2
			B: Mapping matrix for control input					- 2 x 1
			R: Measurement covariance matrix 					- 1 x 1			
			Q: Noise covariance matrix 							- 2 x 2
			u_k: measured angular velocity at time k 			- 1 x 1
			x_km1_km1: The true state of the system at time k-1	- 2 x 1
			z_k: The measured state of the system at time k 	- 1 x 1

	rtype: 	x_k_k: The true state of the system at time k
			P_k_k: The error covariance matrix at time k
	"""
	H = np.matrix([1, 0])			# Maps true state to measured reading

	x_k_km1 = F*x_km1_km1 + B*u_k	
	y_k = z_k - H*x_k_km1			
	P_k_km1 = F *P_km1_km1 *np.transpose(F) + Q
	S_k = H *P_k_km1 *np.transpose(H) + R
	K_k = P_k_km1 *np.transpose(H) *inv(S_k)
	x_k_k = x_k_km1 + K_k *y_k
	P_k_k = (np.identity(3) - K_k *H) *P_k_km1

	return x_k_k, P_k_k
