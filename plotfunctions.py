import numpy as np
import math

def abs_value(v, x, y, p):
    '''
    abs(v[0] + i v[1])
    
    '''
    z = v[0] + 1.0j*v[1]
    return np.abs(z)

def abs_fancy(v, x, y, p):
    '''
    abs((v[0]-<v[0]>) + i )v[1]-<v[1]>))
    
    '''
    z = v[0]-np.mean(v[0],0) + 1.0j*(v[1]-np.mean(v[1],0))
    return np.abs(z)
    
def abs_fancy2(v, x, y, p):
    '''
    abs(v)-<abs(v)>
    
    '''
    z = np.sqrt(v[0]**2 + v[1]**2) - np.mean(np.sqrt(v[0]**2 + v[1]**2), 0)
    return z
    
def abs_dB(v, x, y, p):
    '''
    20*log10(abs(v[0] + i v[1]))
    
    '''
    z = v[0] + 1.0j*v[1]
    return 20*np.log10(np.abs(z))

def phase(v, x, y, p):
    '''
    phase((v[0] + i v[1])e^(i*p*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    return np.unwrap(np.angle(z*math.e**(1.0j*p*math.pi)))

def real_fancy(v, x, y, p):
    '''
    real((v[0]-... + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0]-np.mean(v[0],0) + 1.0j*(v[1]-np.mean(v[1],0))
    z *= math.e**(1.0j*p*math.pi)
    return np.real(z)

def real(v, x, y, p):
    '''
    real((v[0] + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z *= math.e**(1.0j*p*math.pi)
    return np.real(z)
   
def imag(v, x, y, p):
    '''
    imag((v[0] + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z *= math.e**(1.0j*p*math.pi)
    return np.imag(z)

#def detrend(v, x, y, p):
#    '''
#    '''

def real_detrend(v, x, y, p):
    '''
    real((v[0] + i v[1])*e^(i*p*x*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z *= math.e**(1.0j*p*x*math.pi)
    return np.real(z)

def imag_detrend(v, x, y, p):
    '''
    imag((v[0] + i v[1])*e^(i*p*x*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z *= math.e**(1.0j*p*x*math.pi)
    return np.imag(z)

def phase_detrend(v, x, y, p):
    '''
    phase((v[0] + i v[1])*e^(i*p*x*pi))
    '''
    z = v[0] + 1.0j*v[1]
    return np.angle(z*math.e**(1.0j*p*x*math.pi))
    
def phase_detrend_unwrap_reverse(v, x, y, p):
    '''
    unwrap_rev(phase((v[0] + i v[1])*e^(i*p*x*pi)))
    '''
    z = v[0] + 1.0j*v[1]
    return np.unwrap(np.angle(z*math.e**(1.0j*p*x*math.pi))[:,::-1], discont=np.pi, axis=1)[:,::-1]
    
def phase_detrend_unwrap(v, x, y, p):
    '''
    unwrap(phase((v[0] + i v[1])*e^(i*p*x*pi)))
    '''
    z = v[0] + 1.0j*v[1]
    return np.unwrap(np.angle(z*math.e**(1.0j*p*x*math.pi)), discont=np.pi, axis=1)
    
def moving_average(v, x, y, p):
    '''
    moving average of length p
    '''
    p = max(1, min(v[0].shape[0], p))
    mask = np.ones((p,))
    w = 1./np.convolve(np.ones_like(v[0][0]), mask, mode='same')
    z = [np.convolve(a, mask, mode='same') for a in v[0]]
    return w*np.array(z)