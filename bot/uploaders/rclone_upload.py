from configparser import ConfigParser
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from bot import SessionVars
from bot.utils.rename_file import rename
from ..core.get_vars import get_val
from bot.utils.get_rclone_conf import get_config
import os
import logging
import subprocess
import asyncio
import re
from bot import rcprocess
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .progress_for_rclone import status

log = logging.getLogger(__name__)


class RcloneUploader():

    def __init__(self, path, user_msg, new_name, is_rename= False):
        super().__init__()
        self._path = path
        self._is_rename= is_rename
        self._user_msg = user_msg
        self._new_name= new_name
        self._rclone_pr = None
        self.dest_base= None

    async def execute(self):
        old_path = self._path
        new_name= self._new_name
        is_rename= self._is_rename

        dest_drive = get_val("DEF_RCLONE_DRIVE")

        conf_path = await get_config()
        conf = ConfigParser()
        conf.read(conf_path)
        general_drive_name = ""

        for i in conf.sections():
            if dest_drive == str(i):
                if conf[i]["type"] == "drive":
                    self.dest_base = get_val("BASE_DIR")
                    log.info("Google Drive Upload Detected.")
                else:
                    general_drive_name = conf[i]["type"]
                    self.dest_base = get_val("BASE_DIR")
                    log.info(f"{general_drive_name} Upload Detected.")
                break

        if not os.path.exists(old_path):
            await self._user_msg.reply("the path {path} not found")
            return 

        if is_rename:
            path = await rename(old_path, new_name)
        else:
            path= old_path    
            
        if os.path.isdir(path):
            #new_dest_base = os.path.join(self.dest_base, os.path.basename(path))
            new_dest_base = self.dest_base
            logging.info(new_dest_base)
            rclone_copy_cmd = ['rclone', 'copy', f'--config={conf_path}', str(path),
                                    f'{dest_drive}:{new_dest_base}', '-P']

            
            log.info(f'{dest_drive}:{new_dest_base}')
            log.info("Uploading...")

            rclone_pr = subprocess.Popen(
                rclone_copy_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            rcprocess.append(rclone_pr)
            self._rclone_pr = rclone_pr
            rcres= await self.rclone_process_update()

            # if(await self.check_errors(rclone_pr, self._user_msg)):
            #     return
        
            if rcres:
                rclone_pr.kill()
                log.info("subida cancelada")
                await self._user_msg.edit("Subida cancelada")
                return 
            
            log.info("subida exitosa")
            await self._user_msg.edit("Subida exitosa ✅")

        else:
            new_dest_base = self.dest_base
            logging.info(new_dest_base)
            rclone_copy_cmd = ['rclone', 'copy', f'--config={conf_path}', str(path),
                                    f'{dest_drive}:{new_dest_base}', '-P']
            
            log.info(f'{dest_drive}:{new_dest_base}')
            log.info("Uploading...")

            rclone_pr = subprocess.Popen(
                rclone_copy_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            rcprocess.append(rclone_pr)
            self._rclone_pr = rclone_pr
            rcres= await self.rclone_process_update()

            # if(await self.check_errors(rclone_pr, self._user_msg)):
            #     return
        
            if rcres:
                rclone_pr.kill()
                log.info("subida cancelada")
                await self._user_msg.edit("Subida cancelada")
                return 
            
            log.info("subida exitosa")
            await self._user_msg.edit("Subida exitosa ✅")


    async def rclone_process_update(self):
        blank=0    
        process = self._rclone_pr
        user_message = self._user_msg
        sleeps = False
        #start = time.time()
        msg = ""
        msg1 = ""
        #edit_time = get_val("EDIT_SLEEP_SECS")
        
        while True:
            data = process.stdout.readline().decode()
            data = data.strip()
            mat = re.findall("Transferred:.*ETA.*",data)
           
            if mat is not None:
                if len(mat) > 0:
                    sleeps = True
                    #if time.time() - start > edit_time:
                        #start = time.time()
                    nstr = mat[0].replace("Transferred:","")
                    nstr = nstr.strip()
                    nstr = nstr.split(",")
                    percent = nstr[1].strip("% ")
                    try:
                        percent = int(percent)
                    except:
                        percent = 0
                    prg = status(percent)

                    msg = "<b>Subiendo...\n{} \n{} \nVelocidad:- {} \nETA:- {}</b>".format(nstr[0],prg,nstr[2],nstr[3].replace("ETA",""))
                    
                    if msg1 != msg:
                        try:
                            await user_message.edit(text= msg, reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("Cancel", callback_data= "upcancel")]]))    
                            msg1= msg
                        except MessageNotModified as e: 
                            log.info( e)  
                            pass                                
                        
            if data == "":
                blank += 1
                if blank == 20:
                    break
            else:
                blank = 0

            if sleeps:               
                sleeps= False
                if get_val("UP_CANCEL"):
                    SessionVars.update_var("UP_CANCEL", False)
                    return True
                await asyncio.sleep(2)
                process.stdout.flush()    

    # async def check_errors(self, rclone, usermsg):
    #     blank = 0
    #     while True:
    #         data = rclone.stderr.readline().decode()
    #         data = data.strip()
    #         if data == "":
    #             blank += 1
    #             if blank == 5:
    #                 break
    #         else:
    #             mat= data
    #             if mat is not None:
    #                 if len(mat) > 0:
    #                     log.info(f'Error:-{mat}')
    #                     await usermsg.edit(mat)
    #                     return True            

   
