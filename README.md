# tsb_mission_uploader
Discord bot designed to monitor a specific Discord Channel and upload .PBO files to remote FTP Server.
Currently setup for insecure FTP

# Secure FTP and errors
To use TLS change FTP to FTP_TLS and add prot_c in method upload_to_ftp() under login
```
ftps = ftplib.FTP_TLS()
        ftps.set_debuglevel(0)  # 2 for full debug
        ftps.connect(config["FTP_HOST"], int(config["FTP_PORT"]))  # Connect with host and port
        ftps.login(config["FTP_USER"], config["FTP_PASS"]) 
        ftps.prot_c() #<------- Important to gain secure connection
        ftps.cwd(config["FTP_DIRECTORY"])
```
If you are receiving error: _ssl.c:2685 
```de-comment MyFTP_TLS class to maintain initial connection to FTP when reaching the server```
If you are receiving error: _ssl.c:1000  
```Change from secure FTP to insecure FTP (FTP_TLS --> FTP)```

# logs 
Logs are spread out over 3 log files
1. General Bot INFO
2. Error Logs
3. List of PBO's that are added to the server or are duplicates

# other features
Implemented 2 commands
1. !indexM        indexes missions and will return if they are older then 30 days and how much space it would save
2. !indexMremove  indexes missions and will remove mission that are older then 30 days.

Seperation of log files is for an extra feature (callable logs on a website)
