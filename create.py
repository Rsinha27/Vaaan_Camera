import subprocess
from subprocess import Popen
import os, sys
import threading
import time
from .global_file import ll
from . import global_file as gf
from datetime import datetime
import pytz
import os, signal
import onvif
import json
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
import requests
import time
import re




try:
    with open("vms_configurations.json", "r") as f:
        data_dict = json.load(f)
except Exception as e:
    print("In create file: ", e)

def extract_ip(path):
    ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    
   
    match = re.search(ip_pattern, path)
    
    if match:
        return match.group(0)
    else:
        return None


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, queue, max_queue_size=50):
        super().__init__()
        self.queue = queue
        self.max_queue_size = max_queue_size
        self.thread = None

    def create_10sec_video(self, event_time, cam_ip):
        global data_dict

        try:
            clip_path = data_dict["server_clip_url"]

            ip = cam_ip.replace('.', '')[6:]
            time.sleep(1)
            date = datetime.now().strftime("%d%m%y%H%M%S")
          
            reference_no = ip + date

           
            data = {
                     "reference_no": reference_no,
                     "camera": cam_ip,
                     "timestamp": event_time.strftime("%d-%b-%Y %H:%M:%S"),
                     "video_type": "Short",
                     "video_url": clip_path+output_video,
                     "image_url": clip_path+output_image
                   }
        except Exception as e:
            pass

    def on_created(self, event):
        if event.is_directory:
            return
        
        if self.queue.qsize() < self.max_queue_size:
            base_name, ext = os.path.splitext(event.src_path)
            if ext == '.sdv':
                print("File received..")
                print("Event file: ", event.src_path)
                path = event.src_path
                ip_address = extract_ip(path)
                print(f'Extracted IP address: {ip_address}')

                motion_detect_time = datetime.now()
                print("time: ", motion_detect_time)
                motion_data = (motion_detect_time, event.src_path)

                self.thread = threading.Thread(target=self.create_10sec_video, args=(motion_detect_time, ip_address,))
                self.thread.daemon = True
                self.thread.start()

                last_size = -1
                time.sleep(15)
                current_size = os.path.getsize(event.src_path)
                print("Size: ", last_size, current_size)
                while True:
                    current_size = os.path.getsize(event.src_path)
                    print("Size in loop: ", last_size, current_size)
                    if current_size == last_size:
                        self.queue.put(motion_data)
                        print("file added: ", event.src_path)
                        break
                    last_size = current_size
                    time.sleep(5)
            elif ext == '.jpg':
                try:
                    if os.path.exists(event.src_path):
                        os.remove(event.src_path)
                except:
                    pass
        else:
            # Discard files if the queue is full
            print(f"Queue is full. Discarding file: {event.src_path}")


"""This class is used to create camera objects to display live stream and recordings,
    it is also used to manage recordings files by deleting them at the given time"""
