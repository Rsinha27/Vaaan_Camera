from django.db import models

# Create your models here.


class AllCamerasGroup(models.Model):
    all_cameras_group = models.CharField(primary_key=True, unique=True, max_length=100, blank=False)


class CameraGroup(models.Model):
    # auto_increment_id = models.AutoField(primary_key=True)
    group_name = models.CharField(primary_key=True, unique=True, max_length=100, blank=False)
    # device_name = models.CharField(max_length=50, blank=True, null=True)


class StreamingCamera(models.Model):
    # auto_increment_id = models.AutoField(primary_key=True, unique=True, editable=False)
    device_name = models.CharField(primary_key=True, unique=True, max_length=100, blank=False)
    username = models.CharField(max_length=20, blank=False)
    password = models.CharField(max_length=20, blank=False)
    ip_address = models.CharField(max_length=25, blank=False)
    latitude = models.FloatField()
    longitude = models.FloatField()
    storage_days = models.IntegerField(default=30)
    device_category = models.CharField(max_length=20, blank=False)
    project = models.CharField(max_length=20, blank=False)
    all_cameras_group = models.ForeignKey(AllCamerasGroup, on_delete=models.PROTECT, default="All cameras", related_name='all_cameras')
    group_name = models.ForeignKey(CameraGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='camera_groups')
    # incident = models.ForeignKey(IncidentDetails, on_delete=models.CASCADE, null=True, blank=True, related_name="incident")

    # def __str__(self):
    #     return self.device_name