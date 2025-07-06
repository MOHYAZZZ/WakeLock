import PyInstaller.__main__

PyInstaller.__main__.run([
    'wakelock.py',              
    '--onefile',                
    '--noconsole',              
    '--icon=wakelock.ico',      
    '--name=WakeLock',          
    '--add-data=wakelock.ico;.', 
    '--clean'                   
])
