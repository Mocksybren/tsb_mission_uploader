import discord
import os
import json
import logging
import ftplib

# Set up logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# Load configurations from the JSON file
try:
    with open('config.json', 'r') as file:
        config = json.load(file)
    logging.info("Configuration loaded successfully.")
except Exception as e:
    logging.error(f"Error loading configuration: {e}")
    exit()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    if not os.path.exists(config["DOWNLOAD_PATH"]):
        os.makedirs(config["DOWNLOAD_PATH"])

@client.event
async def on_message(message):
    try:
        if message.channel.id == config["CHANNEL_ID"] and message.attachments:
            for attachment in message.attachments:
                # Check if the file is a .PBO file
                if attachment.filename.lower().endswith('.pbo'):
                    downloaded_file = await download_attachment(attachment)
                    upload_to_ftp(downloaded_file)
                    await message.add_reaction('✅')  # React with a checkmark for PBO files
                else:
                    logging.info(f"Skipped non-PBO file: {attachment.filename}")
                    await message.add_reaction('❌')  # React with a red X for non-PBO files
    except Exception as e:
        logging.error(f"Error processing message: {e}")



#class MyFTP_TLS(ftplib.FTP_TLS): #class for FTP_TLS (session based)| Do not forget prot_c when using this
    #"""Explicit FTPS, with shared TLS session"""
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
        logging.info(f'Downloaded {attachment.filename}!')
        return download_location
    except Exception as e:
        logging.error(f"Error downloading attachment: {e}")

def upload_to_ftp(file_path):
    try:
        filename = os.path.basename(file_path)

        ftps =  ftplib.FTP()
        ftps.set_debuglevel(0) #2 for full debug
        ftps.connect(config["FTP_HOST"], int(config["FTP_PORT"]))  # Connect with host and port
        ftps.login(config["FTP_USER"], config["FTP_PASS"])
        ftps.cwd(config["FTP_DIRECTORY"])

        # Check if the file already exists on the server
        existing_files = ftps.nlst()
        if filename in existing_files:
            logging.info(f'File {filename} already exists on the server. Skipping upload.')
            # You can remove the file from local storage even if it's not uploaded
            os.remove(file_path)
            logging.info(f'Deleted {filename} from local storage.')
        else:
            with open(file_path, 'rb') as f:
                ftps.storbinary(f'STOR {filename}', f)
            ftps.quit()  # Properly close the connection
            logging.info(f'Uploaded {filename} to FTP!')
            # Delete the file after successful upload
            os.remove(file_path)
            logging.info(f'Deleted {filename} from local storage.')
    except Exception as e:
        logging.error(f"Error in upload_to_ftp: {e}")

try:
    client.run(config["TOKEN"])
except Exception as e:
    logging.error(f"Error starting bot: {e}")
