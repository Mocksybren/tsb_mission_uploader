import datetime
import discord
import os
import json
import logging
import ftplib

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')      # Default format
dupeflag = bool
# setup for multiple loggers


def setup_logger(name, log_file, level=logging.INFO):

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Set up logging
# logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')


# Creation of multple logger files
botlogger = setup_logger('botlog', 'bot.log')
pbologger = setup_logger('pbolog', 'pbolog.log')
errorlog = setup_logger('errorlog', 'errorlog.log')


# Load configurations from the JSON file
try:
    with open('config.json', 'r') as file:
        config = json.load(file)
    botlogger.info("Configuration loaded successfully.")
except Exception as e:
    errorlog.error(f"Error loading configuration: {e}")
    exit()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    botlogger.info(f'Logged in as {client.user}')
    if not os.path.exists(config["DOWNLOAD_PATH"]):
        os.makedirs(config["DOWNLOAD_PATH"])


@client.event
async def on_message(message):
    global dupeflag
    try:
        if message.channel.id == config["CHANNEL_ID"] and message.attachments:
            for attachment in message.attachments:
                # Check if the file is a .PBO file
                if attachment.filename.lower().endswith('.pbo'):
                    downloaded_file = await download_attachment(attachment)
                    upload_to_ftp(downloaded_file)
                    if not dupeflag:
                        await message.add_reaction('✅')  # React with a checkmark for PBO files
                        # ☑️
                    elif dupeflag:
                        await message.add_reaction('♻')     # React with a recycle mark for duplicates
                else:
                    botlogger.info(f"Skipped non-PBO file: {attachment.filename}")
                    await message.add_reaction('❌')  # React with a red X for non-PBO files
        elif "!indexM" in message.content: # Invoke indexing when reading !indexM
            await index_mission_files(message)
    except Exception as e:
        errorlog.error(f"Error processing message: {e}")


# class MyFTP_TLS(ftplib.FTP_TLS): #class for FTP_TLS (session based)| Do not forget prot_c when using this
    # """Explicit FTPS, with shared TLS session"""
#   def ntransfercmd(self, cmd, rest=None):
#        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
#        if self._prot_p:
#            conn = self.context.wrap_socket(conn,
#                                            server_hostname=self.host,
#                                            session=self.sock.session)  # this is the fix
#        return conn, size
async def download_attachment(attachment):
    try:
        download_location = os.path.join(config["DOWNLOAD_PATH"], attachment.filename)
        await attachment.save(download_location)
        # logger.info(f'Downloaded {attachment.filename}!')
        return download_location
    except Exception as e:
        errorlog.error(f"Error downloading attachment: {e}")


def upload_to_ftp(file_path):
    global dupeflag
    try:
        filename = os.path.basename(file_path)

        botlogger.info(f"Starting FTP for {filename}")

        ftps = ftplib.FTP()
        ftps.set_debuglevel(0)  # 2 for full debug
        ftps.connect(config["FTP_HOST"], int(config["FTP_PORT"]))  # Connect with host and port
        ftps.login(config["FTP_USER"], config["FTP_PASS"])
        ftps.cwd(config["FTP_DIRECTORY"])

        # Check if the file already exists on the server
        existing_files = ftps.nlst()
        if filename in existing_files:
            # logger.info(f'File {filename} already exists on the server. Skipping upload.')
            # You can remove the file from local storage even if it's not uploaded
            os.remove(file_path)
            dupeflag = True
            pbologger.info(f' {filename} already exists on server')
            # logger.info(f'Deleted {filename} from local storage.')
            botlogger.info("FTP aborted due to duplicate .PBO file")
            return dupeflag
        else:
            with open(file_path, 'rb') as f:
                ftps.storbinary(f'STOR {filename}', f)
            ftps.quit()  # Properly close the connection
            dupeflag = False
            # logger.info(f'Uploaded {filename} to FTP!')
            # Delete the file after successful upload
            pbologger.info(f' {filename} has been uploaded')
            os.remove(file_path)
            # logger.info(f'Deleted {filename} from local storage.')
            botlogger.info(f"FTP success PBO file {filename} on server")
            return dupeflag
    except Exception as e:
        errorlog.error(f"Error in upload_to_ftp: {e}")


