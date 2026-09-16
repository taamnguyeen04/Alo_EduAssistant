import math, numpy as np
FUNCTIONS={
'x^2':{'fn':lambda x:x**2,'df':lambda x:2*x,'latex':r'x^2'},
'x^3':{'fn':lambda x:x**3,'df':lambda x:3*x**2,'latex':r'x^3'},
'sin(x)':{'fn':np.sin,'df':np.cos,'latex':r'\sin x'},
'cos(x)':{'fn':np.cos,'df':lambda x:-np.sin(x),'latex':r'\cos x'},
'e^x':{'fn':np.exp,'df':np.exp,'latex':r'e^x'},
}
EXTREMA_FUNCTIONS={
'x^3-3x':{'fn':lambda x:x**3-3*x,'df':lambda x:3*x**2-3,'latex':r'x^3-3x','critical':[(-1.0,'max'),(1.0,'min')],'x_range':[-2.25,2.25],'y_range':[-3.5,3.5]},
'sin(x)':{'fn':np.sin,'df':np.cos,'latex':r'\sin x','critical':[(-math.pi/2,'min'),(math.pi/2,'max')],'x_range':[-math.pi,math.pi],'y_range':[-1.5,1.5]},
}
def clean_num(x,digits=2):
    if abs(x-round(x))<10**(-digits): return str(int(round(x)))
    return f'{x:.{digits}f}'.rstrip('0').rstrip('.')
