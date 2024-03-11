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
                        await message.add_reaction('✅')     # React with a checkmark for PBO files
                    elif dupeflag:
                        await message.add_reaction('♻')     # React with a recycle mark for duplicates
                else:
                    botlogger.info(f"Skipped non-PBO file: {attachment.filename}")
                    await message.add_reaction('❌')  # React with a red X for non-PBO files
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


try:
    client.run(config["TOKEN"])
except Exception as e:
    errorlog.error(f"Error starting bot: {e}")
