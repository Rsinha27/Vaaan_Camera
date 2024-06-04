from django.shortcuts import render

# Create your views here.
import os, sys
from collections import OrderedDict
from . import serializers
from .create import CameraStream
from .create import *
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import StreamingCamera, CameraGroup, AllCamerasGroup
from .global_file import ll
from . import global_file as gf
import threading
import time

from django.http import HttpResponse, FileResponse
from django.http import StreamingHttpResponse
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET
import re
from django.urls import path
from django.shortcuts import render
from django.shortcuts import get_object_or_404
import traceback


"""Used to create AllCamerasGroup at the very beginning"""
try:
    all_cameras_group = AllCamerasGroup.objects.create(all_cameras_group="All cameras")
except Exception as e:
    # print(e)
    print("'All cameras group' already exists..")


"""Select Recordings directory/partition to be used"""
try:
    with open("vms_configurations.json", "r") as f:
        data_dict = json.load(f)
        
    threshold_percent = data_dict["Storage_threshold"]


    if ll.fetch_current_node() != "None":
        gf.current_drive = ll.fetch_current_node()
        gf.current_dir = next(x for x in gf.recordings_drive if gf.recordings_drive[x]==gf.current_drive)
        print("CD: ", gf.current_drive, gf.current_dir)
        dir_info = ll.get_partition_info(gf.current_drive)
        print("before while: ", dir_info)

        while float(dir_info["Used Space Percentage"][:-1]) > threshold_percent:
         
            if ll.fetch_next_node() != "None":
                gf.current_drive = ll.fetch_current_node()
                gf.current_dir = next(x for x in gf.recordings_drive if gf.recordings_drive[x]==gf.current_drive)
                print("new CD: ", gf.current_drive, gf.current_dir)
                dir_info = ll.get_partition_info(gf.current_drive)
                print("in while: ", dir_info)
            else:
                ll.fetch_previous_node()

except Exception as e:
    print(e)
    


"""Used to re-create camera objects on system restart and append to the below list"""


try:
   
    
    all_cameras = StreamingCamera.objects.all()
    for camera in all_cameras:
        try:
            gf.camera_list.append(CameraStream(camera.device_name, camera.username, camera.password, camera.ip_address, camera.storage_days))
        except Exception as e:
            print("Error in starting camera: ", e)
            
except Exception as e:
    print(e)


current_directory = os.path.dirname(os.path.abspath(__file__))


def cameras_reconnect(directory=None):
  

    pass



t = threading.Thread(target=cameras_reconnect, args=())
t.daemon = True
t.start()



#To give list of Cameras from the Recordings  Directory
@require_GET
def recordings_list(request):
    print('requesting cameras data....')
    folder_path = os.path.join( './videos/' + request.path)
    try:
        files = os.listdir(folder_path)
        print(files)
        return JsonResponse(files, safe=False)
    except Exception as e:
        error_message = f'Error getting directory information. {str(e)}'
        print(error_message)
        return JsonResponse(error_message, status=500)
    

#Send the list of Videos of the selected Camera 
@require_GET
def recordings_folder(request, folder_path):
    print('requesting recordings data...')
    folder_path = './videos/' + request.path
    try:
        files = os.listdir(folder_path)
        return JsonResponse(files, safe=False)
    except Exception as e:
        error_message = f'Error getting directory information. {str(e)}'
        print(error_message)
        return HttpResponse(error_message, status=500)








####################################################################################################################



class CameraGroupCreateView(APIView):
    def post(self, request):
        if request.data["group_name"] != "All cameras":
            serializer = serializers.CameraGroupCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class CameraGroupListView(APIView):
    def get(self, request):
        all_cameras_group = AllCamerasGroup.objects.all()
        serializer1 = serializers.AllCamerasGroupDetailSerializer(all_cameras_group, many=True)
        groups = CameraGroup.objects.all()
        serializer2 = serializers.CameraGroupDetailSerializer(groups, many=True)
        # print("abc: ", type(list(serializer1.data)), serializer1.data)
        data1 = list(serializer1.data)
        data2 = list(serializer2.data)
        # return Response({"A":serializer1.data, "B":serializer2.data})
        data = data1 + data2
        return Response(data)

#####################################################################################################################


class CameraGroupDelete(APIView):

    

    def delete(self, request):
        try:
            if request.data["group_name"] == "All cameras":
                return Response({'message': 'this group cannot be deleted'})
            else:
                group = CameraGroup.objects.get(group_name=request.data["group_name"])
                group.delete()
                return Response({'message': 'group deleted'})
        except Exception as e:
            return Response({'message': 'no such group'})