class CameraStream:
    
    def __init__(self, device_name, username, password, ip_address, storage_days):
        global data_dict

        print("in cam: ", gf.current_dir, device_name)
        self.cam_name = device_name
        self.username = username
        self.password = password
        self.cam_ip = ip_address
        self.storage_days = storage_days
       
        self.p3 = None
       
        self.p3_id = None

        self.change_storage_folder = False
        self.to_delete_files = False

        self.recordings_list = []

      
        
        self.recordings_folder_list = [f"videos/Recordings1/{self.cam_name}",
                                       f"videos/Recordings2/{self.cam_name}",
                                       f"videos/Recordings3/{self.cam_name}",
                                       f"videos/Recordings4/{self.cam_name}",
                                       f"videos/Recordings5/{self.cam_name}"]
        
      

        self.motion_detection_folder = data_dict["Motion_detection_folder"]
        self.motion_detection_folder = self.motion_detection_folder + '/' + self.cam_ip
        if not os.path.exists(self.motion_detection_folder):
            os.mkdir(self.motion_detection_folder)

        self.motion_folder = f"videos/MotionDetection/{self.cam_ip}"
        try:
            if not os.path.exists(self.motion_folder):
                os.mkdir(self.motion_folder)
                if os.path.exists(self.motion_folder):
                    os.mkdir(self.motion_folder+'/Videos')
                    os.mkdir(self.motion_folder+'/Images')
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        self.queue = Queue(maxsize=50)

        try:
            for key in data_dict["Recordings_drive"].keys():
                if data_dict["Recordings_drive"][key] != "None":
                    folder = self.recordings_folder_list[int(key)-1]
                    if not os.path.exists(folder):
                        os.mkdir(folder)
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        try:
            self.directory1 = f"videos/Recordings1/{self.cam_name}"
            self.directory2 = f"videos/Recordings2/{self.cam_name}"
            self.directory3 = f"videos/Recordings3/{self.cam_name}"
            self.directory4 = f"videos/Recordings4/{self.cam_name}"
            self.directory5 = f"videos/Recordings5/{self.cam_name}"
           
        except Exception as e:
            print("Looking for me? ", e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)



        mycam = onvif.ONVIFCamera(self.cam_ip, 80, self.username, self.password)

        media = mycam.create_media_service()
        profiles = media.GetProfiles()
        if not profiles:
            print("No media profiles found.")
            return

        """Extracting primary stream URI"""
        media_profile_1 = profiles[0]
        profile_token_1 = media_profile_1.token  # Extracting the token from the media profile

        stream_uri_1 = media.GetStreamUri(
            {'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
             'ProfileToken': profile_token_1}
        )

        self.video_stream_uri_1 = stream_uri_1.Uri
        print("Video Stream URI primary:", self.video_stream_uri_1)
        self.video_stream_uri_1 = "rtsp://{}:{}@{}".format(self.username, self.password, self.video_stream_uri_1[7:])

    
        t = threading.Thread(target=self.maintain_recordings, args=())
        t.daemon = True
        t.start()

        watch_thread = threading.Thread(target=self.watch_motion_folder, args=(self.motion_detection_folder,))
        watch_thread.daemon = True  # Daemonize the thread so it terminates with the main thread
        watch_thread.start()

        process_files_thread = threading.Thread(target=self.process_files, args=())
        process_files_thread.daemon = True
        process_files_thread.start()

       
        self.recording = f"ffmpeg -loglevel error -use_wallclock_as_timestamps 1 -rtsp_transport tcp -i {self.video_stream_uri_1} -vcodec copy -acodec aac -f segment -reset_timestamps 1 -segment_time 1800 -segment_format mp4 -segment_atclocktime 1 -strftime 1 videos/Recordings{gf.current_dir}/{self.cam_name}/%Y%m%dT%H%M%S.mp4".split(" ")
      

        self.start()

      

    def start(self):

      
        if gf.current_drive not in ["None", None]:
            self.p3 = Popen(self.recording)
        time.sleep(2)
       
        if gf.current_drive not in ["None", None]:
            self.p3_id = self.p3.pid
            print("Assigned 2: ", self.p3_id, self.cam_name)

       

    def terminate_process(self):
        print("you have awakened me! ", self.cam_name)
        
        try:
            try:
                
                if gf.current_drive not in ["None", None]:
                    print("In terminate 2: ", self.p3_id)
                    os.kill(int(self.p3_id), signal.SIGKILL)
                print("terminated by process id!")

               

            except:
                print("could not delete by process id!")
           
        except Exception as e:
            print("Failed to stop ffmpeg: ", e)


  


    def get_current_ist(self):
        # Set the time zone to Indian Standard Time (IST)
        ist_timezone = pytz.timezone('Asia/Kolkata')

        # Get the current time in IST
        current_time_ist = datetime.now(ist_timezone)

        # Format the current time as per "%Y%m%dT%H%M%S" format
        formatted_time = current_time_ist.strftime("%Y%m%dT%H%M%S")

        return formatted_time


    def calculate_time_difference(self, date_string1, date_string2):
        # Parse the input date strings using the specified format
        date_format = "%Y%m%dT%H%M%S"
        date1 = datetime.strptime(date_string1, date_format)
        date2 = datetime.strptime(date_string2, date_format)

        # Calculate the time difference
        time_difference = date2 - date1

        # Extract the difference in minutes
        minutes_difference = time_difference.total_seconds() / 60

        return minutes_difference


    
    def get_process_id(self):
        while True:
            try:
              
                if gf.current_drive not in ["None", None]:
                    self.p3_id = self.p3.pid
                break
            except Exception as e:
                print(e)
                print("No.....")

            


    def maintain_recordings(self):
      

        while True:
            file_names = []

            self.recordings_list = []
            
            for directory in self.recordings_folder_list:
                try:
                    for file_name in os.listdir(directory):
                        file_path = os.path.join(directory, file_name)
                        if os.path.isfile(file_path):
                            self.recordings_list.append(file_path)

                   
                    for item in self.recordings_list:
                        item = item.split("/")
                        item = item[-1].split(".")[-2]
                        file_names.append(item)
                    

                except Exception as e:
                   
                    pass                                        


                current_ist = self.get_current_ist()

                if len(file_names) >= 1:
                    if gf.current_drive not in ["None", None]:
                   
                        try:
                           
                            if self.change_storage_folder:
                                try:
                                    os.kill(int(self.p3_id), signal.SIGKILL)
                                except:
                                    pass

                               
                                self.recording = f"ffmpeg -loglevel error -use_wallclock_as_timestamps 1 -rtsp_transport tcp -i {self.video_stream_uri_1} -vcodec copy -acodec aac -f segment -reset_timestamps 1 -segment_time 1800 -segment_format mp4 -segment_atclocktime 1 -strftime 1 videos/Recordings{gf.current_dir}/{self.cam_name}/%Y%m%dT%H%M%S.mp4".split(" ")
                                
                                
                                self.p3 = Popen(self.recording)
                                time.sleep(2)
                                print("process id in start: ", self.p3.pid)
                                self.p3_id = self.p3.pid

                                self.change_storage_folder = False

                        except Exception as e:
                            print("In a new folder: ", e)


                     
                        try:
                            if self.to_delete_files:
                                self.recordings_list = sorted(self.recordings_list)

                                
                                num_files_to_delete = int(len(self.recordings_list) * 0.1)

                                
                                for i in range(num_files_to_delete):
                                    os.remove(self.recordings_list[i])

                                self.to_delete_files = False

                        except Exception as e:
                            print(e)
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            print(exc_type, fname, exc_tb.tb_lineno)

                    try:
                        for item in file_names:
                            item_time = item
                            minutes_difference = self.calculate_time_difference(item_time, current_ist)
                           

                            if int(minutes_difference) > (self.storage_days*24*60):
                                print("deleting: ", directory + "/" + item + ".mp4")
                                to_delete = directory + "/" + item + ".mp4"
                                os.remove(to_delete)
                                del to_delete
                    except Exception as e:
                        print("Exception", e)
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)


            time.sleep(1000)
           


    def watch_motion_folder(self, folder_path):
        try:
           
            event_handler = NewFileHandler(self.queue)
            observer = Observer()
            observer.schedule(event_handler, folder_path, recursive=True)
            observer.start()
            try:
                while True:
                    time.sleep(10)
            except Exception as e:
                print(f"Error: {e}")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
        except Exception as e:
            print(f"Error: {e}")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    def process_files(self):
        global data_dict

        try:
            url = data_dict["Motion_detection_url"]
            clip_path = data_dict["server_clip_url"]
            output_videos_folder = self.motion_folder+'/Videos'
            output_images_folder = self.motion_folder+'/Images' 
            
            while True:
                if not self.queue.empty():
                    motion_data = self.queue.get()
                    print(motion_data)
                    motion_data_date = motion_data[0].strftime("%d-%m-%Y")
                    output_videos_folder = self.motion_folder+'/Videos'+'/'+motion_data_date
                    output_images_folder = self.motion_folder+'/Images'+'/'+motion_data_date
                    try:
                        if not os.path.exists(output_videos_folder):
                            os.mkdir(output_videos_folder)
                        if not os.path.exists(output_images_folder):
                            os.mkdir(output_images_folder)
                    except Exception as e:
                        print(e)
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)
                    
                    # Perform operations on the file
                    print(f"Processing file: {motion_data[1]}")
                    file_name = motion_data[1].split('/')[-1]
                    file_extension = file_name.split('.')

                    try:
                        if file_extension[-1] == 'sdv':
                            base_name, ext = os.path.splitext(file_name)
                            base_name = motion_data[0].strftime("%Y%m%dT%H%M%S")
                            print("base: ", base_name)

                            # Construct ffmpeg command for format change
                            output_video = os.path.join(output_videos_folder, f"{base_name}.mp4")
                            video_format_change = f"ffmpeg -i {motion_data[1]} {output_video} > /dev/null 2>&1"
                            subprocess.run(video_format_change, shell=True)
                            # video = Popen(video_format_change)

                            try:
                                if os.path.exists(motion_data[1]):
                                    os.remove(motion_data[1])
                            except Exception as e:
                                print("Error in deleting video: ", e)

                            # Extract a single frame from the converted video
                            output_image = os.path.join(output_images_folder, f"{base_name}.jpg")
                            frame_extraction = f"ffmpeg -ss 5 -i {output_video} -vframes 1 {output_image} > /dev/null 2>&1"
                            subprocess.run(frame_extraction, shell=True)

                            print("Output Video:", output_video)
                            print("Output Image:", output_image)
                    except Exception as e:
                        print(e)
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)

                        try:
                            ip = self.cam_ip.replace('.', '')[6:]
                            date = datetime.now().strftime("%d%m%y%H%M%S")
                            
                            reference_no = ip + date
                        
                            print("Path: ",clip_path+output_video)

                            data = {
                                     "reference_no": reference_no,
                                     "camera": self.cam_ip,
                                     "timestamp": motion_data[0].strftime("%d-%b-%Y %H:%M:%S"),
                                     "video_type": "Full",
                                     "video_url": clip_path+output_video,
                                     "image_url": clip_path+output_image
                                   }
                            
                      
                            
                            r = requests.post(url, data=json.dumps(data), headers={"Content-Type":"application/json"})
                   
                            print(f"File processed: {motion_data[1]}")
                        except Exception as e:
                            pass
                    
                    time.sleep(10)
                else:
                    time.sleep(10)
        except:
            pass



