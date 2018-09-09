import numpy as np
import pandas as pd
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
    z = z*math.e**(1.0j*p*math.pi)
    z = z.apply(lambda y: np.angle(y))
    z = pd.DataFrame(np.unwrap(z,discont=np.pi,axis=1), index = z.index, columns = z.columns)
    return z

def real_fancy(v, x, y, p):
    '''
    real((v[0]-... + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0]-np.mean(v[0],0) + 1.0j*(v[1]-np.mean(v[1],0))
    z = z*math.e**(1.0j*p*math.pi)
    z = z.apply(lambda x: np.real(x))
    return z

def real(v, x, y, p):
    '''
    real((v[0] + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z = z*math.e**(1.0j*p*math.pi)
    z = z.apply(lambda x: np.real(x))
    return z
   
def imag(v, x, y, p):
    '''
    imag((v[0] + i v[1])*e^(i*p*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    z = z*math.e**(1.0j*p*math.pi)
    z = z.apply(lambda x: np.imag(x))
    return z

#def detrend(v, x, y, p):
#    '''
#    '''

def real_detrend(v, x, y, p):
    '''
    real((v[0] + i v[1])*e^(i*p*x*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    a = pd.Series(x.values,x.values)
    a = math.e**(a.apply(lambda y: 1.0j*p*y*math.pi))
    z = z*a
    z = z.apply(lambda y: np.real(y))
    return z

def imag_detrend(v, x, y, p):
    '''
    imag((v[0] + i v[1])*e^(i*p*x*pi))
    
    '''
    z = v[0] + 1.0j*v[1]
    a = pd.Series(x.values, x.values)
    a = math.e**(a.apply(lambda y: 1.0j*p*y*math.pi))
    z = z*a
    z = z.apply(lambda y: np.imag(y))
    return z

def phase_detrend(v, x, y, p):
    '''
    phase((v[0] + i v[1])*e^(i*p*x*pi))
    '''
    z = v[0] + 1.0j*v[1]
    a = pd.Series(x.values,x.values)
    a = math.e**(a.apply(lambda y: 1.0j*p*y*math.pi))
    z = z*a
    z = z.apply(lambda y: np.angle(y))
    return z
    
def phase_detrend_unwrap_reverse(v, x, y, p):
    '''
    unwrap_rev(phase((v[0] + i v[1])*e^(i*p*x*pi)))
    '''
    z = v[0]+1.0j*v[1]
    a = pd.Series(x.values,x.values)
    a = math.e**(a.apply(lambda y: 1.0j*p*y*math.pi))
    z = z*a
    z = z.apply(lambda y: np.angle(y)).iloc[:,::-1]
    z = pd.DataFrame(np.unwrap(z,discont=np.pi, axis=1), index=z.index, columns = z.columns).iloc[:,::-1]
    return z
    
def phase_detrend_unwrap(v, x, y, p):
    '''
    unwrap(phase((v[0] + i v[1])*e^(i*p*x*pi)))
    '''
    z = v[0] + 1.0j*v[1]
    a = pd.Series(x.values,x.values)
    a = math.e**(a.apply(lambda y: 1.0j*p*y*math.pi))
    z = z*a
    z = z.apply(lambda y: np.angle(y))
    z = pd.DataFrame(np.unwrap(z,discont=np.pi, axis=1), index=z.index, columns = z.columns)
    return z
    
def moving_average(v, x, y, p):
    '''
    moving average of length p
    '''
    p = max(1, min(v[0].shape[1], int(p)))
    mask = np.ones((p,))
    w = 1./np.convolve(np.ones_like(v[0].iloc[0,:]), mask, mode='same')
    for index, row in v[0].iterrows():
        v[0].loc[index,:] = np.convolve(row, mask, mode='same')     
    return w*v[0]