async def index_mission_files(message):
    i = 0
    mb_size_collection = 0
    mb_deleted = 0
    mission_to_delete_list = ()
    try:
        current_date = datetime.date.today() - datetime.timedelta(30) # Get date of index_mission_files invoked and go back 30 days
        botlogger.info("Starting Index of mission Files")

        ftps = ftplib.FTP()
        ftps.set_debuglevel(0)  # 2 for full debug
        ftps.connect(config["FTP_HOST"], int(config["FTP_PORT"]))  # Connect with host and port
        ftps.login(config["FTP_USER"], config["FTP_PASS"])
        ftps.cwd(config["FTP_DIRECTORY"])

        if config["FTP_MODERN"] == 1:
            ls = ftps.mlsd()    # List files in directory
            formatted_date = current_date.strftime("%Y%m%d")  # Format to easy comparison

            for entry in ls:
                if entry[0].lower().startswith('msn') & entry[0].lower().endswith('.pbo'): # if starts with msn and ends with .pbo
                    i = i+1
                    ymd = entry[1].get('modify')[:8] # Get first 8 numbers for date from last modified.
                    size = int(entry[1].get('size'))    # Get Size of file
                    mb_size = str(round((size/1000/1000), 3))   # Transfer it to Mb
                    mb_size_collection = mb_size_collection + float(mb_size)    # Add to total Mb count
                    if ymd < formatted_date and ymd != 0:   # Check if file is older then 30 days
                        mission_to_delete_list += (entry[0],)   # Add file name to to delete list
                        mb_deleted += float(mb_size)    # Save how much Mb it will save

        elif config["FTP_MODERN"] == 0:
            ls = ftps.nlst()
            formatted_date = current_date.strftime("%Y%m%d")

            for entry in ls:
                Mfile = ftps.voidcmd(f"MDTM {entry}")
                if entry.lower().startswith("msn") & entry.lower().endswith(".pbo"): # if starts with msn and ends with .pbo
                    i = i+1
                    print(entry)
                    ymd = Mfile[4:12] # Get first 8 numbers for date from last modified.
                    size = int(ftps.size(entry))    # Get Size of file
                    mb_size = str(round((size/1000/1000), 3))   # Transfer it to Mb
                    mb_size_collection = mb_size_collection + float(mb_size)    # Add to total Mb count
                    if ymd < formatted_date and ymd != 0:   # Check if file is older then 30 days
                        mission_to_delete_list += (entry,)   # Add file name to to delete list
                        mb_deleted += float(mb_size)    # Save how much Mb it will save

        if message.content == "!indexM" and i != 0: # Only index of files in directory
            await message.channel.send(f'{i} Indexed with total amount: {mb_size_collection} Mb ')
            await message.channel.send(f'{len(mission_to_delete_list)} are 30 days or older')
            ftps.quit()  # Close Connection
        elif message.content == "!indexMremove" and len(mission_to_delete_list) != 0:   # Index and Delete files older then 30 days
            await message.channel.send(f'Removing {len(mission_to_delete_list)} files of size amount {mb_deleted} Mb')
            await remove_mission_files(mission_to_delete_list, ftps)    # Invoke remove_mission_files with existing ftp connection made in Index
        else:
            await message.channel.send(f'No missions found')    # No MSN files detected
            ftps.quit()  # Close Connection

    except Exception as e:
        errorlog.error(f"Error in index_mission_files: {e}")


async def remove_mission_files(mission_to_delete_list, ftps):
    try:
        for item in mission_to_delete_list:
            ftps.delete(item)   # Delete files from ftp server from mission_to_delete_list
        ftps.quit() # Close connection

    except Exception as e:
        errorlog.error(f"Error in remove_mission_files: {e}")

try:
    client.run(config["TOKEN"])
except Exception as e:
    errorlog.error(f"Error starting bot: {e}")