def check_storage():
    time.sleep(5)
   

    while True:
        global data_dict

      
        cameras = [cam.cam_name for cam in gf.camera_list]
        print("in check storage cam list: ", cameras)

        try:
        

            recordings_drives = data_dict["Recordings_drive"]
            threshold_percent = data_dict["Storage_threshold"]
       
            print("drive to use: ", gf.current_drive, gf.current_dir)

            try:
                """Select Recordings directory/partition to be used"""

                if ll.fetch_current_node() != "None":
                    dir_info = ll.get_partition_info(gf.current_drive)

                    while float(dir_info["Used Space Percentage"][:-1]) > threshold_percent:
                        if ll.fetch_next_node() != "None":
                           
                            gf.current_drive = ll.fetch_current_node()
                            gf.current_dir = next(x for x in gf.recordings_drive if gf.recordings_drive[x]==gf.current_drive)
                            dir_info = ll.get_partition_info(gf.current_drive)
                          

                            for cam in gf.camera_list:
                                try:
                                   
                                    cam.change_storage_folder = True
                                    cam.to_delete_files = False
                                except Exception as e:
                                    print(e)

                        else:
                            ll.fetch_previous_node()
                            

                            for cam in gf.camera_list:
                                try:
                                    
                                    cam.change_storage_folder = False
                                    cam.to_delete_files = True
                                except Exception as e:
                                    print(e)

            except Exception as e:
                print(e)

        except Exception as e:
            print(e)


        time.sleep(600)
        # time.sleep(60)


check_storage_thread = threading.Thread(target=check_storage)
check_storage_thread.daemon = True
check_storage_thread.start()


