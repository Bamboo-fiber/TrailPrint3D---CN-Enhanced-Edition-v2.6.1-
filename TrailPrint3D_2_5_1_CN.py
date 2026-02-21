"""
Created on Tue Feb 17 01:38:53 2026

==============================================================================
TrailPrint3D - CN Enhanced Edition (v2.5.1)
==============================================================================

Version 2.5.1(CN) - Added Circle Shape, Custom Base Size & Quick Draw

Changelog:
- Full Localization: Complete Chinese language support added throughout the interface
- New Shape: Added "Circle" option to the Shape menu
- Customizable Dimensions: Added base size input with individual size control for each shape (default: 100mm)
- Quick Draw: Added quick drawing functionality for rapid sketching and map painting

------------------------------------------------------------------------------
Copyright (c) 2025 EmGi (Original Creator)
Copyright (c) 2026 Bamboo-fiber (Localization & Enhancements)

MODIFICATION NOTICE / 修改声明:
This version is a modified fork of the original TrailPrint3D (v2.5) by EmGi.
Modifications made by Bamboo-fiber include: Full Chinese UI localization, addition 
of the "Circle Shape", and the "Quick Draw" feature.

本版本基于 EmGi 的原版 (v2.5) 修改而来。
修改内容包括：全量中文汉化、新增"圆形"底座、新增"快速绘制"功能。
------------------------------------------------------------------------------

This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 
International License. To view a copy of this license, visit 
https://creativecommons.org/licenses/by-nc/4.0/ 

==============================================================================
ATTRIBUTIONS / 数据来源致谢:
Elevation data provided by the Mapzen Terrain Tiles project.
© Mapzen. Data hosted on AWS as part of the AWS Public Dataset Program.
License: https://github.com/tilezen/joerd/blob/master/docs/attribution.md 
Elevation data from OpenTopoData, using the SRTM and other datasets.
Elevation data from Open-Elevation, based on Shuttle Radar Topography Mission (SRTM) data © NASA.
Water data © OpenStreetMap contributors
Terrain data from Mapzen, based on data © OpenStreetMap contributors, NASA SRTM, and USGS.
Map data © OpenStreetMap contributors
==============================================================================
"""

bl_info = {
    "name": "轨迹3D打印 (TrailPrint3D)",
    "blender": (4, 5, 2),
    "category": "Object",
    "author": "Bamboo-fiber",
    "version": (2, 5, 1),
    "description": "为您的小型冒险创建3D打印地形图",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY"
}

category = "TrailPrint3D"
AddonVersion = (2, 5, 1)


import bpy # type: ignore
import webbrowser
import xml.etree.ElementTree as ET
import math
import requests # type: ignore
import time
from datetime import date
from datetime import datetime
import bmesh # type: ignore
from mathutils import Vector, bvhtree, Euler
import os
import sys
import json
import platform
import zlib
import struct
import csv


gpx_file_path = ""
exportPath = ""
shape = ""
name = ""
size =  48
num_subdivisions = 4
scaleElevation = 5
pathThickness = 1.2
pathScale = 0.8
shapeRotation = 0
overwritePathElevation = False
autoScale = 1
dataset = "srtm30m"  # OpenTopoData dataset

textFont = r"C:\Windows\Fonts\msyhbd.ttc"
textSize = 0
overwriteLength = ""
overwriteHeight = ""
overwriteTime = ""
outerBorderSize = 0

minLat = 0
maxLat = 0
minLon = 0
maxLon = 0

lowestZ = 0
highestZ = 0


overwritePathElevation = False
centerx = 0
centery = 0
total_length = 0
total_elevation = 0
total_time = 0
time_str = ""
elevationOffset = 0
# Conversion factor: 1 degree latitude/longitude ≈ 111320 meters
LAT_LON_TO_METERS = 111.32
additionalExtrusion = 0
specialCollection = [("----", "----", "")]
duration = 0
api = 0
fixedElevationScale = False
minThickness = 2
selfHosted = ""
opentopoAdress = ""
GPXsections = 0

scaleHor = 0

MapObject  = None
plateobj = None
textobj = None
objWater = None
objForest = None
objCity = None
objGlacier = None

# Define a path to store the counter data
counter_file = os.path.join(bpy.utils.user_resource('CONFIG'), "api_request_counter.json")
elevation_cache_file = os.path.join(bpy.utils.user_resource('CONFIG'), "elevation_cache.json")
# Set up a cache directory for Terrarium tiles
terrarium_cache_dir = os.path.join(bpy.utils.user_resource('CONFIG'), "terrarium_cache")
if not os.path.exists(terrarium_cache_dir):
    os.makedirs(terrarium_cache_dir)

# In-memory elevation cache
_elevation_cache = {}
cacheSize = 100000

buggyDataset = 0
exportformat = "STL"

#PANEL----------------------------------------------------------------------------------------------------------

def shape_callback(self,context):
    #print(f"Shape: {self.shape}")
    if self.shape == "HEXAGON INNER TEXT" or self.shape == "HEXAGON OUTER TEXT" or self.shape =="OCTAGON OUTER TEXT" or self.shape == "HEXAGON FRONT TEXT":
        try:
            bpy.utils.register_class(MY_PT_Shapes)
        except:
            pass
    else:
        try:
            bpy.utils.unregister_class(MY_PT_Shapes)
        except:
            pass

# Cache the collection names
def get_external_collections(path):
    if not os.path.exists(path):
        return []
    with bpy.data.libraries.load(path, link=True) as (data_from, _):
        return list(data_from.collections)

# Update dropdown items dynamically when panel is drawn
def update_collection_items(self, context):
    
    print("Updating")
    path = bpy.context.scene.tp3d.specialBlend_path
    path = bpy.path.abspath(path)
    names = get_external_collections(path)
    print(names)
    global specialCollection
    specialCollection = [(name, name, "") for name in names]
    #return [(name, name, "") for name in names]

def dynamic_specialCollection_items(self, context):
    return specialCollection
    
# Define a Property Group to store variables
class MyProperties(bpy.types.PropertyGroup):
    file_path: bpy.props.StringProperty(
        name="轨迹文件路径",
        description="选择一个GPX或IGC文件",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    export_path: bpy.props.StringProperty(
        name="导出路径",
        description="保存STL文件的文件夹路径",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    chain_path: bpy.props.StringProperty(
        name="文件夹路径",
        description="选择包含多个GPX文件的文件夹",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    trailName: bpy.props.StringProperty(name="地图名称", default="", description="留空则使用文件名")
    
    shape: bpy.props.EnumProperty(
        name = "形状",
        items=[
            ("HEXAGON", "六边形", "六边形地图"),
            ("SQUARE", "正方形", "正方形地图"),
            ("CIRCLE", "圆形", "圆形地图"),
            ("HEXAGON INNER TEXT", "六边形(内嵌文字)", "带文字切割的六边形地图"),
            ("HEXAGON OUTER TEXT", "六边形(外置文字)", "带底盘和外部文字的六边形地图"),
            ("HEXAGON FRONT TEXT", "六边形(正前文字)", "带底盘且文字在正前方的六边形地图")
        ],
        default = "HEXAGON",
        update = shape_callback 
    )
    
    shapeRotation: bpy.props.FloatProperty(
        name="形状旋转",
        default=0.0,
        min=-360.0,
        max=360.0,
        description="旋转地图形状的起始角度"
    )
    
    api: bpy.props.EnumProperty(
        name = "API 来源",
        items=[
            ("OPENTOPODATA", "Opentopodata", "较慢但高度精确"),
            ("OPEN-ELEVATION","Open-Elevation","较快但部分区域质量一般"),
            ("TERRAIN-TILES", "Terrain-Tiles", "目前最快的可用数据集")
        ],
        default = "TERRAIN-TILES"
    )

    dataset: bpy.props.EnumProperty(
        name = "数据集",
        items=[
            ("srtm30m", "srtm30m", "纬度 -60 到 60"),
            ("aster30m","aster30m","全球范围"),
            ("ned10m","ned10m","美国本土/夏威夷/阿拉斯加部分"),
            ("mapzen","mapzen","全球范围"),
            ("nzdem8m","nzdem8m","新西兰 8m"),
            ("eudem25m","eudem25m","欧洲")
        ],
        default = "aster30m"
    )

    scalemode: bpy.props.EnumProperty(
        name="缩放模式",
        items=[
            ('FACTOR', "自适应比例", "根据底座尺寸自动撑满轨迹"),
            ('COORDINATES', "经纬度对应", "通过两个坐标点计算精确物理比例"),
            ('SCALE', "全球统一比例", "使用固定的墨卡托投影比例（多块拼图推荐）")
        ],
        default='FACTOR'
    )

    pathScale: bpy.props.FloatProperty(name = "轨迹占比", default = 0.8, min = 0.01, max = 200, description = "轨迹相对于底座的大小（1.0为撑满）")
    scaleLon1: bpy.props.FloatProperty(name = "经度1", default = 0)
    scaleLat1: bpy.props.FloatProperty(name = "纬度1", default = 0)
    scaleLon2: bpy.props.FloatProperty(name = "经度2", default = 0)
    scaleLat2: bpy.props.FloatProperty(name = "纬度2", default = 0)

    selfHosted: bpy.props.StringProperty(name="私有 API 地址", default="")

    objSize: bpy.props.IntProperty(name="六边形宽度 (mm)", default = 100, min = 5, max = 10000)
    num_subdivisions: bpy.props.IntProperty(name = "网格精细度", default = 4, min = 1, max = 10)
    scaleElevation: bpy.props.FloatProperty(name = "垂直夸张倍数", default = 10, min = 0, max = 10000)
    pathThickness: bpy.props.FloatProperty(name = "轨迹线径 (mm)", default = 1.2, min = 0.1, max = 5)
    
    overwritePathElevation: bpy.props.BoolProperty(name="路径贴合地面", default=True)

    o_verticesPath: bpy.props.StringProperty(name="轨迹顶点", default="等待数据...")
    o_verticesMap: bpy.props.StringProperty(name="地图顶点", default="等待数据...")
    o_mapScale: bpy.props.StringProperty(name="比例尺", default = "")
    o_time: bpy.props.StringProperty(name="生成状态", default="等待生成...")
    
    o_apiCounter_OpenTopoData: bpy.props.StringProperty(name="API 计数 (Daily)", default = "API 限制: ---/1000")
    o_apiCounter_OpenElevation: bpy.props.StringProperty(name="API 计数 (Monthly)", default = "API 限制: ---/1000")
    o_centerx: bpy.props.FloatProperty(name = "中心 X", default = 0)
    o_centery: bpy.props.FloatProperty(name = "中心 Y", default = 0)

    magnetHeight: bpy.props.FloatProperty(name = "Magnet Height", default = 2.5, description = "Height of the Holes for Magnets")
    magnetDiameter: bpy.props.FloatProperty(name = "Magnet Diameter", default = 6.3, description = "Diameter of the Holes for Magnets")

    bottomMarkCutout: bpy.props.BoolProperty(name="Bottom Mark Cutout", default = False, description = "Creates Bottom mark as a Cutout")

    textFont: bpy.props.StringProperty(
        name="字体路径",
        description="选择一个字体文件",
        default=r"C:\Windows\Fonts\msyhbd.ttc", 
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    textSize: bpy.props.IntProperty(name="Text Size", default = 5, min = 0, max = 1000)
    textSizeTitle: bpy.props.IntProperty(name="Title Text Size", default = 0, min = 0, max = 1000, description = "Keep 0 to use value from 'Text Size'")
    overwriteLength: bpy.props.StringProperty(name="text1", default = "")
    overwriteHeight: bpy.props.StringProperty(name="text2", default = "")
    overwriteTime: bpy.props.StringProperty(name="text3", default = "")
    outerBorderSize: bpy.props.IntProperty(name="BorderSize in %", default = 20, min = 0, max = 1000, description="Only for Shapes with Plate")
    text_angle_preset: bpy.props.IntProperty(name="Text Angle", description="Rotate Text on Shape", default=0, min = 0, max = 260)
    plateThickness: bpy.props.FloatProperty(name="plateThickness", default = 5, description="Thickness of the Additional Plate")
    plateInsertValue: bpy.props.FloatProperty(name="plateInsertValue", default = 0, description="Depth of Cutout for the Map in the Plate, 0  to ignore")

    tileSpacing: bpy.props.FloatProperty(name="tileSpacing", default = 0, description="Distance between Tiles when Extending")
   
    minThickness: bpy.props.IntProperty(name="minThickness", default = 2, min = 0, max = 1000, description="Additional Thickness on lowest point")
    xTerrainOffset: bpy.props.FloatProperty(name="xTerrainOffset", default = 0, description="Gives the map an Offset in X-Direction from the path")
    yTerrainOffset: bpy.props.FloatProperty(name="yTerrainOffset", default = 0, description="Gives the map an Offset in Y-Direction from the path")

    rescaleMultiplier: bpy.props.FloatProperty(name = "scale", default = 1, min = 0, max = 10000)
    thickenValue: bpy.props.FloatProperty(name="thickenValue", default = 1, description = "Makes your Map 1mm thicker")
    fixedElevationScale: bpy.props.BoolProperty(name="FixedElevationScale(10mm)", default=False, description = "Force the elevation to be 10mm High from highest to lowest point (ElevationScale still applies after that)")
    singleColorMode: bpy.props.BoolProperty(name="SingleColorMode", default = False, description = "Enable this if you dont have a Multicolor printer")
    tolerance: bpy.props.FloatProperty(name="Tolerance", default = 0.2, description="Tolerance of the Trail for the SingleColorMode")
    disableCache: bpy.props.BoolProperty(name="disableCache", default = False, description = "disabling cache if you encounter random holes in your mesh")
    ccacheSize: bpy.props.IntProperty(name = "Cache Size", default = 50000, min = 0)
    indipendendTiles : bpy.props.BoolProperty(name="IndipendendTiles", default = False, description = "Tile minThickness is indipendend from other tiles")
  
    sAdditionalExtrusion: bpy.props.FloatProperty(name="sAdditionalExtrusion",default = 0)
    sAutoScale: bpy.props.FloatProperty(name="sAutoScale",default = 1)
    sScaleHor: bpy.props.FloatProperty(name="sScaleHor",default = 1, description = "Scale of the Map")
    sElevationOffset: bpy.props.FloatProperty(name="sElevationOffset", default = 0)
    sMapInKm: bpy.props.FloatProperty(name = "Map Length", default = 0, description = "How much Km are the equivalent of the Map Size")

    col_wActive: bpy.props.BoolProperty(name="Include Water", default=False, description = "Include Water (lakes, ponds) (experimental), Seas dont work yet")
    col_wArea: bpy.props.FloatProperty(name="Water Size Treshold", default = 1, description = "lakes smaller than the treshold wont be included")
    col_fActive: bpy.props.BoolProperty(name="Include Forests", default=False, description = "Include Forests (experimental)")
    col_fArea: bpy.props.FloatProperty(name="Forest Size Treshold", default = 10, description = "Forests smaller than the treshold wont be included")
    col_cActive: bpy.props.BoolProperty(name="Include City Boundaries", default=False, description = "Include City Boundaries(experimental)")
    col_cArea: bpy.props.FloatProperty(name="City Size Treshold", default = 1, description = "Cities smaller than the treshold wont be included")
    col_glActive: bpy.props.BoolProperty(name="Include Glaciers", default=False, description = "Include Glaciers (If there are any)")
    col_glArea: bpy.props.FloatProperty(name="Glacier Size Treshold", default = 1, description = "Glaciers smaller than the treshold wont be included")
    col_KeepManifold: bpy.props.BoolProperty(name="Keep Non-Manifold Objects", default=False, description = "Keep Broken/Non-Manifold Water Parts")
    col_PaintMap: bpy.props.BoolProperty(name="Paint Map", default=True, description = "Paint map instead of Generating Separate Objects (Reccomended for MAC users)")

    mountain_treshold:bpy.props.IntProperty(name="Mountain Treshold", default = 60, min = 0, max = 100,subtype='PERCENTAGE', description="Height Treshold to Color Mountians")
    cl_thickness: bpy.props.FloatProperty(name="Contour Line Thickness", default = 0.2, description = "Thickness of the Contour Line")
    cl_distance: bpy.props.FloatProperty(name="Contour Line distance", default = 2, description = "Distance between Contour lines")
    cl_offset: bpy.props.FloatProperty(name="Contour Line offset", default = 0.0, description = "Offset of the Countour lines")

    show_stats: bpy.props.BoolProperty(name="Additional Info", default=False)
    show_coloring: bpy.props.BoolProperty(name="Include Elements", default=False)
    show_chain: bpy.props.BoolProperty(name="Multi Generation", default=False)
    show_map: bpy.props.BoolProperty(name="Map",default=False)
    show_pin: bpy.props.BoolProperty(name="Pin",default=False)
    show_special: bpy.props.BoolProperty(name="Special",default=False)
    show_postProcess: bpy.props.BoolProperty(name="Post Process", default = False)
    show_api: bpy.props.BoolProperty(name="API", default=False)
    show_attribution: bpy.props.BoolProperty(name="Attribution", default = False)
    show_preset: bpy.props.BoolProperty(name="Preset", default=False)

    cityname: bpy.props.StringProperty(name="Cityname", default="Berlin", description = "Get coordinates of a City")
    pinLat: bpy.props.FloatProperty(name="标记点纬度", default = 48.00)
    pinLon: bpy.props.FloatProperty(name="标记点经度", default = 8.00)

    mapmode: bpy.props.EnumProperty(
        name="区域生成模式",
        items=[
            ('FROMPLANE', "基于物体平面", "根据场景中的平面物体生成地图"),
            ('FROMCENTER', "中心点+半径", "根据中心经纬度和半径公里数生成"),
            ('2POINTS', "两点坐标范围", "根据两个对角线坐标点生成")
        ],
        default='FROMPLANE'
    )

    jMapLat: bpy.props.FloatProperty(name="中心纬度", default = 49.00)
    jMapLon: bpy.props.FloatProperty(name="中心经度", default = 9.00)
    jMapRadius: bpy.props.FloatProperty(name="抓取半径(km)", default = 200)

    jMapLat1: bpy.props.FloatProperty(name="纬度 1", default = 48.00)
    jMapLon1: bpy.props.FloatProperty(name="经度 1", default = 8.00)
    jMapLat2: bpy.props.FloatProperty(name="纬度 2", default = 49.00)
    jMapLon2: bpy.props.FloatProperty(name="经度 2", default = 9.00)

    specialBlend_path: bpy.props.StringProperty(
        name="TP3dSpecial.blend Path",
        description="Select the TP3dSpecial.blend file you got from Patreon",
        default="",
        maxlen=1024,
        subtype='FILE_PATH',  # Enables file selection
        #update = update_collection_items
    )# type: ignore

    # Custom property to store selection
    specialCollectionName: bpy.props.EnumProperty(
        name="specialCollection",
        description="Choose a collection from the external .blend",
        items=dynamic_specialCollection_items
    )# type: ignore
    
    # Define the operator (script execution)
class MY_OT_runGeneration(bpy.types.Operator):
    bl_idname = "wm.run_my_script"
    bl_label = "开始生成"
    bl_description = "根据当前设置生成轨迹和地图模型"

    def execute(self, context):
        props = context.scene.tp3d  # Access stored variables
        
        runGeneration(0)
        
        return {'FINISHED'}

class MY_OT_ExportSTL(bpy.types.Operator):
    bl_idname = "wm.exportstl"
    bl_label = "导出 STL"
    bl_description = "将选中对象导出为单独的STL文件 (不含颜色)"

    def execute(self, context):
        props = context.scene.tp3d  # Access stored variables
        
        global exportPath
        exportPath = bpy.context.scene.tp3d.get('export_path', None)

        if exportPath == None:
            show_message_box("'Export path' is Empty. Please select a Directory For the finished files")
            return {'FINISHED'}
            
        exportPath = bpy.path.abspath(exportPath)

        if not exportPath or exportPath == "":
            show_message_box("Export path is empty! Please select a valid folder.")
            return {'FINISHED'}
        if not os.path.isdir(exportPath):
            show_message_box(f"Invalid export Directory: {exportPath}. Please select a valid Directory.")
            return {'FINISHED'}
        
        if not bpy.context.selected_objects:
            show_message_box("Please select the Object you want to Export")
            return{'FINISHED'}
        
        export_selected_to_STL("STL") 
        
        return {'FINISHED'}

class MY_OT_ExportOBJ(bpy.types.Operator):
    bl_idname = "wm.exportobj"
    bl_label = "Export OBJ"
    bl_description = "Export Selected Objects as Separate OBJ"

    def execute(self, context):
        props = context.scene.tp3d  # Access stored variables
        
        global exportPath
        exportPath = bpy.context.scene.tp3d.get('export_path', None)

        if exportPath == None:
            show_message_box("'Export path' is Empty. Please select a Directory For the finished files")
            return {'FINISHED'}
            
        exportPath = bpy.path.abspath(exportPath)

        if not exportPath or exportPath == "":
            show_message_box("Export path is empty! Please select a valid folder.")
            return {'FINISHED'}
        if not os.path.isdir(exportPath):
            show_message_box(f"Invalid export Directory: {exportPath}. Please select a valid Directory.")
            return {'FINISHED'}
        
        if not bpy.context.selected_objects:
            show_message_box("Please select the Object you want to Export")
            return{'FINISHED'}
        
        export_selected_to_STL("OBJ") 
        
        return {'FINISHED'}
 
def open_website(self, context):
    webbrowser.open("https://patreon.com/EmGi3D?utm_source=Blender")
  
# Operator to open a website
class MY_OT_OpenWebsite(bpy.types.Operator):
    bl_idname = "wm.open_website"
    bl_label = "Visit My Website"
    bl_description = "The Patreon Version as Additional Features!"

    def execute(self, context):
        open_website(self, context)
        #self.report({'INFO'}, "Opening website...")
        return {'FINISHED'}

def open_discord(self, context):
    webbrowser.open("https://discord.gg/C67H9EJFbz")
  
# Operator to open a website
class MY_OT_JoinDiscord(bpy.types.Operator):
    bl_idname = "wm.join_discord"
    bl_label = "Join Discord"
    bl_description = "Discord Community for TrailPrint3D!"

    def execute(self, context):
        open_discord(self, context)
        #self.report({'INFO'}, "Opening website...")
        return {'FINISHED'}

class MY_OT_Rescale(bpy.types.Operator):
    bl_idname = "wm.rescale"
    bl_label = "Rescale the z value"
    bl_description = "Rescales the Elevation the Currently selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        multiZ = bpy.context.scene.tp3d.get('rescaleMultiplier', 1)

        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type in {'MESH', 'CURVE'}]
        lowestZ = 1000

        print("Rescaling")
        for obj in selected_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                for i, vert in enumerate(mesh.vertices):
                    if vert.co.z < lowestZ and vert.co.z > 0.1:
                        lowestZ = vert.co.z
            if obj.type == "CURVE":
                if lowestZ == 1000:
                    for spline in obj.data.splines:
                        for point in spline.bezier_points:
                            if point.co.z > 0.1 and point.co.z < lowestZ:
                                lowestZ = point.co.z

        print(f"lowestZ: {lowestZ}")

        for obj in selected_objects:
        
            print(obj.name)
            if lowestZ != 1000 and obj.type == "MESH":
                    bpy.context.view_layer.objects.active = obj  # Make it active
                    bpy.ops.object.mode_set(mode='EDIT')
                    # Access mesh data
                    mesh = bmesh.from_edit_mesh(obj.data)
                    for v in mesh.verts:
                        if v.co.z > 0.1:
                            v.co.z = (v.co.z - lowestZ) * (multiZ) + lowestZ
                    bmesh.update_edit_mesh(obj.data)
            
            bpy.ops.object.mode_set(mode='OBJECT')  # Exit Edit Mode
            
            if lowestZ != 1000 and obj.type =="CURVE":
                # Access curve splines
                for spline in obj.data.splines:
                    for point in spline.bezier_points:
                        if point.co.z > -0.5:
                            point.co.z = (point.co.z - lowestZ) * (multiZ) + lowestZ
                    for point in spline.points:  # For NURBS
                        if point.co.z > -0.5:
                            point.co.z = (point.co.z - lowestZ) * (multiZ) + lowestZ

            bpy.ops.object.mode_set(mode='OBJECT')  # Exit Edit Mode

            if "Elevation Scale" in obj:
                obj["Elevation Scale"] *= multiZ

        print(f"Scaled all elevation points by Factor {multiZ} on {len(selected_objects)} object(s).")

        return {'FINISHED'}

class MY_OT_savePreset(bpy.types.Operator):
    bl_idname="wm.savepreset"
    bl_label = "Save preset"
    bl_description = "Save the current settings as a preset"
    bl_options = {'REGISTER', 'UNDO'}

    user_input: bpy.props.StringProperty(name="Preset name")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self,context):
       save_myproperties_to_csv(self.user_input)

       show_message_box("Saved Preset","CHECKMARK", " ")

       return {'FINISHED'}

class MY_OT_loadPreset(bpy.types.Operator):
    bl_idname="wm.loadpreset"
    bl_label = "Load preset"
    bl_description = "Load the current settings as a preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self,context):
        current = bpy.context.scene.preset_list
        load_myproperties_from_csv(current)

        show_message_box("Preset Loaded","CHECKMARK", " ")

        return {'FINISHED'}

class MY_OT_deletePreset(bpy.types.Operator):
    bl_idname="wm.deletepreset"
    bl_label = "Delete preset"
    bl_description = "Delete the current selected preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self,context):
        current = bpy.context.scene.preset_list
        delete_preset_file(current)

        show_message_box("Deleted Selected Preset","CHECKMARK", " ")

        return {'FINISHED'}
 
class MY_OT_thicken(bpy.types.Operator):
    bl_idname="wm.thicken"
    bl_label = "Thicken Map"
    bl_description = "Make the selected Map thicker"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self,context):
        
        selected_objects = context.selected_objects
        val = bpy.context.scene.tp3d.thickenValue

        bpy.context.tool_settings.mesh_select_mode = (False, False, True)

        bpy.ops.object.select_all(action='DESELECT')
        for zobj in selected_objects:
            zobj.select_set(False)

        if not selected_objects:
            show_message_box("No objects selected.")
            return {'CANCELLED'}

        for zobj in selected_objects:
            # Check if the custom property 'Object type' exists
            if "Object type" in zobj:
                print(zobj.name)
                if zobj["Object type"] == "TRAIL" or zobj["Object type"] == "WATER" or zobj["Object type"] == "FOREST" or zobj["Object type"] == "CITY":
                    zobj.location.z += val
                elif zobj["Object type"] == "MAP" :
                    zobj.select_set(True)
                    bpy.context.view_layer.objects.active = zobj
                    selectBottomFaces(zobj)
                    bpy.ops.mesh.select_more()
                    bpy.ops.mesh.select_all(action='INVERT')
                    mesh = bmesh.from_edit_mesh(zobj.data)
                    
                    verts_to_move = set()
                    for face in mesh.faces:
                        if face.select:
                            verts_to_move.update(face.verts)

                    for vert in verts_to_move:
                        vert.co.z += val
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    zobj.select_set(False)
                    zobj["minThickness"] += val
                    
        bpy.context.view_layer.objects.active = selected_objects[0]
        for zobj in selected_objects:
            zobj.select_set(True)
            
        return {'FINISHED'}

class MY_OT_PinCoords(bpy.types.Operator):
    bl_idname="wm.pincoords"
    bl_label = "PinCoords"
    bl_description = "Place a Pin on a Coordinate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        minThickness = bpy.context.scene.tp3d.minThickness

        centerlat = bpy.context.scene.tp3d.pinLat
        centerlon = bpy.context.scene.tp3d.pinLon
        
        xp,yp,zp = convert_to_blender_coordinates(float(centerlat),float(centerlon),0,0)
        name = "Pin_" + str(round(centerlat,2)) + "." + str(round(centerlon,2))

        #Delete existing object with same name (optional)
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

        #Creatin the Cone
        bpy.ops.mesh.primitive_cone_add(
            vertices=16,
            radius1=0.4,
            radius2=0.8,
            depth=4,
            location=(xp, yp, minThickness + 2)  # Position base at Z=0
        )
        pin = bpy.context.active_object
        pin.name = name

        return {'FINISHED'}

class MY_OT_MagnetHoles(bpy.types.Operator):
    bl_idname = "wm.magnetholes"
    bl_label = "Magnet Holes"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self,context):

        selected_objects = context.selected_objects

        if not selected_objects:
            show_message_box("No objects selected")
            #return{'FINISHED'}
            return{'FINISHED'}

        
        
        bpy.ops.object.select_all(action='DESELECT')
        for zobj in selected_objects:
            zobj.select_set(False)

        for zobj in selected_objects:

            if zobj.type != 'MESH':
                continue

            zobj.select_set(True)
            bpy.context.view_layer.objects.active = zobj

            obj_size = bpy.context.scene.tp3d.objSize

            #Check for selection and custom property
            if zobj:
                if "objSize" in zobj.keys():
                    obj_size = zobj["objSize"]
            elif not zobj:
                    print("Select a Map.")
                    return{'FINISHED'}
            
            if "MagnetHoles" not in zobj.keys():
                continue

            if zobj["MagnetHoles"] == True:
                continue

            magnetDiameter = bpy.context.scene.tp3d.magnetDiameter
            magnetHeight = bpy.context.scene.tp3d.magnetHeight

            #Flip normals and Get bottom faces
            selectBottomFaces(zobj)

            #get the lowest zValue of one the faces
            zValue = 0

            # Switch to Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')
            mesh = bmesh.from_edit_mesh(zobj.data)

            # Get the world matrix to convert local to global coordinates
            world_matrix = zobj.matrix_world

            # Collect global Z-values of selected faces
            z_values = [
                (world_matrix @ face.calc_center_median()).z
                for face in mesh.faces if face.select
            ]
            
            zValue = min(z_values)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            #Set 3D cursor to object's origin
            bpy.context.scene.cursor.location = zobj.location

            #Create 4 cylinders around the object
            radius = obj_size / 3
            angle_step = math.radians(90)
            created_cylinders = []

            for i in range(4):
                angle = i * angle_step
                offset_x = math.cos(angle) * radius
                offset_y = math.sin(angle) * radius
                pos = zobj.location + Vector((offset_x, offset_y, zValue))
                pos = zobj.location + Vector((offset_x, offset_y, 0))

                bpy.ops.mesh.primitive_cylinder_add(
                    radius=magnetDiameter / 2,
                    depth=magnetHeight*2,
                    location=pos
                )
                cyl = bpy.context.active_object
                created_cylinders.append(cyl)

            #Merge cylinders into one object
            bpy.ops.object.select_all(action='DESELECT')
            for cyl in created_cylinders:
                cyl.select_set(True)
            bpy.context.view_layer.objects.active = created_cylinders[0]
            bpy.ops.object.join()
            merged_cylinders = bpy.context.active_object

            #Perform boolean difference
            bpy.ops.object.select_all(action='DESELECT')
            zobj.select_set(True)
            bpy.context.view_layer.objects.active = zobj

            bool_mod = zobj.modifiers.new(name="MagnetCutout", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = merged_cylinders

            bpy.ops.object.modifier_apply(modifier=bool_mod.name)

            #Cleanup - delete the merged cutter object
            bpy.data.objects.remove(merged_cylinders, do_unlink=True)

            zobj["MagnetHoles"] = True

            bpy.ops.object.select_all(action='DESELECT')
            zobj.select_set(False)

            print("Shlong")

        bpy.context.view_layer.objects.active = selected_objects[0]
        for zobj in selected_objects:
            zobj.select_set(True)
        
        print("Magnet holes Added")
        
        return{'FINISHED'}

class MY_OT_Dovetail(bpy.types.Operator):
    bl_idname = "wm.dovetail"
    bl_label = "Dovetail"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self,context):

        selected_objects = context.selected_objects

        if not selected_objects:
            show_message_box("No objects selected")
            return{'FINISHED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        for zobj in selected_objects:
            zobj.select_set(False)
        
        for zobj in selected_objects:

            if zobj.type != 'MESH':
                continue
            
            if "Dovetail" not in zobj.keys():
                continue

            if zobj["Dovetail"] == True:
                continue

            zobj.select_set(True)
            bpy.context.view_layer.objects.active = zobj
            
            #Check for selection and custom property
            if zobj:
                if "objSize" not in zobj.keys():
                    break
                        
                obj_size = zobj["objSize"]

            dovetailSize = 15
            dovetailHeight = 3
            
            if obj_size <= 50:
                dovetailSize = 5
            elif obj_size <= 75:
                dovetailSize = 10

            #Flip normals and Get bottom faces
            selectBottomFaces(zobj)

            #get the lowest zValue of one the faces
            zValue = 0

            # Switch to Edit Mode
            #bpy.ops.object.mode_set(mode='EDIT')
            mesh = bmesh.from_edit_mesh(zobj.data)

            # Get the world matrix to convert local to global coordinates
            world_matrix = zobj.matrix_world

            # Collect global Z-values of selected faces
            z_values = [
                (world_matrix @ face.calc_center_median()).z
                for face in mesh.faces if face.select
            ]
            
            zValue = min(z_values)

            bpy.ops.object.mode_set(mode='OBJECT')
            
            #Set 3D cursor to object's origin
            bpy.context.scene.cursor.location = zobj.location

            #Create 4 cylinders around the object
            radius = obj_size/2 * 0.866 - dovetailSize/2
            angle_step = math.radians(60)
            steps = 6
            created_cylinders = []

            for i in range(steps):
                angle = i * angle_step + math.radians(30)
                offset_x = math.cos(angle) * radius
                offset_y = math.sin(angle) * radius
                #pos = zobj.location + Vector((offset_x, offset_y, zValue + dovetailHeight/2))
                pos = zobj.location + Vector((offset_x, offset_y, 0 + dovetailHeight/2))
                rotation = Euler((0, 0, angle - math.radians(90)), 'XYZ')

                bpy.ops.mesh.primitive_cylinder_add(
                    vertices = 3,
                    radius=dovetailSize,
                    depth=dovetailHeight,
                    location=pos,
                    rotation = rotation
                )
                cyl = bpy.context.active_object
                created_cylinders.append(cyl)
            
            #Merge cylinders into one object
            bpy.ops.object.select_all(action='DESELECT')
            for cyl in created_cylinders:
                cyl.select_set(True)
            bpy.context.view_layer.objects.active = created_cylinders[0]
            bpy.ops.object.join()
            merged_cylinders = bpy.context.active_object

            #Select top faces of the Triangles to scale them up slightly
            selectTopFaces(merged_cylinders)

            mesh = bmesh.from_edit_mesh(merged_cylinders.data)
            # Scale factor
            scale_factor = 1.05

            # Scale each selected face from its own center
            for face in mesh.faces:
                if face.select:
                    center = face.calc_center_median()
                    for vert in face.verts:
                        direction = vert.co - center
                        vert.co = center + direction * scale_factor

            # Update the mesh
            bmesh.update_edit_mesh(merged_cylinders.data, loop_triangles=False)

            bpy.ops.object.mode_set(mode='OBJECT')

            #Perform boolean difference
            bpy.ops.object.select_all(action='DESELECT')
            zobj.select_set(True)
            bpy.context.view_layer.objects.active = zobj

            bool_mod = zobj.modifiers.new(name="DovetailCutout", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = merged_cylinders
            
            zobj["Dovetail"] = True

            bpy.ops.object.modifier_apply(modifier=bool_mod.name)

            #Cleanup - delete the merged cutter object
            bpy.data.objects.remove(merged_cylinders, do_unlink=True)

            bpy.ops.object.select_all(action='DESELECT')
            zobj.select_set(False)
        
        bpy.context.view_layer.objects.active = selected_objects[0]
        for zobj in selected_objects:
            zobj.select_set(True)
        
        print("Dovetail Added")
        
        return{"FINISHED"}

class MY_OT_TerrainDummy(bpy.types.Operator):
    bl_idname = "wm.dummy"
    bl_label = "Dummy Operator"
    def execute(self,context):
        show_message_box("This Feature is Exclusive for Patreon Supporters")
        return{"FINISHED"}
    
class MY_OT_BottomMark(bpy.types.Operator):
    bl_idname = "wm.bottommark"
    bl_label = "Bottom Mark"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self,context):

        selected_objects = context.selected_objects

        bottomMarkCutout = bpy.context.scene.tp3d.bottomMarkCutout

        if not selected_objects:
            show_message_box("No objects selected")
            return{'FINISHED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        for zobj in selected_objects:
            zobj.select_set(False)

        generated = False
        for zobj in selected_objects:
            
            #Check for selection and custom property
            if "BottomMark" not in zobj.keys():
                continue

            if zobj["BottomMark"] == True:
                continue

            if zobj.type == "MESH" and "objSize" in zobj:

                zobj.select_set(True)
                bpy.context.view_layer.objects.active = zobj

                mark = BottomText(zobj)
                generated = True

                if bottomMarkCutout == True:

                    mark.scale.z = 2
                    recalculateNormals(mark)
                    # Add boolean modifier
                    bool_mod = zobj.modifiers.new(name="Boolean", type='BOOLEAN')
                    bool_mod.object = mark
                    bool_mod.operation = 'DIFFERENCE'
                    bool_mod.solver = 'EXACT'

                    bpy.context.view_layer.objects.active = zobj
                    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

                    bpy.data.objects.remove(mark, do_unlink=True)
                
                bpy.ops.object.select_all(action='DESELECT')
                zobj.select_set(False)
            
        if generated == False:
            show_message_box("Not a valid Object selected")

        bpy.context.view_layer.objects.active = selected_objects[0]
        for zobj in selected_objects:
            zobj.select_set(True)
        
        return{'FINISHED'}
                                
class MY_OT_ColorMountain(bpy.types.Operator):
    bl_idname="wm.colormountain"
    bl_label = "Color Mountains"
    bl_description = "Color Mountains above a certain Treshold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self,context):
        
        selected_objects = bpy.context.selected_objects
        min_treshold = bpy.context.scene.tp3d.mountain_treshold

        #Collect min/max from custom properties
        min_z = None
        max_z = None
        minThickness = None

        if not selected_objects:
            show_message_box("No Object Selected. Please select a Map first")
            return {'CANCELLED'}

        for obj in selected_objects:
            if "lowestZ" in obj.keys() and "highestZ" in obj.keys() and obj["highestZ"] != 0:
                low = obj["lowestZ"]
                high = obj["highestZ"]
                minThickness = obj["minThickness"]
                min_z = low if min_z is None else min(min_z, low)
                max_z = high if max_z is None else max(max_z, high)

        print(f"Lowest Z across objects: {min_z}, Highest Z: {max_z}")

        #Create or get green material
        matG = bpy.data.materials.get("BASE")
        
        #Create or get a gray material
        mat = bpy.data.materials.get("MOUNTAIN")

        #Iterate objects and faces
        for obj in selected_objects:
            if obj.type != 'MESH' or obj["Object type"] != "MAP" or max_z == 0:
                print("Not Applied")
                continue
            print("Apply Mountain Color")
    
            #obj.data.materials.clear()
            #obj.data.materials.append(matG)  # creates first slot and assigns

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)

            #Ensure material exists on the object
            matG_index = obj.data.materials.find("BASE")
            mat_index = obj.data.materials.find("MOUNTAIN")
            if mat_index == -1:  # Material not assigned yet
                obj.data.materials.append(mat)
                mat_index = len(obj.data.materials) - 1
            
            tres = (max_z-min_z)/100 * min_treshold + minThickness
            for face in bm.faces:
                #Skip vertical faces (normal is not pointing up/down)
                if abs(face.normal.z) < 0.02:  
                    continue

                avg_z = sum(v.co.z for v in face.verts) / len(face.verts)
                if avg_z > tres and face.material_index == matG_index:
                    face.material_index = mat_index
                elif avg_z < tres and face.material_index == mat_index:
                    face.material_index = matG_index

            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')
        
        return {'FINISHED'}

class MY_OT_ContourLines(bpy.types.Operator):
    bl_idname="wm.contourlines"
    bl_label = "Contour Lines"
    bl_description = "Color Mountains above a certain Treshold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self,context):
        
        selected_objects = bpy.context.selected_objects
        cl_thickness = bpy.context.scene.tp3d.cl_thickness
        cl_distance = bpy.context.scene.tp3d.cl_distance
        cl_offset = bpy.context.scene.tp3d.cl_offset

        size = bpy.context.scene.tp3d.objSize
        
        if not selected_objects:
            show_message_box("No Object Selected. Please select a Map first")
            return {'CANCELLED'}

        for obj in selected_objects:

            if not "Object type" in obj:
                continue
            if obj["Object type"] != "MAP":
                continue

            objs = list(bpy.context.scene.objects)
            for o in objs:
                if "Object type" in o and "PARENT" in o:
                    if o["PARENT"] == obj and  o["Object type"] == "LINES":
                        bpy.data.objects.remove(o, do_unlink=True)

            # Deselect everything
            bpy.ops.object.select_all(action='DESELECT')
            
            # Create plane at 3D cursor
            bpy.ops.mesh.primitive_plane_add(size=size + 10, enter_editmode=False, align='WORLD',
                                            location=bpy.context.scene.cursor.location)
            plane = bpy.context.active_object
            plane.name = "CuttingPlane"
            plane.location.z += cl_offset
            
            # Add Array modifier in Z direction
            array_mod = plane.modifiers.new(name="ArrayZ", type='ARRAY')
            array_mod.relative_offset_displace = (0, 0, 0)   # disable relative offset
            array_mod.constant_offset_displace = (0, 0, cl_distance)   # fixed step in Z
            array_mod.use_relative_offset = False
            array_mod.use_constant_offset = True
            array_mod.count = 100  # you can adjust how many slices
            
            # Add Solidify modifier for thickness
            solidify_mod = plane.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify_mod.thickness = cl_thickness
            
            # Apply modifiers up to solidify
            bpy.context.view_layer.objects.active = plane
            bpy.ops.object.modifier_apply(modifier=array_mod.name)
            bpy.ops.object.modifier_apply(modifier=solidify_mod.name)
            
            # Add Boolean modifier with INTERSECT mode
            bool_mod = plane.modifiers.new(name="Boolean", type='BOOLEAN')
            bool_mod.operation = 'INTERSECT'
            bool_mod.solver = 'MANIFOLD'  # or 'EXACT'
            bool_mod.use_self = False
            bool_mod.use_hole_tolerant = True  # helps with manifold issues
            bool_mod.object = obj

            plane.name = obj.name + "_LINES"

            mat = bpy.data.materials.get("WHITE")
            plane.data.materials.clear()
            plane.data.materials.append(mat)

            writeMetadata(plane,"LINES")
            plane["PARENT"] = obj
            
            # Apply Boolean
            bpy.context.view_layer.objects.active = plane
            
            bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = selected_objects[0]
            
        return {'FINISHED'}

       
# Create the UI Panel
class MY_PT_Generate(bpy.types.Panel):
    bl_label = "创建地图"
    bl_idname = "PT_EmGi_3DPath+"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TrailPrint3D"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.tp3d  # Get properties

        # Add input fields
        layout.label(text = "开发者: Bamboo-fiber")
        layout.label(text = "版本: 2.5.1（CN）")
        layout.separator() 
        
        # Add the script execution button
        layout.label(text = "生成模型")
        layout.operator("wm.run_my_script", text="点击生成模型", icon='DISC')
        
        box = layout.box()
        box.prop(props, "file_path", icon = "ANIM")
        box.prop(props, "export_path", icon = "FILE_FOLDER")
        box.prop(props, "trailName", icon = "SORTALPHA")
        
        # Shape Selection
        box.prop(props, "shape")
        box.separator()

        # --- MODIFIED SECTION START ---
        # Change the label based on the selected shape
        if props.shape == "CIRCLE":
            box.prop(props, "objSize", text="圆形直径 (mm)")
        elif props.shape == "SQUARE":
            box.prop(props, "objSize", text="正方形边长 (mm)")
        elif props.shape == "HEXAGON":
            box.prop(props, "objSize", text="六边形宽度 (mm)")
        else:
            box.prop(props, "objSize") # Default fallback
        # --- MODIFIED SECTION END ---

        box.prop(props, "num_subdivisions")
        box.prop(props, "scaleElevation")
        box.prop(props, "pathThickness")
        
        box.prop(props, "scalemode")
        if props.scalemode == "FACTOR":
            box.prop(props, "pathScale")
        elif props.scalemode == "COORDINATES":
            row = box.row()
            row.prop(props,"scaleLat1")
            row.prop(props,"scaleLon1")
            row = box.row()
            row.prop(props,"scaleLat2")
            row.prop(props,"scaleLon2")
        elif props.scalemode == "SCALE":
            box.prop(props, "pathScale")
        else:
            box.label(text=props.scalemode)

        box.prop(props, "overwritePathElevation") 

        layout.label(text = props.o_time, icon = "TIME")
        layout.label(text = "------------------------------")
    

class MY_PT_Advanced(bpy.types.Panel):
    bl_label = "高级功能"
    bl_idname = "PT_Advanced"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TrailPrint3D"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.tp3d  # Get properties
        
        # STL EXPORT
        box = layout.box()
        box.label(text = "手动导出选中项")
        box.operator("wm.exportstl", text="导出 STL", icon="EXPORT")
        box.operator("wm.exportobj", text="导出 OBJ", icon = "EXPORT")

        # MAP 设置部分
        layout.prop(props,"show_map", text="地图详细设置", icon="TRIA_DOWN" if props.show_map else "TRIA_RIGHT")
        if props.show_map:
            box = layout.box()
            box.prop(props, "fixedElevationScale", text="固定高程比例(10mm)")
            box.prop(props, "minThickness", text="底座物理厚度")
            box.prop(props, "shapeRotation", text="形状旋转")
            box.prop(props, "xTerrainOffset", text="地形 X 偏移")
            box.prop(props, "yTerrainOffset", text="地形 Y 偏移")
            box.prop(props, "singleColorMode", text="单色打印模式")
            box.prop(props, "tolerance", text="轨迹容差")
            box.prop(props, "disableCache", text="禁用缓存")
            box.prop(props, "ccacheSize", text="缓存大小")
            box.separator()

            box.label(text="自定义范围地图")
            if bpy.context.scene.tp3d.sScaleHor != 0: # 修正判断逻辑
                box.prop(props, "mapmode", text="生成模式")
                if props.mapmode == "FROMPLANE":
                    box.operator("wm.dummy", text = "从选区创建地图", icon = "OBJECT_DATA")
                    box.prop(props,"indipendendTiles", text="独立分块")
                elif props.mapmode == "FROMCENTER":
                    row = box.row()
                    row.prop(props, "jMapLat", text="中心纬度") # 强制中文显示
                    row.prop(props, "jMapLon", text="中心经度") # 强制中文显示
                    box.prop(props, "jMapRadius", text="抓取半径(km)")
                elif props.mapmode == "2POINTS":
                    row = box.row()
                    row.prop(props, "jMapLat1")
                    row.prop(props, "jMapLon1")
                    row = box.row()
                    row.prop(props, "jMapLat2")
                    row.prop(props, "jMapLon2")
            layout.separator()

        # 元素包含 (水体/森林/建筑) 部分
        layout.prop(props,"show_coloring", text="地图元素包含", icon="TRIA_DOWN" if props.show_coloring else "TRIA_RIGHT")
        if props.show_coloring:
            boxer = layout.box()
            box = boxer.box()
            box.label(text = "水体设置")
            box.prop(props, "col_wActive", text="包含水体")
            box.prop(props, "col_wArea", text="面积过滤阈值")
            
            box = boxer.box()
            box.label(text = "森林设置")
            box.prop(props, "col_fActive", text="包含森林")
            box.prop(props, "col_fArea", text="面积过滤阈值")
            
            box = boxer.box()
            box.label(text = "建筑/城市设置")
            box.prop(props, "col_cActive", text="包含建筑边界")
            box.prop(props, "col_cArea", text="面积过滤阈值")
            
            boxer.prop(props,"col_PaintMap", text="直接绘制在地图上")

        # PIN 标记点部分
        layout.prop(props,"show_pin", text="标记点设置", icon="TRIA_DOWN" if props.show_pin else "TRIA_RIGHT")
        if props.show_pin:
            box = layout.box()
            box.label(text="通过坐标放置标记点") # 如果这里是英文请修改
            row = box.row()
            row.prop(props, "pinLat", text="纬度") # 添加 text="..." 强制指定中文
            row.prop(props, "pinLon", text="经度") # 添加 text="..." 强制指定中文
            box.operator("wm.pincoords", text = "在坐标处放置标记点", icon = "PINNED")

        # 后期处理部分
        layout.prop(props,"show_postProcess", text="后期处理", icon = "TRIA_DOWN" if props.show_postProcess else "TRIA_RIGHT")
        if props.show_postProcess:
            box = layout.box()
            box.label(text="山脉与地形效果")
            box.prop(props,"mountain_treshold", text="山脉上色阈值")
            box.operator("wm.colormountain", text="高海拔上色", icon = "RNDCURVE")
            box.separator()
            box.prop(props,"cl_thickness", text="等高线粗细")
            box.prop(props,"cl_distance", text="等高线间距")
            box.operator("wm.contourlines", text="生成等高线", icon = "ALIGN_JUSTIFY")
            box.separator()
            box.operator("wm.magnetholes", text="生成磁铁孔", icon = "SNAP_OFF")
            box.operator("wm.dovetail", text="生成燕尾榫", icon = "SHAPEKEY_DATA")
            box.operator("wm.bottommark", text="生成底部文字", icon = "SMALL_CAPS")

        # 统计信息部分
        layout.prop(props,"show_stats", text="统计与 API 信息", icon="TRIA_DOWN" if props.show_stats else "TRIA_RIGHT")
        if props.show_stats:
            box = layout.box()
            box.label(text=props.o_verticesPath)
            box.label(text=props.o_verticesMap)
            box.label(text=f"水平缩放: {props.sScaleHor}")
            box.label(text=props.o_time)
            box.label(text=props.o_apiCounter_OpenTopoData)

class MY_PT_Shapes(bpy.types.Panel):
    bl_label = "形状附加设置"  # 修改这里，原词是 "Additional Shape Settings"
    bl_idname = "PT_ShapeSettings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TrailPrint3D"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.tp3d  # Get properties
        
        if props.shape == "HEXAGON INNER TEXT" or props.shape == "HEXAGON OUTER TEXT" or props.shape == "OCTAGON OUTER TEXT" or props.shape == "HEXAGON FRONT TEXT": 
            if not props.textFont:
                props.textFont = r"C:\Windows\Fonts\msyhbd.ttc"
            # 修改以下显示文字
            layout.prop(props, "textFont", text="选择字体") 
            layout.prop(props, "textSize", text="文本大小")
            layout.prop(props, "textSizeTitle", text="标题大小")
            layout.separator()
            layout.label(text = "手动覆盖文本内容:") # 修改这里，原词是 "Overwrite text:"
            layout.prop(props, "overwriteLength", text="覆盖长度文字")
            layout.prop(props, "overwriteHeight", text="覆盖海拔文字")
            layout.prop(props, "overwriteTime", text="覆盖耗时文字")
            layout.prop(props, "plateThickness", text="底盘厚度")
            layout.prop(props, "outerBorderSize", text="外边框占比(%)")
            layout.prop(props, "plateInsertValue", text="底座切口深度")
            layout.prop(props, "text_angle_preset", text="文字旋转角度")

class OBJECT_OT_ShowCustomPropsPopup(bpy.types.Operator):
    bl_idname = "object.show_custom_props_popup"
    bl_label = "Generation Settings"
    bl_description = "Show what Settings were used to Generate this Object (With Map object Selected)"
    bl_options = {'REGISTER'}

    MAX_PER_COLUMN = 25
    NORMAL_WIDTH = 400
    DOUBLE_WIDTH = 800

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj:
            layout.label(text="No active object.", icon="ERROR")
            return

        custom_props = [k for k in obj.keys() if not k.startswith("_")]

        if not custom_props:
            layout.label(text="No custom properties found. Please Select a Map", icon="INFO")
            return

        total = len(custom_props)

        if total > self.MAX_PER_COLUMN:
            split = layout.split(factor=0.5)
            col1 = split.column(align=True)
            col2 = split.column(align=True)

            mid = (total + 1) // 2

            for col, chunk in zip((col1, col2), (custom_props[:mid], custom_props[mid:])):
                for key in chunk:
                    row = col.row()
                    row.label(text=key + ":", icon='DOT')
                    row.label(text=str(obj[key]))
        else:
            col = layout.column(align=True)
            for key in custom_props:
                row = col.row()
                row.label(text=key + ":", icon='DOT')
                row.label(text=str(obj[key]))

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = context.active_object
        custom_props = [k for k in obj.keys() if not k.startswith("_")] if obj else []
        width = self.DOUBLE_WIDTH if len(custom_props) > self.MAX_PER_COLUMN else self.NORMAL_WIDTH
        return context.window_manager.invoke_props_dialog(self, width=width)

# Register the classes and properties
def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.tp3d = bpy.props.PointerProperty(type=MyProperties)

    bpy.utils.register_class(MY_OT_runGeneration)
    bpy.utils.register_class(MY_OT_ExportSTL)
    bpy.utils.register_class(MY_OT_ExportOBJ)
    bpy.utils.register_class(MY_PT_Generate)
    bpy.utils.register_class(MY_PT_Advanced)
    bpy.utils.register_class(MY_OT_OpenWebsite)
    bpy.utils.register_class(MY_OT_JoinDiscord)
    bpy.utils.register_class(MY_OT_Rescale)
    bpy.utils.register_class(OBJECT_OT_ShowCustomPropsPopup)
    bpy.utils.register_class(MY_OT_PinCoords)
    bpy.utils.register_class(MY_OT_TerrainDummy)
    bpy.utils.register_class(MY_OT_MagnetHoles)
    bpy.utils.register_class(MY_OT_Dovetail)
    bpy.utils.register_class(MY_OT_thicken)
    bpy.utils.register_class(MY_OT_BottomMark)
    bpy.utils.register_class(MY_OT_ColorMountain)
    bpy.utils.register_class(MY_OT_ContourLines)
    bpy.utils.register_class(MY_OT_savePreset)
    bpy.utils.register_class(MY_OT_loadPreset)
    bpy.utils.register_class(MY_OT_deletePreset)
    

def unregister():
    del bpy.types.Scene.tp3d
    bpy.utils.unregister_class(MyProperties)

    bpy.utils.unregister_class(MY_OT_runGeneration)
    bpy.utils.unregister_class(MY_OT_ExportSTL)
    bpy.utils.unregister_class(MY_OT_ExportOBJ)
    bpy.utils.unregister_class(MY_PT_Generate)
    bpy.utils.unregister_class(MY_PT_Advanced)
    bpy.utils.unregister_class(MY_OT_OpenWebsite)
    bpy.utils.unregister_class(MY_OT_JoinDiscord)
    bpy.utils.unregister_class(MY_OT_Rescale)
    bpy.utils.unregister_class(OBJECT_OT_ShowCustomPropsPopup)
    bpy.utils.unregister_class(MY_OT_PinCoords)
    bpy.utils.unregister_class(MY_OT_TerrainDummy)
    bpy.utils.unregister_class(MY_OT_MagnetHoles)
    bpy.utils.unregister_class(MY_OT_Dovetail)
    bpy.utils.unregister_class(MY_OT_thicken)
    bpy.utils.unregister_class(MY_OT_BottomMark)
    bpy.utils.unregister_class(MY_OT_ColorMountain)
    bpy.utils.unregister_class(MY_OT_ContourLines)
    bpy.utils.unregister_class(MY_OT_savePreset)
    bpy.utils.unregister_class(MY_OT_loadPreset)
    bpy.utils.unregister_class(MY_OT_deletePreset)

#--------------------------------------------------
#Debug
#--------------------------------------------------

def save_myproperties_to_csv(filename):
    """
    Save all writable properties of a MyProperties instance to a CSV file.
    Each row is: property_name , value
    """
    folder = os.path.join(bpy.utils.user_resource('CONFIG'), "presets")
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, filename + ".csv")

    props = bpy.context.scene.tp3d

    print(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["property", "value"])  # header

        for p in props.bl_rna.properties:
            name = p.identifier
            if name == "rna_type" or p.is_readonly:
                continue

            try:
                value = getattr(props, name)
            except:
                continue

            # Convert lists/tuples to string
            if isinstance(value, (list, tuple)):
                value = ",".join(map(str, value))

            writer.writerow([name, value])

def load_myproperties_from_csv(filename):
    """
    Load all properties from a CSV file and overwrite the values in MyProperties.
    """
    folder = os.path.join(bpy.utils.user_resource('CONFIG'), "presets")
    filepath = os.path.join(folder, filename + ".csv")

    if not os.path.isfile(filepath):
        print("Preset file not found:", filepath)
        return

    props = bpy.context.scene.tp3d

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        for row in reader:
            if len(row) < 2:
                continue

            name, value = row[0], row[1]

            if not hasattr(props, name):
                continue  # skip unknown properties

            current = getattr(props, name)

            try:
                # Convert back to correct type
                if isinstance(current, bool):
                    value = value.lower() == "true"
                
                elif isinstance(current, int):
                    value = int(value)
                
                elif isinstance(current, float):
                    value = float(value)
                
                elif isinstance(current, (list, tuple)):
                    # Split list stored as comma-separated string
                    value = [float(v) for v in value.split(",")]
                
                # strings stay strings
            except:
                # Failed conversion → keep original
                continue

            try:
                setattr(props, name, value)
            except:
                pass

def delete_preset_file(preset_name):
    """
    Deletes a preset .csv file from the Blender CONFIG/presets folder.
    preset_name = name WITHOUT extension
    """
    folder = os.path.join(bpy.utils.user_resource('CONFIG'), "presets")
    filepath = os.path.join(folder, preset_name + ".csv")

    if not os.path.isfile(filepath):
        print("File not found:", filepath)
        return False

    try:
        os.remove(filepath)
        print("Deleted:", filepath)
        return True
    except Exception as e:
        print("Error deleting file:", e)
        return False
    


def list_files_callback(self, context):
    folder = os.path.join(bpy.utils.user_resource('CONFIG'), "presets")
    items = []

    if os.path.isdir(folder):
        for fname in os.listdir(folder):
            if os.path.isfile(os.path.join(folder, fname)):
                name_no_ext = os.path.splitext(fname)[0]
                items.append((name_no_ext, name_no_ext, ""))

    # Show placeholder if empty
    if not items:
        items.append(("none", "-- No files found --", ""))

    return items

bpy.types.Scene.preset_list = bpy.props.EnumProperty(
    name="Presets",
    items=list_files_callback
)

def load_counter():
    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r") as f:
                data = json.load(f)
                return data.get("count_openTopodata", 0), data.get("date_openTopoData", ""), data.get("count_openElevation",0), data.get("date_openElevation","")
        except:
            return 0, "", 0, ""
    return 0, "", 0, ""

# Function to save the counter data
def save_counter(count_openTopodata, date_openTopoData, count_openElevation, date_openElevation):
    with open(counter_file, "w") as f:
        json.dump({"count_openTopodata": count_openTopodata, "date_openTopoData": date_openTopoData, "count_openElevation": count_openElevation, "date_openElevation": date_openElevation}, f)

# Function to update the request counter
def update_request_counter():
    today = date.today().isoformat()  # ✅ This correctly gets today's date
    today_date = date.today().isoformat()  # Get today's date in iso format
    today_month = date.today().month  # Get current month as an integer (1-12)
    count_openTopodata, date_openTopoData, count_openElevation, date_openElevation = load_counter()

    # Reset counter if the date has changed
    if date_openTopoData != today_date:
        count_openTopodata = 0
    
    if date_openElevation != today_month:
        count_openElevation = 0

    global api
    if api == 0:
        count_openTopodata += 1
    elif api == 1:
        count_openElevation += 1

    save_counter(count_openTopodata, today_date, count_openElevation,today_month)
    
    return count_openTopodata, count_openElevation  # Return the updated count

def send_api_request(addition = ""):
    
    global dataset
    request_count = update_request_counter()
    now = datetime.now()
    if api == 0:
        print(f"{now.hour:02d}:{now.minute:02d} | Fetching: {addition} | API Usage: {request_count} | {dataset}")
    elif api == 1:
        print(f"{now.hour:02d}:{now.minute:02d} | Fetching: {addition} | API Usage: {request_count}")
    elif api == 2:
        print(f"{now.hour:02d}:{now.minute:02d} | Fetching API")

if __name__ == "__main__":

    register()
    #unregister()


#--------------------------------------------------------------------------------------------------------------------
#DISPLAY GENERATION----------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------

import xml.etree.ElementTree as ET
from datetime import datetime
import bpy

def read_gpx_1_1(filepath):
    """
    Reads a GPX file and extracts the coordinates, elevation, and timestamps
    from either track points (trkpt) or route points (rtept).
    """

    tree = ET.parse(filepath)
    root = tree.getroot()

    segmentlist = []
    # Define namespaces for parsing GPX
    ns = {'default': 'http://www.topografix.com/GPX/1/1'}

    #find segments inside the file
    ammount = 0
    segments = root.findall('.//default:trkseg',ns)
    print(f"Segments: {len(segments)}")
    if segments:
        for seg in segments:
            # Try to find track points first
            points = seg.findall('.//default:trkpt', ns)
            point_type = 'trkpt'

            # If no track points found, look for route points
            if not points:
                points = seg.findall('.//default:rtept', ns)
                point_type = 'rtept'

            segcoords = []
            lowestElevation = 10000

            for pt in points:
                lat = float(pt.get('lat'))
                lon = float(pt.get('lon'))
                ele = pt.find('default:ele', ns)
                elevation = float(ele.text) if ele is not None else 0.0
                time = pt.find('default:time', ns)
                ammount += 1
                try:
                    timestamp = datetime.fromisoformat(time.text.replace("Z", "+00:00")) if time is not None else None
                except Exception:
                    timestamp = None
                segcoords.append((lat, lon, elevation, timestamp))
                if elevation < lowestElevation:
                    lowestElevation = elevation

            global elevationOffset
            elevationOffset = max(lowestElevation - 50, 0)

            bpy.context.scene.tp3d["sElevationOffset"] = elevationOffset
            bpy.context.scene.tp3d["o_verticesPath"] = f"{point_type.upper()}  Path vertices: {len(segcoords)}"
            segmentlist.append(segcoords)

    #coordinates.append(segcoords)
    print(f"Ammount: {ammount}")
    return segmentlist
    
def read_gpx_1_0(filepath):
    """Reads a GPX 1.0 file and extracts the coordinates, elevation, and timestamps."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    segmentlist = []
    # Define the namespace to handle the GPX 1.0 format correctly
    ns = {'gpx': 'http://www.topografix.com/GPX/1/0'}

    # Extract track points (latitude, longitude, elevation, timestamp)
    segcoords = []
    lowestElevation = 10000

    segments = root.findall('.//gpx:trkseg',ns)
    print(f"Segments in 1.0: {len(segments)}")
    
                 
    if segments:
        for seg in segments:
            # Extracting track points
            for trkpt in seg.findall('.//gpx:trkpt', ns):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                ele = trkpt.find('gpx:ele', ns)
                elevation = float(ele.text) if ele is not None else 0.0
                time = trkpt.find('gpx:time', ns)
                timestamp = datetime.fromisoformat(time.text) if time is not None else None
                #print(f"lat: {lat}, long: {lon}, ele: {elevation}, time: {timestamp}")
                segcoords.append((lat, lon, elevation, timestamp))
                
                if elevation < lowestElevation:
                    lowestElevation = elevation
        
            global elevationOffset
            elevationOffset = max(lowestElevation - 50, 0)

            bpy.context.scene.tp3d["sElevationOffset"] = elevationOffset
            
            bpy.context.scene.tp3d["o_verticesPath"] = f"Path vertices: {len(segcoords)}"
            segmentlist.append(segcoords)
        
        return segmentlist

def read_igc(filepath):
    """Reads an IGC file and extracts the coordinates, elevation, and timestamps."""
    segmentlist = []
    coordinates = []
    lowestElevation = 10000
    
    with open(filepath, 'r') as file:
        for line in file:
            # IGC B records contain position data
            if line.startswith('B'):
                try:
                    # Extract time (HHMMSS)
                    time_str = line[1:7]
                    hours = int(time_str[0:2])
                    minutes = int(time_str[2:4])
                    seconds = int(time_str[4:6])
                    
                    # Extract latitude (DDMMmmmN/S)
                    lat_str = line[7:15]
                    lat_deg = int(lat_str[0:2])
                    lat_min = int(lat_str[2:4])
                    lat_min_frac = int(lat_str[4:7]) / 1000.0
                    lat = lat_deg + (lat_min + lat_min_frac) / 60.0
                    if lat_str[7] == 'S':
                        lat = -lat
                    
                    # Extract longitude (DDDMMmmmE/W)
                    lon_str = line[15:24]
                    lon_deg = int(lon_str[0:3])
                    lon_min = int(lon_str[3:5])
                    lon_min_frac = int(lon_str[5:8]) / 1000.0
                    lon = lon_deg + (lon_min + lon_min_frac) / 60.0
                    if lon_str[8] == 'W':
                        lon = -lon
                    
                    # Extract pressure altitude (in meters)
                    pressure_alt = int(line[25:30])
                    
                    # Extract GPS altitude (in meters)
                    gps_alt = int(line[30:35])
                    
                    # Create timestamp (using current date since IGC files don't store date in B records)
                    now = datetime.now()
                    timestamp = datetime(now.year, now.month, now.day, hours, minutes, seconds)
                    
                    # Use GPS altitude for elevation
                    elevation = gps_alt
                    
                    coordinates.append((lat, lon, elevation, timestamp))
                    
                    if elevation < lowestElevation:
                        lowestElevation = elevation
                    
                except (ValueError, IndexError) as e:
                    print(f"Error parsing IGC line: {line.strip()}")
                    continue

    global elevationOffset
    elevationOffset = max(lowestElevation - 50, 0)
    
    bpy.context.scene.tp3d["o_verticesPath"] = "Path vertices: " + str(len(coordinates))

    segmentlist.append(coordinates)
    return segmentlist


def read_gpx_directory(directory_path):
    """Reads all GPX files in a directory and extracts coordinates, elevation, and timestamps."""
    
    # Define GPX namespace
    ns = {'default': 'http://www.topografix.com/GPX/1/1'}
    
    # List to store all coordinates from all GPX files
    coordinates = []
    coordinatesSeparate = []  # Stores a list of lists for separate files
    lowestElevation = 10000  # High initial value

    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".gpx"):  # Only process .gpx files
            filepath = os.path.join(directory_path, filename)

            file_extension = os.path.splitext(filepath)[1].lower()
            if file_extension == '.gpx':
                tree = ET.parse(filepath)
                root = tree.getroot()
                version = root.get("version")
                print(f"File Name: {filename}, File Version: {version}")
                if version == "1.0":
                    co= read_gpx_1_0(filepath)
                if version == "1.1":
                    co= read_gpx_1_1(filepath)
            elif file_extension == '.igc':
                co= read_igc(filepath)

            # Append the file-specific list to coordinatesSeparate
            if co:
                for coseg in co:
                    coordinatesSeparate.append(coseg)
                    lowest = min(coseg, key = lambda x: x[2])
                    lowest_In_coords = lowest[2]
                    if lowest_In_coords < lowestElevation:
                        lowestElevation = lowest_In_coords
                        print(f"new Lowest Elevation: {lowestElevation}")

    
    #Merge the separate coordinates to one big list together
    coordinates = [pt for sublist in coordinatesSeparate for pt in sublist]
    
    
    # Calculate elevation offset
    global elevationOffset
    elevationOffset = max(lowestElevation - 50, 0)

    bpy.context.scene.tp3d["sElevationOffset"] = elevationOffset

    # Store the number of points in the Blender scene property
    bpy.context.scene.tp3d["o_verticesPath"] = f"Path vertices: {len(coordinates)}"
    
    print(f"Total GPX files processed: {len(coordinatesSeparate)}")
    
    return coordinatesSeparate

def read_gpx_file():
     gpx_file_path = bpy.context.scene.tp3d.get('file_path', None)

     coords = []
     file_extension = os.path.splitext(gpx_file_path)[1].lower()
     if file_extension == '.gpx':
         tree = ET.parse(gpx_file_path)
         root = tree.getroot()
         version = root.get("version")

         ns = {'default': root.tag.split('}')[0].strip('{')}
         global GPXsections
         GPXsections = len(root.findall(".//default:trkseg", ns))
         print(f"GPX Sections: {GPXsections}")
         
         if version == "1.0":
             coords = read_gpx_1_0(gpx_file_path)
         if version == "1.1":
             coords= read_gpx_1_1(gpx_file_path)
     elif file_extension == '.igc':
         coords= read_igc(gpx_file_path)
     else:
         show_message_box("Unsupported file format. Please use .gpx or .igc files.")
         toggle_console()
         return 

     print(f"poats: {len(coords)}")
     
     return coords


# Load cache from disk
def load_elevation_cache():
    """Load the elevation cache from disk"""

    global _elevation_cache
    if os.path.exists(elevation_cache_file):
        try:
            with open(elevation_cache_file, "r") as f:
                _elevation_cache = json.load(f)
        except Exception as e:
            print(f"Error loading elevation cache: {str(e)}")
            _elevation_cache = {}
    else:
        _elevation_cache = {}

# Save cache to disk
def save_elevation_cache():
    """Save the elevation cache to disk"""
    # Limit cache size to prevent excessive file sizes
    print(f"Currently cached:  {len(_elevation_cache)}")
    if len(_elevation_cache) > cacheSize:
        # Keep only the most recent entries
        keys = list(_elevation_cache.keys())
        for key in keys[:-cacheSize]:
            del _elevation_cache[key]
            
    try:
        with open(elevation_cache_file, "w") as f:
            json.dump(_elevation_cache, f)
    except Exception as e:
        print(f"Error saving elevation cache: {str(e)}")

def get_cached_elevation(lat, lon, api_type="opentopodata"):
    """Get elevation from cache if available"""
    key = f"{lat:.5f}_{lon:.5f}_{api_type}"
    return _elevation_cache.get(key)

def cache_elevation(lat, lon, elevation, api_type="opentopodata"):
    """Cache elevation data"""
    key = f"{lat:.5f}_{lon:.5f}_{api_type}"
    _elevation_cache[key] = elevation

def setupColors():
    #Create or get green material
    mat_name = "BASE"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.05, 0.7, 0.05, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
    #Create or get green material
    mat_name = "FOREST"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.05, 0.25, 0.05, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
    
    #Create or get Gray material
    mat_name = "MOUNTAIN"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
    
    #Create or get Blue material
    mat_name = "WATER"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.8, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
    
    #Create or get Red material
    mat_name = "TRAIL"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (1.0, 0.0, 0.0, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
    
    #Create or get Yellow material
    mat_name = "CITY"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.7, 0.7, 0.1, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------

    #Create or get Whiteish material
    mat_name = "GLACIER"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.8, 0.9, 0.8, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
      
    #Create or get Black material
    mat_name = "BLACK"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------
          
    #Create or get White material
    mat_name = "WHITE"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials[mat_name]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

    # If none exists, create one
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

    # Find Material Output
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (300, 0)

    # Connect BSDF → Output
    if not bsdf.outputs["BSDF"].is_linked:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    # Set base color
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    
    #-------------------------------------------------------------------------------------------------------------------

def calculate_scale(mapSize, coordinates, tp):
    
    #for lat, lon, ele in coordinates:
    min_lat = min(point[0] for point in coordinates)
    max_lat = max(point[0] for point in coordinates)
    min_lon = min(point[1] for point in coordinates)
    max_lon = max(point[1] for point in coordinates)

    print(f"min_lon: {min_lon}")
    
    R = 6371  # Earth's radius in meters (Web Mercator standard)
    #x1 = R * math.radians(min_lon)
    #x1 = R * math.radians(min_lon) * math.cos(math.radians(min_lat))
    #y1 = R * math.log(math.tan(math.pi / 4 + math.radians(min_lat) / 2))
    #x2 = R * math.radians(max_lon)
    #x2 = R * math.radians(max_lon) * math.cos(math.radians(max_lat))
    #y2 = R * math.log(math.tan(math.pi / 4 + math.radians(max_lat) / 2))
    #width = abs(x2 - x1)
    #height = abs(y2 - y1)
    #distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    print(f"min_lat: {min_lat}, min_lon: {min_lon}")
    x1, y1, e = convert_to_neutral_coordinates(min_lat, min_lon, 0,0)
    x2, y2, e = convert_to_neutral_coordinates(max_lat, max_lon, 0,0)

    if scalemode == "FACTOR" and tp != 2:
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    else:
        width = haversine(min_lat, min_lon, min_lat, max_lon) * 1
        height = haversine(min_lat, min_lon, max_lat,min_lon) * 1
        distance = haversine(min_lat,min_lon,max_lat,max_lon)*1
    
    print(f"Distance in km: {width}")
    print(f"Distance in km: {height}")
    print(f"Distance in km: {distance}")

    #COMMENTED OUT
    #CALCULATES THE ACCURATE SCALE BUT MULTIPLE PATHS TO EACH OTHER WONT ALIGN CORRECTLY WITH IT AS THE "mf"
    #IS DIFFRENT FOR EACH LATITUDE AND THEREFORE HAS A DIFFRENT "COORDINATE SYSTEM"
    if scalemode == "SCALE":
        mx1 = x1 = R * math.radians(min_lon) * math.cos(math.radians(min_lat))
        mx2 = x2 = R * math.radians(max_lon) * math.cos(math.radians(max_lat))
        mwidth = abs(mx1 - mx2)
        mf = 1/width * mwidth
        mf = 1
        print(f"mf: {mf}")

    if scalemode == "COORDINATES" or scalemode == "SCALE":
        distance = 0

    print(f"width: {width}")
    print(f"height: {height}")

    maxer = max(width,height, distance)

    print(f"maxer:{maxer}")
    scale = 1
    print(f"Scalemode: {scalemode}")
    print(f"tp: {tp}")
    if scalemode == "COORDINATES" or tp == 2 or tp == 3:
        print("scalemode1")
        scale = mapSize / maxer
    elif scalemode == "FACTOR":
        scale = (mapSize * pathScale) / maxer
        print(scale)
        print("scalemode2")
    elif scalemode == "SCALE":
        scale = pathScale * mf
        print("scalemode3")

    return scale

def convert_to_blender_coordinates(lat, lon, elevation,timestamp):

    scaleHor = bpy.context.scene.tp3d.sScaleHor
     
    R = 6371  # Earth's radius in meters (Web Mercator standard)
    x = R * math.radians(lon) * scaleHor
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * scaleHor
    z = (elevation - elevationOffset) /1000 * scaleElevation * autoScale
     
    return (x, y, z)

def convert_to_neutral_coordinates(lat, lon, elevation,timestamp):
      
    R = 6371  # Earth's radius in meters (Web Mercator standard)
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    z = (elevation - elevationOffset) /1000 * scaleElevation * autoScale
                   
    return (x, y, z)
 

# Convert offsets to latitude/longitude
def convert_to_geo(x,y):
    """Converts Blender x/y offsets to latitude/longitude."""

    scaleHor = bpy.context.scene.tp3d.sScaleHor
    
    R = 6371  # Earth's radius in meters (Web Mercator standard)
    longitude = math.degrees((x) / (R * scaleHor) )
    latitude = math.degrees(2 * math.atan(math.exp((y) / (R * scaleHor) )) - math.pi / 2)
    return latitude, longitude

def create_curve_from_coordinates(coordinates):
    """
    Create a curve in Blender based on a list of (x, y, z) coordinates.
    """
    # Create a new curve object
    curve_data = bpy.data.curves.new('GPX_Curve', type='CURVE')
    curve_data.dimensions = '3D'
    polyline = curve_data.splines.new('POLY')
    polyline.points.add(count=len(coordinates) - 1)

    # Populate the curve with points
    for i, coord in enumerate(coordinates):
        polyline.points[i].co = (coord[0], coord[1], coord[2], 1)  # (x, y, z, w)

    # Create an object with this curve
    curve_object = bpy.data.objects.new('GPX_Curve_Object', curve_data)
    bpy.context.collection.objects.link(curve_object)
    curve_object.data.bevel_depth = pathThickness/2  # Set the thickness of the curve
    curve_object.data.bevel_resolution = 4  # Set the resolution for smoothness
    
    mod = curve_object.modifiers.new(name="Remesh",type="REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = 0.05 * pathThickness * 10/2
    mod.adaptivity = 0.0
    curve_object.data.use_fill_caps = True
        
    curve_object.data.name = name + "_Trail"
    curve_object.name = name + "_Trail"
         
    curve_object.select_set(True)
  
    bpy.context.view_layer.objects.active = curve_object

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='SELECT')
    #bpy.ops.curve.smooth()
    bpy.ops.object.mode_set(mode='OBJECT')
  
    # Convert to mesh
    if shape == "HEXAGON INNER TEXT" or shape == "HEXAGON OUTER TEXT" or shape == "OCTAGON OUTER TEXT" or shape == "HEXAGON FRONT TEXT":
        #bpy.ops.object.convert(target='MESH')
        pass

def simplify_curve(points_with_extra, min_distance=0.1000):
    """
    Removes points that are too close to any previously accepted point.
    Keeps the full (x, y, z, time) format.
    """

    if not points_with_extra:
        return []

    simplified = [points_with_extra[0]]
    last_xyz = Vector(points_with_extra[0][:3])
    skipped = 0

    for pt in points_with_extra[1:]:
        current_xyz = Vector(pt[:3])
        if (current_xyz - last_xyz).length >= min_distance:
            simplified.append(pt)
            last_xyz = current_xyz
        else:
            skipped += 1
            pass

    print(f"Smooth curve: Removed {skipped} vertices")
    return simplified

def create_hexagon(size):
    """Creates a hexagon at (0,0,0), subdivides it, and rotates it by 90 degrees."""
    verts = []
    faces = []
    num_subdivisions = bpy.context.scene.tp3d.num_subdivisions

    for i in range(6):
        angle = math.radians(60 * i)
        x = size * math.cos(angle)
        y = size * math.sin(angle)
        verts.append((x, y, 0))
    verts.append((0, 0, 0))  # Center vertex
    faces = [[i, (i + 1) % 6, 6] for i in range(6)]
    mesh = bpy.data.meshes.new("Hexagon")
    obj = bpy.data.objects.new("Hexagon", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    #bpy.ops.mesh.subdivide(number_cuts=num_subdivisions)
    for _ in range(num_subdivisions):
        bpy.ops.mesh.subdivide(number_cuts=1)  # 1 cut per loop for even refinement
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.name = name
    obj.data.name = name
    return obj

def create_rectangle(width, height):
    """Creates a rectangle at (0,0,0), subdivides it, and rotates it by 90 degrees."""

    num_subdivisions = bpy.context.scene.tp3d.get('num_subdivisions', 4)
    verts = [
        (-width / 2, -height / 2, 0),  # Bottom-left
        (width / 2, -height / 2, 0),   # Bottom-right
        (width / 2, height / 2, 0),    # Top-right
        (-width / 2, height / 2, 0)    # Top-left
    ]
    faces = [[0, 1, 2, 3]]
    mesh = bpy.data.meshes.new("Rectangle")
    obj = bpy.data.objects.new("Rectangle", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for _ in range(num_subdivisions+1):
        bpy.ops.mesh.subdivide(number_cuts=1)  # 1 cut per loop for even refinement
    #bpy.ops.mesh.subdivide(number_cuts=num_subdivisions)  # Can change number of subdivisions if needed
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.name = name
    obj.data.name = name
    
    return obj

def create_circle(radius):
    """Creates a circle at (0,0,0), subdivides it."""
    verts = []
    faces = []
    num_subdivisions = bpy.context.scene.tp3d.num_subdivisions
    
    # 64 segments creates a smooth looking circle
    segments = 64
    
    # Create the outer ring vertices
    for i in range(segments):
        angle = math.radians((360 / segments) * i)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        verts.append((x, y, 0))
    
    verts.append((0, 0, 0))  # Center vertex
    
    # Create faces connecting outer ring to center
    # The center vertex is at index 'segments'
    faces = [[i, (i + 1) % segments, segments] for i in range(segments)]
    
    mesh = bpy.data.meshes.new("Circle")
    obj = bpy.data.objects.new("Circle", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Subdivide to create grid for terrain elevation
    for _ in range(num_subdivisions):
        bpy.ops.mesh.subdivide(number_cuts=1) 
        
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.name = name
    obj.data.name = name
    return obj
        
# Get real elevation for a point
def get_elevation_single(lat, lon):
    """Fetches real elevation for a single latitude and longitude using OpenTopoData."""
    url = f"https://api.opentopodata.org/v1/{dataset}?locations={lat},{lon}"
    response = requests.get(url).json()
    elevation = response['results'][0]['elevation'] if 'results' in response else 0
    return elevation

# Scale down elevation to match Blender terrain
 
def get_elevation_openTopoData(coords, lenv = 0, pointsDone = 0):
    """Fetches real elevation for each vertex using OpenTopoData with request batching."""

    disableCache = bpy.context.scene.tp3d.get("disableCache",0)

    # Ensure the cache is loaded
    if not _elevation_cache:
        load_elevation_cache()

    # First, check which coordinates need fetching (not in cache)
    coords_to_fetch = []
    coords_indices = []

    elevations = [0] * len(coords)  # Pre-allocate list
    
    
    #check if coordinates are in cache or not
    for i, (lat, lon) in enumerate(coords):
        cached_elevation = get_cached_elevation(lat, lon)
        if cached_elevation is not None and disableCache == 0:
            # Use cached elevation
            elevations[i] = cached_elevation
        else:
            # Need to fetch this coordinate
            elevations[i] = -5
            coords_to_fetch.append((lat, lon))
            coords_indices.append(i)

    if len(coords) - len(coords_to_fetch) > 0:
        print(f"Using: {len(coords) - len(coords_to_fetch)} cached Coordinates")

    # If all elevations were found in cache, return immediately
    if not coords_to_fetch:
        return elevations

    #coords = [convert_to_geo(y, x, v[0], v[1]) for v in vertices]
    #elevations = []
    batch_size = 100
    for i in range(0, len(coords_to_fetch), batch_size):
        batch = coords_to_fetch[i:i + batch_size]
        query = "|".join([f"{c[0]},{c[1]}" for c in batch])
        url = f"{opentopoAdress}{dataset}?locations={query}"
        #print(url)
        last_request_time = time.monotonic()
        response = requests.get(url)
        nr = i + len(batch) + pointsDone
        addition = f" {nr}/{int(lenv)}"
        send_api_request(addition)
        response.raise_for_status()
                  
        data = response.json()
        # Handle the elevation data and replace 'null' with 0
        for o, result in enumerate(data['results']):
            elevation = result.get('elevation', None)  # Safe get, default to None if key is missing
            if elevation is None:
                elevation = 0  # Replace None (null in JSON) with 0
            cache_elevation(batch[o][0], batch[o][1], elevation)
            ind = coords_indices[i+o]
            elevations[ind] = elevation
        
        # Get current time
        now = time.monotonic()  # Monotonic time is safer for measuring elapsed time
        elapsed_time = now - last_request_time
        if i + batch_size < len(coords_to_fetch) and elapsed_time < 1.3:
            time.sleep(1.3 - elapsed_time)  # Pause to prevent request throttling
   
    return elevations

def get_elevation_openElevation(coords, lenv = 0, pointsDone = 0):
    """Fetches real elevation for each vertex using Open-Elevation with request batching."""
    
    elevations = []
    batch_size = 1000
    for i in range(0, len(coords), batch_size):
        batch = coords[i:i + batch_size]
        # Open-Elevation expects a POST request with JSON body
        payload = {"locations": [{"latitude": c[0], "longitude": c[1]} for c in batch]}
        url = "https://api.open-elevation.com/api/v1/lookup"
        last_request_time = time.monotonic()
        
        headers = {'Content-Type': 'application/json'}
        nr = i + len(batch) + pointsDone
        addition = f" {nr}/{int(lenv)}"
        send_api_request(addition)
        
        response = requests.post(url, json=payload, headers=headers)
        
        #print(url)
        #print(payload)
        
        response.raise_for_status()

        data = response.json()
                  
        # Handle the elevation data and replace 'null' with 0
        for result in data['results']:
            elevation = result.get('elevation', None)
            if elevation is None:
                elevation = 0
            elevations.append(elevation)
        
        # Get current time for request rate limiting
        now = time.monotonic() 
        
        elapsed_time = now - last_request_time
        if elapsed_time < 2:
            time.sleep(2 - elapsed_time)  # Pause to prevent request throttling

    return elevations

def lonlat_to_tilexy(lon, lat, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def lonlat_to_pixelxy(lon, lat, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n * 256
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n * 256
    return int(x % 256), int(y % 256)

def fetch_terrarium_tile_raw(zoom, xtile, ytile):
    """Fetch the raw PNG binary data for a tile, either from cache or online."""
    tile_path = os.path.join(terrarium_cache_dir, f"{zoom}_{xtile}_{ytile}.png")
    if not os.path.exists(tile_path):
        url = f"https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{zoom}/{xtile}/{ytile}.png"
        #print("Sending Request")
        response = requests.get(url)
        response.raise_for_status()
        with open(tile_path, "wb") as f:
            f.write(response.content)
    with open(tile_path, "rb") as f:
        return f.read()

def paeth_predictor(a, b, c):
    # PNG Paeth filter
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c

def parse_png_rgb_data(png_bytes):
    """Extract uncompressed RGB bytes from a PNG image (supports all PNG filter types)."""
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    offset = 8
    width = height = None
    idat_data = b''

    while offset < len(png_bytes):
        length = struct.unpack(">I", png_bytes[offset:offset+4])[0]
        chunk_type = png_bytes[offset+4:offset+8]
        data = png_bytes[offset+8:offset+8+length]
        offset += 12 + length

        if chunk_type == b'IHDR':
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", data)
            assert bit_depth == 8 and color_type == 2, "Only 8-bit RGB PNGs supported"
        elif chunk_type == b'IDAT':
            idat_data += data
        elif chunk_type == b'IEND':
            break

    raw = zlib.decompress(idat_data)
    stride = 3 * width
    rgb_array = []
    prev_row = bytearray(stride)

    for y in range(height):
        i = y * (stride + 1)
        filter_type = raw[i]
        scanline = bytearray(raw[i + 1:i + 1 + stride])
        recon = bytearray(stride)

        if filter_type == 0:
            recon[:] = scanline
        elif filter_type == 1:  # Sub
            for i in range(stride):
                val = scanline[i]
                left = recon[i - 3] if i >= 3 else 0
                recon[i] = (val + left) % 256
        elif filter_type == 2:  # Up
            for i in range(stride):
                recon[i] = (scanline[i] + prev_row[i]) % 256
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = recon[i - 3] if i >= 3 else 0
                up = prev_row[i]
                recon[i] = (scanline[i] + (left + up) // 2) % 256
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                a = recon[i - 3] if i >= 3 else 0
                b = prev_row[i]
                c = prev_row[i - 3] if i >= 3 else 0
                recon[i] = (scanline[i] + paeth_predictor(a, b, c)) % 256
        else:
            raise ValueError(f"Unsupported filter type {filter_type}")

        # Convert scanline to list of (R, G, B) tuples
        row = [(recon[i], recon[i+1], recon[i+2]) for i in range(0, stride, 3)]
        rgb_array.append(row)
        prev_row = recon

    return rgb_array


def terrarium_pixel_to_elevation(r, g, b):
    """Convert Terrarium RGB pixel to elevation in meters."""
    return (r * 256 + g + b / 256) - 32768

def get_elevation_TerrainTiles(coords, lenv=0, pointsDone=0, zoom=10):

    #Each Tile requested is a PNG that is 256x256 Pixels big

    realdist1 = haversine(minLat,minLon,minLat,maxLon)*1000
    realdist2 = haversine(maxLat,minLon,maxLat,maxLon)*1000

    #calculating zoom
    zoom = 10
    horVerts = 1 + 2**(num_subdivisions+1)
    dist = 25.00000 / 2**(num_subdivisions-1) #25 is the rough distance between verts on resolution 1
    strt = 156543 #m/Pixel on Tile PNG
    #print(f"dist:{dist}")
    cntr = 2

    #print(f"scaleHor: {scaleHor}")
    vertdist = max(realdist1,realdist2)/horVerts #Distance between 2 vertices
    while strt > vertdist:
        cntr += 1
        strt /= 2
        #print(f"halved: {strt:.2f}, {cntr}, {vertdist:.2f}")
    #Max zoom level to 14
    cntr = min(cntr,15)

    #print(f"horVerts: {horVerts}")
    print(f"Zoom Level for API: {cntr}, Start fetching Data...")
        #print(f"calculated distance: {dist}")
    zoom = cntr
                

    tile_dict = {}
    for idx, (lat, lon) in enumerate(coords):
        xtile, ytile = lonlat_to_tilexy(lon, lat, zoom)
        tile_dict.setdefault((xtile, ytile), []).append((idx, lat, lon))

    total_tiles = len(tile_dict)
    progress_intervals = set(range(10,101,10))
    elevations = [0] * len(coords)
    for i, ((xtile, ytile), idx_lat_lon_list) in enumerate(tile_dict.items(), 1):
        percent_complete = int((i/ total_tiles) * 100)
        if percent_complete in progress_intervals:
            print(f"{datetime.now().strftime('%H:%M:%S')} - {percent_complete}% complete, {i}")
            progress_intervals.remove(percent_complete)
        try:
            png_bytes = fetch_terrarium_tile_raw(zoom, xtile, ytile)
            rgb_array = parse_png_rgb_data(png_bytes)
        except Exception as e:
            print(f"Failed to fetch or parse tile {zoom}/{xtile}/{ytile}: {e}")
            for idx, _, _ in idx_lat_lon_list:
                elevations[idx] = 0
            continue

        for idx, lat, lon in idx_lat_lon_list:
            px, py = lonlat_to_pixelxy(lon, lat, zoom)
            px = min(max(px, 0), 255)
            py = min(max(py, 0), 255)
            r, g, b = rgb_array[py][px]
            temp_ele = terrarium_pixel_to_elevation(r, g, b)
            if temp_ele < -1:
                temp_ele = -1
                global buggyDataset
                buggyDataset = 1
            elevations[idx] = temp_ele
        
    
    return elevations

def get_elevation_path_openElevation(vertices):
    """Fetches real elevation for each vertex using OpenTopoData with request batching."""
    v = vertices
    coords = [(v[0], v[1], v[2], v[3]) for v in vertices]
    elevations = []
    batch_size = 1000
    for i in range(0, len(coords), batch_size):
        batch = coords[i:i + batch_size]
        # Open-Elevation expects a POST request with JSON body
        payload = {"locations": [{"latitude": c[0], "longitude": c[1]} for c in batch]}
        url = "https://api.open-elevation.com/api/v1/lookup"
        last_request_time = time.monotonic()
        
        headers = {'Content-Type': 'application/json'}

        addition = f"(overwrite path) {i + len(batch)}/{len(coords)}"
        send_api_request(addition)

        response = requests.post(url, json=payload, headers=headers)
        
        #print(url)
        #print(payload)
        
        response.raise_for_status()

        data = response.json()
        
        elevations.extend([r['elevation'] for r in data['results']])
        now = time.monotonic()  # Monotonic time is safer for measuring elapsed time
        elapsed_time = now - last_request_time
        if i + batch_size < len(coords) and elapsed_time < 1.4:
            time.sleep(1.4 - elapsed_time)  # Pause to prevent request throttling
    
    for i in range(len(vertices)):
        coords[i] =  (coords[i][0], coords[i][1], elevations[i], coords[i][3])
        #print(elevations[i])

    return coords # Get real elevation for each vertex

def get_elevation_path_openTopoData(vertices):
    """Fetches real elevation for each vertex using OpenTopoData with request batching."""
    v = vertices
    coords = [(v[0], v[1], v[2], v[3]) for v in vertices]
    elevations = []
    batch_size = 100
    for i in range(0, len(coords), batch_size):
        batch = coords[i:i + batch_size]
        query = "|".join([f"{c[0]},{c[1]}" for c in batch])
        url = f"{opentopoAdress}{dataset}?locations={query}"
        last_request_time = time.monotonic()
        response = requests.get(url).json()
        addition = f"(overwrite path) {i + len(batch)}/{len(coords)}"
        send_api_request(addition)
        
        #elevations.extend([r['elevation'] for r in response['results']])
        elevations.extend([r.get('elevation') or 0 for r in response['results']])

        now = time.monotonic()  # Monotonic time is safer for measuring elapsed time
        elapsed_time = now - last_request_time
        if i + batch_size < len(coords) and elapsed_time < 1.4:
            time.sleep(1.4 - elapsed_time)  # Pause to prevent request throttling
    
    for i in range(len(vertices)):
        coords[i] =  (coords[i][0], coords[i][1], elevations[i], coords[i][3])
        #print(elevations[i])

    return coords

def RaycastCurveToMesh(curve_obj, mesh_obj):
    
    print("---")
    print(mesh_obj.name)
    #MOVE EVERY POINT UP BY 100 SO ITS POSSIBLE TO RAYCAST IT DOWNARDS ONTO THE MESH
    offset = Vector((0, 0, 1000))
    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            for p in spline.bezier_points:
                p.co += offset
                # if you want to move the handles too:
                p.handle_left += offset
                p.handle_right += offset
        else:  # POLY / NURBS
            for p in spline.points:
                p.co = (p.co.x, p.co.y, p.co.z + offset.z, p.co.w)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_mesh_obj = mesh_obj.evaluated_get(depsgraph)

    curve_world     = curve_obj.matrix_world
    curve_world_inv = curve_world.inverted()

    mesh_world     = eval_mesh_obj.matrix_world
    mesh_world_inv = mesh_world.inverted()

    direction_world = Vector((0, 0, -1))  # world -Z
    direction_local = (mesh_world_inv.to_3x3() @ direction_world).normalized()

    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            points = spline.bezier_points
        else:
            points = spline.points

        for point in points:
            # world-space position of curve point
            if spline.type == 'BEZIER':
                co_world = curve_world @ point.co
            else:
                co_world = curve_world @ point.co.xyz

            # convert origin to mesh local
            co_local = mesh_world_inv @ co_world

            # raycast in mesh local space
            success, hit_loc, normal, face_index = eval_mesh_obj.ray_cast(co_local, direction_local)

            if success:
                # back to world space
                hit_world = mesh_world @ hit_loc
                # then into curve local
                local_hit = curve_world_inv @ hit_world

                if spline.type == 'BEZIER':
                    point.co = local_hit
                    point.handle_left_type = point.handle_right_type = 'AUTO'
                else:
                    point.co = (local_hit.x, local_hit.y, local_hit.z, 1.0)
            else:
                point.co -= Vector((offset.x, offset.y, offset.z, 1.0))

    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT')

    # select all points if you want to smooth everything
    bpy.ops.curve.select_all(action='SELECT')

    # run the smooth operator
    bpy.ops.curve.smooth()

    # back to Object Mode if you like
    bpy.ops.object.mode_set(mode='OBJECT')

    print("Path Elevation Overwritten")

def RaycastCurveToAnyMesh(curve_obj, offset_z=1000.0, smooth_after=True):
    """Move curve points up by offset_z then raycast straight down onto any mesh below.
    Uses scene.ray_cast so the nearest mesh hit is used automatically.
    """

    print("Raycasting")
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    offset = Vector((0.0, 0.0, offset_z))

    # Move points up by offset so we can raycast downwards
    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            for p in spline.bezier_points:
                p.co += offset
                p.handle_left += offset
                p.handle_right += offset
        else:  # POLY / NURBS
            for p in spline.points:
                # p.co is (x, y, z, w)
                p.co = (p.co.x, p.co.y, p.co.z + offset_z, p.co.w)

    curve_world     = curve_obj.matrix_world
    curve_world_inv = curve_world.inverted()

    # ray direction in world space: straight down
    direction_world = Vector((0.0, 0.0, -1.0))

    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            points = spline.bezier_points
        else:
            points = spline.points

        for point in points:
            # get world-space position of the point
            if spline.type == 'BEZIER':
                co_world = curve_world @ point.co
            else:
                co_world = curve_world @ point.co.xyz

            # cast ray from this origin straight down in world-space
            # scene.ray_cast returns (result, location, normal, face_index, object, matrix)
            hit_result = scene.ray_cast(depsgraph, co_world, direction_world)
            hit_success = hit_result[0]

            if hit_success:
                hit_loc_world = hit_result[1]

                # convert hit back into curve local space
                local_hit = curve_world_inv @ hit_loc_world

                if spline.type == 'BEZIER':
                    point.co = local_hit
                    # keep handles auto to get a reasonable shape; alternatively compute
                    point.handle_left_type = point.handle_right_type = 'AUTO'
                else:
                    # preserve w component
                    w = getattr(point.co, "w", 1.0)
                    point.co = (local_hit.x, local_hit.y, local_hit.z, w)

    # optional smoothing (go into edit mode, smooth, come back)
    if smooth_after:
        bpy.context.view_layer.objects.active = curve_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.smooth()
        bpy.ops.object.mode_set(mode='OBJECT')

    print("Curve projected onto nearest mesh below each point.")
  

# Get tile elevation
def get_tile_elevation(obj):

    mesh = obj.data
    global api
    api = bpy.context.scene.tp3d.get('api',2)
    
    # Set chunk size based on API
    if api == 0 or api == 1:
        chunk_size = 100000
    elif api == 2:
        chunk_size = 50000000
    else:
        chunk_size = 100000  # fallback

    vertices = list(mesh.vertices)
    obj_matrix = obj.matrix_world

    # Convert all vertex positions to world space
    world_verts = [obj_matrix @ v.co for v in vertices]

    # Get min/max bounds in world space
    min_x = min(v.x for v in world_verts)
    max_x = max(v.x for v in world_verts)
    min_y = min(v.y for v in world_verts)
    max_y = max(v.y for v in world_verts)

    global minLon, maxLon, minLat, maxLat

    # Use object's world location as reference origin
    origin_lat = obj_matrix.translation.y
    origin_lon = obj_matrix.translation.x

    minl = convert_to_geo(min_x, min_y)
    maxl = convert_to_geo(max_x, max_y)

    minLat = minl[0]
    maxLat = maxl[0]
    minLon = minl[1]
    maxLon = maxl[1]

    realdist1 = haversine(minLat,minLon,maxLat,maxLon)*1
    realdist2 = haversine(minLat,minLon,maxLat,maxLon)*1
    bpy.context.scene.tp3d["sMapInKm"] = max(realdist1,realdist2)

    elevations = []
    for i in range(0, len(world_verts), chunk_size):
        chunk = world_verts[i:i + chunk_size]

        coords = [convert_to_geo(v.x, v.y) for v in chunk]

        if api == 0:
            chunk_elevations = get_elevation_openTopoData(coords, len(vertices), i)
        elif api == 1:
            chunk_elevations = get_elevation_openElevation(coords, len(vertices), i)
        elif api == 2:
            #print(f"Loading {i}/{len(vertices)}")
            chunk_elevations = get_elevation_TerrainTiles(coords, len(vertices), i)
        else:
            chunk_elevations = [0.0] * len(chunk)  # fallback

        elevations.extend(chunk_elevations)

        # Free memory after processing chunk
        del chunk_elevations

    save_elevation_cache()

    global lowestZ
    global highestZ
    lowestZ = min(elevations)
    highestZ = max(elevations)
    global additionalExtrusion
    additionalExtrusion = lowestZ
    diff = highestZ - lowestZ

    bpy.context.scene.tp3d["o_verticesMap"] = str(len(mesh.vertices))

    return elevations, diff

# Transform MapObject
def transform_MapObject(obj, newX, newY):
    obj.location.x += newX
    obj.location.y += newY

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points using the Haversine formula."""
    R = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c  # distance in kilometers
    #print(f"Distance between 2 points: {distance}")
    return distance
    

def calculate_total_length(points):
    #Calculates the total path length in kilometers.
    total_distance = 0.0
    for i in range(1, len(points)):
        lon1, lat1, _, _ = points[i - 1]
        lon2, lat2, _, _ = points[i]
        total_distance += haversine(lon1, lat1, lon2, lat2)
    return total_distance

def calculate_total_elevation(points):
    #Calculates the total elevation gain in meters.
    total_elevation = 0.0
    for i in range(1, len(points)):
        _, _, elev1, _ = points[i - 1]
        _, _, elev2, _ = points[i]
        if elev2 > elev1:
            total_elevation += elev2 - elev1
    return total_elevation

def calculate_total_time(points):
    hrs = 0
    #Calculates the total time taken between the first and last points.
    if len(points) < 2:
        return 0.0
    start_time = points[0][3]
    end_time = points[-1][3]
    if start_time != None and end_time != None:
        time_diff = end_time - start_time
        hours = int(time_diff.total_seconds() / 3600)
        minutes = int((time_diff.total_seconds() / 3600 - hours) * 60)
        time_str = f"{hours}h {minutes}m"
        #print(time_str)
        hrs = time_diff.total_seconds() / 3600

        return hrs

def update_text_object(obj_name, new_text):
    """Updates the text of a Blender text object."""
    text_obj = bpy.data.objects.get(obj_name)
    if text_obj and text_obj.type == 'FONT':
        text_obj.data.body = new_text

def export_to_STL(zobj,force = "STL"):
   
    exportPath = bpy.context.scene.tp3d.get('export_path', None)
    bpy.ops.object.select_all(action='DESELECT')
    zobj.select_set(True)
    bpy.context.view_layer.objects.active = zobj

    if zobj.material_slots and force != "STL":  
        bpy.ops.wm.obj_export(filepath=exportPath + zobj.name + ".obj",
            export_selected_objects=True,
            export_triangulated_mesh=True, 
            apply_modifiers=True,
            export_materials=True,
            forward_axis="Y",
            up_axis="Z",
            )
        #show_message_box("File Exported as OBJ because it contains Materials","INFO","OBJ File Exported")
    else:
        bpy.ops.wm.stl_export(filepath=exportPath +  zobj.name + ".stl", export_selected_objects = True)
        #show_message_box("File Exported to your selected directory","INFO","File Exported")
    
    zobj.select_set(False)  # Select the object

def export_selected_to_STL(force = "STL"):
    
    exportPath = bpy.context.scene.tp3d.get('export_path', None)
    selected_objects = bpy.context.selected_objects
    active_obj = bpy.context.active_object

    if not selected_objects:
            show_message_box("No objects selected")
            return{'FINISHED'}

    for zobj in selected_objects:
        bpy.ops.object.select_all(action='DESELECT')
        zobj.select_set(True)
        bpy.context.view_layer.objects.active = zobj

        if (zobj.material_slots or force == "OBJ") and force != "STL":  
            bpy.ops.wm.obj_export(filepath=exportPath + zobj.name + ".obj",
                export_selected_objects=True,
                export_triangulated_mesh=True, 
                apply_modifiers=True,
                export_materials=True,
                forward_axis="Y",
                up_axis="Z",
                )
            #show_message_box("File Exported as OBJ because it contains Materials","INFO","OBJ File Exported")
            show_message_box("OBJ Exported to your selected directory","INFO","File Exported")
        else:
            bpy.ops.wm.stl_export(filepath=exportPath +  zobj.name + ".stl", export_selected_objects = True)
            show_message_box("STL Exported to your selected directory","INFO","File Exported")


    bpy.ops.object.select_all(action='DESELECT')
    for zobj in selected_objects:
        zobj.select_set(True)
    bpy.context.view_layer.objects.active = active_obj
    
    
    active_obj = bpy.context.active_object

def zoom_camera_to_selected(obj):

    bpy.ops.object.select_all(action='DESELECT')

    obj.select_set(True)  # Select the object

    area = [area for area in bpy.context.screen.areas if area.type == "VIEW_3D"][0]
    region = area.regions[-1]

    with bpy.context.temp_override(area=area, region=region):
        bpy.ops.view3d.view_selected(use_all_regions=False)
            

def create_text(name, text, position, scale_multiplier, rotation=(0, 0, 0), extrude=20):
    txt_data = bpy.data.curves.new(name=name, type='FONT')
    txt_obj = bpy.data.objects.new(name=name, object_data=txt_data)
    bpy.context.collection.objects.link(txt_obj)
    
    global textFont
    # 不要只用 .get("textFont", "")，如果得到的是空字符串，就赋给它默认值
    temp_font = bpy.context.scene.tp3d.textFont
    if not temp_font:
        textFont = r"C:\Windows\Fonts\msyhbd.ttc"
    else:
        textFont = temp_font
        
    txt_data.body = text
    txt_data.extrude = extrude
    #txt_data.font = bpy.data.fonts.load("C:/Windows/Fonts/ariblk.ttf")  # Adjust path if needed
    txt_data.font = bpy.data.fonts.load(textFont)
    txt_data.align_x = 'CENTER'
    txt_data.align_y = "CENTER"
    
    txt_obj.scale = (scale_multiplier, scale_multiplier, 1)
    txt_obj.location = position
    txt_obj.rotation_euler = rotation
    
    txt_obj.location.z -= 1
    
    return txt_obj

def HexagonInnerText():

    global total_elevation
    global total_length

    textSize = bpy.context.scene.tp3d.textSize
    textSize2 = bpy.context.scene.tp3d.textSizeTitle

    if textSize2 == 0:
        textSize2 = textSize
          
        
    dist =  (size/2 - size/2 * (1-pathScale)/2)
    
    temp_y = math.sin(math.radians(90)) * (dist  * math.cos(math.radians(30)))
      
    tName = create_text("t_name", "Name", (0, temp_y, 0.1),1)

    for i, (text_name, angle) in enumerate(zip(["t_length", "t_elevation", "t_duration"], [210, 270, 330])):
        angle_centered = angle + 90
        x = math.cos(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        y = math.sin(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        rot_z = math.radians(angle_centered)
        create_text(text_name, text_name.split("_")[1].capitalize(), (x, y, 0.1),1,  (0, 0, rot_z), 100)

    tElevation = bpy.data.objects.get("t_elevation")
    tLength = bpy.data.objects.get("t_length")
    tDuration = bpy.data.objects.get("t_duration")
            
    transform_MapObject(tName, centerx + xTerrainOffset, centery + yTerrainOffset)
    transform_MapObject(tElevation, centerx + xTerrainOffset, centery + yTerrainOffset)
    transform_MapObject(tLength, centerx + xTerrainOffset, centery + yTerrainOffset)
    transform_MapObject(tDuration,centerx + xTerrainOffset, centery + yTerrainOffset)
    

    update_text_object("t_name", f"{name}")
    update_text_object("t_elevation", f"{total_elevation:.2f} hm")
    update_text_object("t_length", f"{total_length:.2f} km")
    update_text_object("t_duration", f"{time_str}")

    if overwriteLength != "":
        update_text_object("t_length", overwriteLength)
    if overwriteHeight != "":
        update_text_object("t_elevation", overwriteHeight)
    if overwriteTime != "":
        update_text_object("t_duration", overwriteTime)

    #Scale text sizes to mm values (blender units)
    bpy.context.view_layer.update()
    current_height = tName.dimensions.y
    if current_height == 0:
        current_height = tElevation.dimensions.y
    if current_height == 0:
        current_height = tLength.dimensions.y
    if current_height == 0:
        current_height = 5
    scale_factor = textSize2 / current_height
    tName.scale.x *= scale_factor
    tName.scale.y *= scale_factor

    scale_factor = textSize / current_height
    tElevation.scale.x *= scale_factor
    tLength.scale.x *= scale_factor
    tDuration.scale.x *= scale_factor
    tElevation.scale.y *= scale_factor
    tLength.scale.y *= scale_factor
    tDuration.scale.y *= scale_factor

    #SHAPE ROTATION
    tName.select_set(True)
    tElevation.select_set(True)
    tLength.select_set(True)
    tDuration.select_set(True)
    bpy.context.view_layer.objects.active = tName
    #bpy.ops.object.transform_apply(location = False, rotation=True, scale = False)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    tName.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    tElevation.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    tLength.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    tDuration.rotation_euler[2] += shapeRotation * (3.14159265 / 180)

    convert_text_to_mesh("t_name", MapObject.name)
    convert_text_to_mesh("t_elevation", MapObject.name)
    convert_text_to_mesh("t_length", MapObject.name)
    convert_text_to_mesh("t_duration", MapObject.name)
        

    bpy.ops.object.select_all(action='DESELECT')

    tName.select_set(True)
    tElevation.select_set(True)
    tLength.select_set(True)
    tDuration.select_set(True)
    #curveObj.select_set(True)
    
    bpy.context.view_layer.objects.active = tName
    
    bpy.ops.object.join()

    tName.name = name + "_Text"


    #SHAPE ROTATION
    tName.select_set(True)
    bpy.context.view_layer.objects.active = tName
    bpy.ops.object.transform_apply(location = False, rotation=True, scale = False)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')


    global textobj
    textobj = tName

def HexagonOuterText():
    
    outersize = size * ( 1 + outerBorderSize/100)
    thickness = plateThickness
    textSize = bpy.context.scene.tp3d.textSize
    textSize2 = bpy.context.scene.tp3d.textSizeTitle

    if textSize2 == 0:
        textSize2 = textSize
        

    verts = []
    faces = []
    for i in range(6):
        angle = math.radians(60 * i)
        x = outersize/2 * math.cos(angle)
        y = outersize/2 * math.sin(angle)
        verts.append((x, y, 0))
    verts.append((0, 0, 0))  # Center vertex
    faces = [[i, (i + 1) % 6, 6] for i in range(6)]
    mesh = bpy.data.meshes.new("HexagonOuter")
    outerHex = bpy.data.objects.new("HexagonOuter", mesh)
    bpy.context.collection.objects.link(outerHex)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    outerHex.name = name
    outerHex.data.name = name
    
    bpy.context.view_layer.objects.active = outerHex
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move()
    bpy.ops.transform.translate(value=(0, 0, -8))#bpy.ops.mesh.select_all(action='DESELECT')

    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the mesh data
    mesh = outerHex.data

    # Get selected faces
    selected_faces = [face for face in mesh.polygons if face.select]
    
    if selected_faces:
        for face in selected_faces:
            for vert_idx in face.vertices:
                vert = mesh.vertices[vert_idx]
                vert.co.z =  - thickness
    else:
        print("No face selected.")

    transform_MapObject(outerHex, centerx, centery)
        

    dist = (outersize - size)/4 + size/2
    
    temp_y = math.sin(math.radians(90)) * (dist  * math.cos(math.radians(30)))
        

    #t_name = create_text("t_name", "Name", (0, temp_y, 1 + additionalExtrusion - 2 ),text_size,(0, 0, 0),0.4)

    for i, (text_name, angle) in enumerate(zip(["t_name","t_length", "t_elevation", "t_duration"], [90 + text_angle_preset, 210 + text_angle_preset, 270 + text_angle_preset, 330 + text_angle_preset])):
        angle_centered = angle + 90
        x = math.cos(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        y = math.sin(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        rot_z = math.radians(angle_centered)
        if i == 0:
            rot_z += math.radians(180)
        create_text(text_name, text_name.split("_")[1].capitalize(), (x, y,1.4),1,  (0, 0, rot_z), 0.4)

    tName = bpy.data.objects.get("t_name")
    tElevation = bpy.data.objects.get("t_elevation")
    tLength = bpy.data.objects.get("t_length")
    tDuration = bpy.data.objects.get("t_duration")
          
    transform_MapObject(tName, centerx, centery)
    transform_MapObject(tElevation, centerx, centery)
    transform_MapObject(tLength, centerx, centery)
    transform_MapObject(tDuration, centerx, centery)
    

    update_text_object("t_name", f"{name}")
    update_text_object("t_elevation", f"{total_elevation:.2f} hm")
    update_text_object("t_length", f"{total_length:.2f} km")
    update_text_object("t_duration", f"{time_str}")

    if overwriteLength != "":
        update_text_object("t_length", overwriteLength)
    if overwriteHeight != "":
        update_text_object("t_elevation", overwriteHeight)
    if overwriteTime != "":
        update_text_object("t_duration", overwriteTime)

    #Scale text sizes to mm values (blender units)
    bpy.context.view_layer.update()
    current_height = tName.dimensions.y
    if current_height == 0:
        current_height = tElevation.dimensions.y
    if current_height == 0:
        current_height = tLength.dimensions.y
    if current_height == 0:
        current_height = 5
            
    scale_factor = textSize2 / current_height
    tName.scale.x *= scale_factor
    tName.scale.y *= scale_factor

    scale_factor = textSize / current_height
    tElevation.scale.x *= scale_factor
    tLength.scale.x *= scale_factor
    tDuration.scale.x *= scale_factor
    tElevation.scale.y *= scale_factor
    tLength.scale.y *= scale_factor
    tDuration.scale.y *= scale_factor

    
    convert_text_to_mesh("t_name", outerHex.name, False)
    convert_text_to_mesh("t_elevation", outerHex.name, False)
    convert_text_to_mesh("t_length", outerHex.name, False)
    convert_text_to_mesh("t_duration", outerHex.name, False)
        

    bpy.ops.object.select_all(action='DESELECT')

    tName.select_set(True)
    tElevation.select_set(True)
    tLength.select_set(True)
    tDuration.select_set(True)
    
    bpy.context.view_layer.objects.active = tName
    
    bpy.ops.object.join()

    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    
    tName.name = name + "_Text"
    outerHex.name = name + "_Plate"

    tName.location.z += plateThickness
    outerHex.location.z += plateThickness
  
    # 设置底盘为黑色
    mat_black = bpy.data.materials.get("BLACK")
    if mat_black:
        if len(outerHex.data.materials) > 0:
            outerHex.data.materials.clear()
        outerHex.data.materials.append(mat_black)
  
    #SHAPE ROTATION
    outerHex.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    outerHex.select_set(True)
    bpy.context.view_layer.objects.active = outerHex
    bpy.ops.object.transform_apply(location = False, rotation=True, scale = False)

    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')


    global plateobj
    plateobj = outerHex

    global textobj
    textobj = tName


def HexagonFrontText():
    
    outersize = size * ( 1 + outerBorderSize/100)
    thickness = plateThickness
    textSize = bpy.context.scene.tp3d.textSize
    textSize2 = bpy.context.scene.tp3d.textSizeTitle

    if textSize2 == 0:
        textSize2 = textSize
        

    verts = []
    faces = []
    for i in range(6):
        angle = math.radians(60 * i)
        x = outersize/2 * math.cos(angle)
        y = outersize/2 * math.sin(angle)
        verts.append((x, y, 0))
    verts.append((0, 0, 0))  # Center vertex
    faces = [[i, (i + 1) % 6, 6] for i in range(6)]
    mesh = bpy.data.meshes.new("HexagonOuter")
    outerHex = bpy.data.objects.new("HexagonOuter", mesh)
    bpy.context.collection.objects.link(outerHex)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    outerHex.name = name
    outerHex.data.name = name
    
    bpy.context.view_layer.objects.active = outerHex
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move()
    bpy.ops.transform.translate(value=(0, 0, -8))#bpy.ops.mesh.select_all(action='DESELECT')

    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the mesh data
    mesh = outerHex.data

    # Get selected faces
    selected_faces = [face for face in mesh.polygons if face.select]
    
    if selected_faces:
        for face in selected_faces:
            for vert_idx in face.vertices:
                vert = mesh.vertices[vert_idx]
                vert.co.z =  - thickness;
    else:
        print("No face selected.")

    transform_MapObject(outerHex, centerx, centery)

    dist = outersize/2
    
    temp_y = math.sin(math.radians(90)) * (dist  * math.cos(math.radians(30)))
        

    for i, (text_name, angle) in enumerate(zip(["t_name","t_length", "t_elevation", "t_duration"], [90 + text_angle_preset, 210 + text_angle_preset, 270 + text_angle_preset, 330 + text_angle_preset])):
        angle_centered = angle + 90
        x = math.cos(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        y = math.sin(math.radians(angle)) * (dist * math.cos(math.radians(30)))
        rot_z = math.radians(angle_centered)
        #if i == 0:
            #rot_z += math.radians(180)
        create_text(text_name, text_name.split("_")[1].capitalize(), (x, y,minThickness/2 - plateThickness / 2),1,  (math.radians(90), 0, rot_z), 0.4)

    tName = bpy.data.objects.get("t_name")
    tElevation = bpy.data.objects.get("t_elevation")
    tLength = bpy.data.objects.get("t_length")
    tDuration = bpy.data.objects.get("t_duration")
          
    transform_MapObject(tName, centerx, centery)
    transform_MapObject(tElevation, centerx, centery)
    transform_MapObject(tLength, centerx, centery)
    transform_MapObject(tDuration, centerx, centery)
    

    update_text_object("t_name", f"{name}")
    update_text_object("t_elevation", f"{total_elevation:.2f} hm")
    update_text_object("t_length", f"{total_length:.2f} km")
    update_text_object("t_duration", f"{time_str}")

    if overwriteLength != "":
        update_text_object("t_length", overwriteLength)
    if overwriteHeight != "":
        update_text_object("t_elevation", overwriteHeight)
    if overwriteTime != "":
        update_text_object("t_duration", overwriteTime)

    #Scale text sizes to mm values (blender units)
    bpy.context.view_layer.update()
    current_height = tName.dimensions.y
    if current_height == 0:
        current_height = tElevation.dimensions.y
    if current_height == 0:
        current_height = tLength.dimensions.y
    if current_height == 0:
        current_height = 5
    scale_factor = textSize2 / current_height
    tName.scale.x *= scale_factor
    tName.scale.y *= scale_factor

    scale_factor = textSize / current_height
    tElevation.scale.x *= scale_factor
    tLength.scale.x *= scale_factor
    tDuration.scale.x *= scale_factor
    tElevation.scale.y *= scale_factor
    tLength.scale.y *= scale_factor
    tDuration.scale.y *= scale_factor

    
    convert_text_to_mesh("t_name", outerHex.name, False)
    convert_text_to_mesh("t_elevation", outerHex.name, False)
    convert_text_to_mesh("t_length", outerHex.name, False)
    convert_text_to_mesh("t_duration", outerHex.name, False)
        

    bpy.ops.object.select_all(action='DESELECT')

    tName.select_set(True)
    tElevation.select_set(True)
    tLength.select_set(True)
    tDuration.select_set(True)
    
    bpy.context.view_layer.objects.active = tName
    
    bpy.ops.object.join()
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    

    tName.name = name + "_Text"
    outerHex.name = name + "_Plate"

    tName.location.z += plateThickness
    outerHex.location.z += plateThickness
  
    # 设置底盘为黑色
    mat_black = bpy.data.materials.get("BLACK")
    if mat_black:
        if len(outerHex.data.materials) > 0:
            outerHex.data.materials.clear()
        outerHex.data.materials.append(mat_black)

    #SHAPE ROTATION
    outerHex.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    outerHex.select_set(True)
    bpy.context.view_layer.objects.active = outerHex
    bpy.ops.object.transform_apply(location = False, rotation=True, scale = False)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')


    global plateobj
    plateobj = outerHex

    global textobj
    textobj = tName
    

def BottomText(obj):

    global total_elevation
    global total_length
 
    name = obj.name
    if "objSize" in obj:
        size = obj["objSize"]
    else:
        return

    thickness = 0.1
    # Place text objects
    text_size = (size / 10)
      
    
    dist =  (size/2 - size/2 * (1-pathScale)/2)
    
    temp_y = size/4
    temp_y = 0
        
    global additionalExtrusion
    additionalExtrusion = obj["AdditionalExtrusion"]

    tName = create_text("t_name", "Name", (0, 0,1.1),text_size)
    
    cx = obj.location.x
    cy = obj.location.y

    transform_MapObject(tName, cx, cy)

    tName.data.extrude = 0.1

    tName.scale.x *= -1
    
    update_text_object("t_name", name)

    convert_text_to_mesh("t_name", obj.name, False)

    tName.name = name + "_Mark"

    bpy.ops.object.select_all(action='DESELECT')

    tName.select_set(True)

    bpy.context.view_layer.objects.active = tName

    mat = bpy.data.materials.get("TRAIL")
    tName.data.materials.clear()
    tName.data.materials.append(mat)

    return tName

    

def convert_text_to_mesh(text_obj_name, mesh_obj_name, merge = True):
    # Get the text and mesh objects
    text_obj = bpy.data.objects.get(text_obj_name)
    mesh_obj = bpy.data.objects.get(mesh_obj_name)
    
    if not text_obj or not mesh_obj:
        print("One or both objects not found")
        return
    
    # Ensure the text object is selected and active
    bpy.ops.object.select_all(action='DESELECT')
    text_obj.select_set(True)
    bpy.context.view_layer.objects.active = text_obj
    
    # Convert text to mesh
    bpy.ops.object.convert(target='MESH')
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Enable auto-merge vertices
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.002)
    #bpy.context.tool_settings.use_mesh_automerge = True
    
    # Switch back to object mode to move it
    bpy.ops.object.mode_set(mode='OBJECT')

    recalculateNormals(text_obj)
    
    # Move the text object up by 1
    text_obj.location.z += 1
    
    # Move the text object down by 1 (merging overlapping vertices)
    text_obj.location.z -= 1
    
    # Disable auto-merge vertices
    bpy.context.tool_settings.use_mesh_automerge = False
    
    if merge == True:
        # Add boolean modifier
        bool_mod = text_obj.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = mesh_obj
        bool_mod.operation = 'INTERSECT'
        bool_mod.solver = 'MANIFOLD'
        
        
        # Apply the boolean modifier
        bpy.ops.object.select_all(action='DESELECT')
        text_obj.select_set(True)
        bpy.context.view_layer.objects.active = text_obj
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
    
    # Move the text object up by 1
    text_obj.location.z += 0.4

def intersect_alltrails_with_existing_box(cutobject):
    #cutobject is the object that will be cut to the Map shapes
    cutobject.scale.z = 1000

    robj2 = None
    
    bpy.ops.object.select_all(action='DESELECT')

    cutobject.select_set(True)
    bpy.context.view_layer.objects.active = cutobject
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    #cube = bpy.data.objects.get(cutobject)
    cube = cutobject
    if not cube:
        print(f"Object named '{cutobject}' not found.")
        return

    # Get cube's bounding box in world coordinates
    cube_bb = [cube.matrix_world @ Vector(corner) for corner in cube.bound_box]
  
    def is_point_inside_cube(point, bb):
        min_corner = Vector((min(v[0] for v in bb),
                             min(v[1] for v in bb),
                             min(v[2] for v in bb)))
        max_corner = Vector((max(v[0] for v in bb),
                             max(v[1] for v in bb),
                             max(v[2] for v in bb)))
        return all(min_corner[i] <= point[i] <= max_corner[i] for i in range(3))
    done = False
    boolObjects = []
    for robj in bpy.data.objects:
        if "_Trail" in robj.name and robj.type in {'CURVE', 'MESH'}:
            if not robj.hide_get():
                # Convert curve to mesh
                if robj.type == 'CURVE':
                    bpy.context.view_layer.objects.active = robj
                    bpy.ops.object.select_all(action='DESELECT')
                    robj2 = robj.copy()
                    robj2.data = robj.data.copy()
                    bpy.context.collection.objects.link(robj2)
                    robj2.select_set(True)
                    bpy.ops.object.convert(target='MESH')
                    trail_mesh = robj2
                    print("-")
                    print(robj2.name)
                else:
                    trail_mesh = robj
                    print("-")
                    print(robj.name)
                    
                
                #robj.hide_set(True)

                if trail_mesh:
                    if trail_mesh.type == "MESH" and len(trail_mesh.data.vertices) > 0:
                        # Check if any vertex is inside the cube
                        for v in trail_mesh.data.vertices:
                            global_coord = trail_mesh.matrix_world @ v.co
                            if is_point_inside_cube(global_coord, cube_bb):
                                # Apply Boolean modifier
                                #print(f"{trail_mesh.name} is inside the Boundaries")
                                if trail_mesh not in boolObjects:
                                    boolObjects.append(trail_mesh)
                                #Set done to True so it doesnt delete the object later
                                done = True
                                #Change Collection
                                continue  # No need to keep checking this object
                            else:
                                pass
                                #print(f"{trail_mesh.name} is NOT inside the Boundaries")
                    else:
                        print("No Vertices for Trail Found")
                        bpy.data.objects.remove(trail_mesh, do_unlink=True)
                
                #bpy.data.objects.remove(robj, do_unlink=True)
                #break
    if done == False:
        #print("No matching trail found. removing cutobject")
        bpy.data.objects.remove(cutobject, do_unlink=True)
    #Pfade kopieren, zusammenfügen und die boolean operation mit allen trails kombiniert ausführen
    if done == True:
        copied_objects = []
        #Copy objects
        for obj in boolObjects:
            print(f"Copy obj {obj.name}")
            obj_copy = obj.copy()
            obj_copy.data = obj.data.copy()
            bpy.context.collection.objects.link(obj_copy)
            copied_objects.append(obj_copy)

        #Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        #Select all copied objects and make one active
        for obj in copied_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copied_objects[0]

        #Join them into a single object
        bpy.ops.object.join()

        merged_object = bpy.context.active_object

        bool_mod = cube.modifiers.new(name=f"Intersect", type='BOOLEAN')
        bool_mod.operation = 'INTERSECT'
        bool_mod.object = merged_object
        bpy.context.view_layer.objects.active = cube
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)

        bpy.data.objects.remove(merged_object, do_unlink=True)
        if robj2 != None:
            bpy.data.objects.remove(robj2, do_unlink=True)

        mat = bpy.data.materials.get("TRAIL")
        cube.data.materials.clear()
        cube.data.materials.append(mat)
    
        writeMetadata(cube,"TRAIL")

def intersect_trail_with_existing_box(cutobject,trail):
    #cutobject is the object that will be cut to the Map shapes
    cutobject.scale.z = 1000

    robj2 = None
    
    bpy.ops.object.select_all(action='DESELECT')

    cutobject.select_set(True)
    bpy.context.view_layer.objects.active = cutobject
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    #cube = bpy.data.objects.get(cutobject)
    cube = cutobject
    if not cube:
        print(f"Object named '{cutobject}' not found.")
        return

    # Get cube's bounding box in world coordinates
    cube_bb = [cube.matrix_world @ Vector(corner) for corner in cube.bound_box]
  
    def is_point_inside_cube(point, bb):
        min_corner = Vector((min(v[0] for v in bb),
                             min(v[1] for v in bb),
                             min(v[2] for v in bb)))
        max_corner = Vector((max(v[0] for v in bb),
                             max(v[1] for v in bb),
                             max(v[2] for v in bb)))
        return all(min_corner[i] <= point[i] <= max_corner[i] for i in range(3))
    done = False
    boolObjects = []
    if trail.type == 'CURVE':
        bpy.context.view_layer.objects.active = trail
        bpy.ops.object.select_all(action='DESELECT')
        robj2 = trail.copy()
        robj2.data = trail.data.copy()
        bpy.context.collection.objects.link(robj2)
        robj2.select_set(True)
        bpy.ops.object.convert(target='MESH')
        trail_mesh = robj2
        print("-")
        print(robj2.name)
        
        #robj.hide_set(True)

    if trail_mesh:
        if trail_mesh.type == "MESH" and len(trail_mesh.data.vertices) > 0:
            # Check if any vertex is inside the cube
            for v in trail_mesh.data.vertices:
                global_coord = trail_mesh.matrix_world @ v.co
                if is_point_inside_cube(global_coord, cube_bb):
                    # Apply Boolean modifier
                    #print(f"{trail_mesh.name} is inside the Boundaries")
                    if trail_mesh not in boolObjects:
                        boolObjects.append(trail_mesh)
                    #Set done to True so it doesnt delete the object later
                    done = True
                    #Change Collection
                    continue  # No need to keep checking this object
                else:
                    pass
                    #print(f"{trail_mesh.name} is NOT inside the Boundaries")
        else:
            print("No Vertices for Trail Found")
            bpy.data.objects.remove(trail_mesh, do_unlink=True)
        

    if done == False:
        #print("No matching trail found. removing cutobject")
        bpy.data.objects.remove(cutobject, do_unlink=True)
    #Pfade kopieren, zusammenfügen und die boolean operation mit allen trails kombiniert ausführen
    if done == True:
        copied_objects = []
        #Copy objects
        for obj in boolObjects:
            print(f"Copy obj {obj.name}")
            obj_copy = obj.copy()
            obj_copy.data = obj.data.copy()
            bpy.context.collection.objects.link(obj_copy)
            copied_objects.append(obj_copy)

        #Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        #Select all copied objects and make one active
        for obj in copied_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copied_objects[0]

        #Join them into a single object
        bpy.ops.object.join()

        merged_object = bpy.context.active_object

        bool_mod = cube.modifiers.new(name=f"Intersect", type='BOOLEAN')
        bool_mod.operation = 'INTERSECT'
        bool_mod.object = merged_object
        bpy.context.view_layer.objects.active = cube
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)

        bpy.data.objects.remove(merged_object, do_unlink=True)
        if robj2 != None:
            bpy.data.objects.remove(robj2, do_unlink=True)

        mat = bpy.data.materials.get("TRAIL")
        cube.data.materials.clear()
        cube.data.materials.append(mat)
    
        writeMetadata(cube,"TRAIL")

def separate_duplicate_xy(coordinates, offset=0.05):
    seen_xy = set()

    for i, point in enumerate(coordinates):
        # Convert tuple to list if needed
        if isinstance(point, tuple):
            point = list(point)
            coordinates[i] = point  # Update the original array with the list version

        x, y, z = point[0], point[1], point[2]
        xy_key = (x, y,z)

        if xy_key in seen_xy:
            point[2] += offset
            point[1] += offset
            #print("Duplicate")
        else:
            seen_xy.add(xy_key)

        return(coordinates)

def single_color_mode(crv, mapName):
   
    map = bpy.data.objects.get(mapName)
    tol = bpy.context.scene.tp3d.tolerance
    print(f"tol: {tol}")
    print (crv.name)
    print(crv.type)

    lowestZonCurve = 1000

    if crv.type == "CURVE":
        
        #Getting the lowest Point of the Curve
        curve = crv.data
        for spline in curve.splines:
            if hasattr(spline, "points") and len(spline.points) > 0:
                for p in spline.points:
                    co_local = Vector((p.co.x, p.co.y, p.co.z))
                    co_world = crv.matrix_world @ co_local
                    z = co_local.z
                    if lowestZonCurve is None or z < lowestZonCurve:
                        lowestZonCurve = z

        print(f"lowestzoncurve: {lowestZonCurve}")


        crv_data = crv.data
        crv_data.dimensions = "2D"
        crv_data.dimensions = "3D"
        crv_data.extrude = 200
        
        # Ensure the text object is selected and active
        bpy.ops.object.select_all(action='DESELECT')
        crv.select_set(True)
        bpy.context.view_layer.objects.active = crv

        bpy.ops.object.mode_set(mode='EDIT')

        # select all points if you want to smooth everything
        bpy.ops.curve.select_all(action='SELECT')

        # run the smooth operator
        
        bpy.ops.curve.smooth()

        # back to Object Mode if you like
        bpy.ops.object.mode_set(mode='OBJECT')

        #Create a duplicate object of the curve that will be slightly thicker
        crv_thick = crv.copy()
        crv_thick.data = crv.data.copy()
        crv_thick.data.bevel_depth = pathThickness/2 + tol  # Set the thickness of the curve
        bpy.context.collection.objects.link(crv_thick)
    elif crv.type == "MESH":
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = crv.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        lowestZonCurve = min((crv.matrix_world @ v.co).z for v in mesh.vertices)

        #crv.scale.z = 100

        crv_thick = crv.copy()
        crv_thick.data = crv.data.copy()
        #crv_thick.data.scale = 1.02
        bpy.context.collection.objects.link(crv_thick)

    bpy.ops.object.convert(target='MESH')

    recalculateNormals(crv)

    # Add boolean modifier
    bool_mod = crv.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.object = map
    bool_mod.operation = 'INTERSECT'
    bool_mod.solver = 'MANIFOLD'


    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    for v in crv.data.vertices:
        pass
        v.co += Vector((0,0,lowestZonCurve - 2))

    recalculateNormals(crv)
    

    #Adding another Intersect Modifier to make the path "Plane" with the Map
    # Add boolean modifier
    bool_mod = crv.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.object = map
    bool_mod.operation = 'INTERSECT'
    bool_mod.solver = 'MANIFOLD'

    recalculateNormals(crv)
    

    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    #doing the same for the duplicate
    bpy.ops.object.select_all(action='DESELECT')
    crv_thick.select_set(True)
    bpy.context.view_layer.objects.active = crv_thick
    bpy.ops.object.convert(target='MESH')


    # Add boolean modifier
    bool_mod = crv_thick.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.object = map
    bool_mod.operation = 'INTERSECT'
    bool_mod.solver = 'MANIFOLD'

    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    crv_thick.scale = (1.002,1.002,1)

    recalculateNormals(crv_thick)

    # Move the text object up by x
    crv_thick.location.z += lowestZonCurve -2

    bpy.ops.object.select_all(action='DESELECT')
    map.select_set(True)
    bpy.context.view_layer.objects.active = map

    bool_mod = map.modifiers.new(name="Boolean", type="BOOLEAN")
    bool_mod.object = crv_thick
    bool_mod.operation = "DIFFERENCE"
    bool_mod.solver = "MANIFOLD"

    #Remove the last material from the MAP as the boolean operation adds it to the list witout using it
    #Without removing it will color the next boolean operation in the color of the trail
    mats = map.data.materials


    bpy.ops.object.modifier_apply(modifier = bool_mod.name)
    bpy.data.objects.remove(crv_thick, do_unlink = True)


# --- OSM FETCHING ---

def fetch_osm_data(bbox, kind = "WATER"):
    south, west, north, east = bbox
    overpass_url = "http://overpass-api.de/api/interpreter"
    if kind == "WATER":
        query = f"""
        [out:json][timeout:25];
        (
            nwr["natural"="water"]({south},{west},{north},{east});
            nwr["water"="river"]({south},{west},{north},{east});
            nwr["water"="lake"]({south},{west},{north},{east});
         );
        out body;
        >;
        out skel qt;
        """
    if kind == "FOREST":
        query = f"""
        [out:json][timeout:25];
        (
            nwr["natural"="wood"]({south},{west},{north},{east});
            nwr["landuse"="forest"]({south},{west},{north},{east});
         );
        out body;
        >;
        out skel qt;
        """
    if kind == "CITY":
        query = f"""
        [out:json][timeout:25];
        (
            nwr["landuse"~"residential|urban|commercial|industrial"]({south},{west},{north},{east});
          );
        out body;
        >;
        out skel qt;
        """
    if kind == "GLACIER":
        query = f"""
        [out:json][timeout:25];
        (
            nwr["natural"="glacier"]({south},{west},{north},{east});
          );
        out body;
        >;
        out skel qt;
        """

    '''
    #way["landuse"~"residential|urban|commercial|industrial"]({south},{west},{north},{east});
    #relation["landuse"~"residential|urban|commercial|industrial"]({south},{west},{north},{east});

    nwr["natural"="water"]({south},{west},{north},{east});
    nwr["water"="river"]({south},{west},{north},{east});
    nwr["water"="lake"]({south},{west},{north},{east});

            
    way["natural"="water"]({south},{west},{north},{east});
        relation["natural"="water"]({south},{west},{north},{east});

        way["water"="river"]({south},{west},{north},{east});
        relation["water"="river"]({south},{west},{north},{east});

        way["waterway"="river"]({south},{west},{north},{east});
        way["waterway"="stream"]({south},{west},{north},{east});

    '''
    #print(query)
    for attempt in range(3):
        try:
            response = requests.post(overpass_url, data={'data': query})

            #check if response is valid
            print("Status:", response.status_code)
            if response.status_code != 200:
                print("Content-Type:", response.headers.get("content-type"))
                print("Response text preview:\n", response.text[:500])

            #print(response.json())
            if response.status_code == 504:
                print(f"Timeout (504), retrying... {attempt+1}/3")
            if response.status_code == 200:
                return response
            
        except Exception as e:
            print("Request failed:", e)
            time.sleep(5)

    return None
 

def extract_multipolygon_bodies(elements, nodes):

    # Helper to get coordinates of a way by its node ids
    def way_coords(way):
        return [ (nodes[nid]['lat'], nodes[nid]['lon'], nodes[nid].get('elevation', 0)) for nid in way['nodes'] if nid in nodes ]

    # Store all multipolygon lakes as lists of outer rings (each ring = list of coords)
    multipolygon_lakes = []

    # Index ways by their id for quick lookup
    way_dict = {el['id']: el for el in elements if el['type'] == 'way'}

    for el in elements:
        if el['type'] in ('relation', 'way'):
            # Collect outer and inner member ways
            outer_ways = []
            inner_ways = []

            for member in el.get('members', []):
                if member['type'] != 'way':
                    continue
                way = way_dict.get(member['ref'])
                if not way:
                    continue

                role = member.get('role', '')
                if role == 'outer':
                    outer_ways.append(way)
                elif role == 'inner':
                    inner_ways.append(way)

            # Stitch ways to closed loops for outer and inner rings
            def stitch_ways(ways):
                loops = []
                # Convert ways to list of coords
                ways_coords = [way_coords(w) for w in ways]

                while ways_coords:
                    current = ways_coords.pop(0)
                    changed = True
                    while changed:
                        changed = False
                        i = 0
                        while i < len(ways_coords):
                            w = ways_coords[i]

                            # Check if current end connects to w start or end
                            if w:
                                if current[-1] == w[0]:
                                    current.extend(w[1:])
                                    ways_coords.pop(i)
                                    changed = True
                                elif current[-1] == w[-1]:
                                    current.extend(reversed(w[:-1]))
                                    ways_coords.pop(i)
                                    changed = True
                                # Also check if current start connects to w end or start
                                elif current[0] == w[-1]:
                                    current = w[:-1] + current
                                    ways_coords.pop(i)
                                    changed = True
                                elif current[0] == w[0]:
                                    current = list(reversed(w[1:])) + current
                                    ways_coords.pop(i)
                                    changed = True
                                else:
                                    i += 1
                    loops.append(current)

                return loops

            outer_loops = stitch_ways(outer_ways)
            inner_loops = stitch_ways(inner_ways)

            # For now, just add outer loops as separate lakes (you could add inner loops for holes)
            for loop in outer_loops:
                multipolygon_lakes.append(loop)

    return multipolygon_lakes


# --- COLOR MESH CREATION ---

def col_create_line_mesh(name, coords):
    mesh = bpy.data.meshes.new(name)
    tobj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(tobj)

    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in coords]
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i + 1]))
    bm.to_mesh(mesh)
    bm.free()
    return tobj


def col_create_face_mesh(name, coords):

    if len(coords) < 3:
        return  # Need at least 3 points for a face
      
    mesh = bpy.data.meshes.new(name)
    tobj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(tobj)

    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in coords]
    try:
        bm.faces.new(verts)
        pass
    except ValueError:
        print(ValueError)
        pass  # face might already exist or be invalid
    bm.to_mesh(mesh)
    bm.free()
    return tobj

def calculate_polygon_area_2d(coords):
    area = 0.0
    
    if len(coords) >= 3:
        
        n = len(coords)
        for i in range(n):
            x0, y0, z0 = coords[i]
            x1, y1, z1 = coords[(i + 1) % n]  # Wrap around to the first point
            area += (x0 * y1) - (x1 * y0)

        return abs(area) * 0.5
    
    return 0.0  # <--- This line was missing, causing the crash

def build_osm_nodes(data):
    nodes = {}
    for element in data['elements']:
        if element['type'] == 'node':
            nodes[element['id']] = element
    return nodes


def coloring_main(map,kind = "WATER"):

    col_KeepManifold = (bpy.context.scene.tp3d.col_KeepManifold)
    if kind == "WATER":
        col_Area = (bpy.context.scene.tp3d.col_wArea)
    if kind == "FOREST":
        col_Area = (bpy.context.scene.tp3d.col_fArea)
    if kind == "CITY":
        col_Area = (bpy.context.scene.tp3d.col_cArea)
    if kind == "GLACIER":
        col_Area = (bpy.context.scene.tp3d.col_glArea)

    col_PaintMap = (bpy.context.scene.tp3d.col_PaintMap)

    global exportformat
    if col_PaintMap == True:
        exportformat = "OBJ"

    bpy.context.preferences.edit.use_global_undo = False

    #print(f"ADDING {kind} MESH")
    #print(f"Map name: {map.name}")

    name = map.name

    lat_step = 2
    lon_step = 2

    waterDeleted = 0
    waterCreated = 0

    if maxLat - minLat < lat_step:
        lat_step = maxLat - minLat
    if maxLon - minLon < lon_step:
        lon_step = maxLon - minLon

    lats = math.ceil((maxLat - minLat) / lat_step)
    lons = math.ceil((maxLon - minLon) / lon_step)

    created_objects = []

    #print(f"lats: {lats}, lons: {lons}")
    if lats * lons < 20:
        for k in range(lats):
            for l in range(lons):
                print(f"loop: {((k) * lons + l + 1)}/{lats * lons}")
                south = minLat + k * lat_step
                north = south + lat_step
                west = minLon + l * lon_step
                east = west + lon_step

                bbox = (south, west, north, east)
                data = []
                #data = fetch_osm_data(bbox, kind)
                try:
                    #pass
                    resp = fetch_osm_data(bbox, kind)
                    if resp.status_code != 200:
                        print("OSM Timeout")
                        return 
                    
                except:
                    show_message_box("Something went wrong with fetching OSM data, Try again maybe or idk")
                    continue

                data = resp.json()
                nodes = build_osm_nodes(data)
                bodies = extract_multipolygon_bodies(data['elements'], nodes)
                #print(f"Nodes: {len(nodes)}, Bodies: {len(bodies)}")

                for i, coords in enumerate(bodies):
                    blender_coords = [convert_to_blender_coordinates(lat, lon, ele, 0) for lat, lon, ele in coords]
                    calcArea = calculate_polygon_area_2d(blender_coords)
                    #print(f"tArea1: {calcArea}")
                    if calcArea > col_Area:
                        tobj = col_create_face_mesh(f"Relation_{i}", blender_coords)
                        created_objects.append(tobj)
                        waterCreated += 1
                    else:
                        waterDeleted += 1

                for i, element in enumerate(data['elements']):
                    #print(i)
                    if element['type'] != 'way':
                        waterDeleted += 1
                        continue

                    coords = []
                    for node_id in element.get('nodes', []):
                        if node_id in nodes:
                            node = nodes[node_id]
                            coord = convert_to_blender_coordinates(
                                node['lat'], node['lon'], 0,0
                            )
                            coords.append(coord)
                    tArea = calculate_polygon_area_2d(coords)
                    #print(f"tArea2: {tArea}")
                    if len(coords) < 2 or tArea < col_Area:
                        waterDeleted += 1
                        continue
                    
                    tags = element.get("tags", {})
                    if coords[0] == coords[-1]:
                        tobj = col_create_face_mesh(f"coloredObject_{i}", coords)
                        created_objects.append(tobj)
                        waterCreated += 1
                    else:
                        tobj = col_create_line_mesh(f"OpenObject_{i}", coords)
                        created_objects.append(tobj)
                        waterCreated += 1
                    
                time.sleep(5)  # Pause to prevent request throttling
    else:
        print("Region too big. Cant Fetch All Water Sources")
    

    # --- Merge all created water meshes into one ---

    print(f"{kind} Objects Created: {waterCreated}, Objects Ignored: {waterDeleted}")

    #print(f"Creating {kind} Objects")
    if created_objects:
        ctx = bpy.context
        bpy.ops.object.select_all(action='DESELECT')
        found = 0
        biggestArea = 0
        for tobj in created_objects:
            
            bm = bmesh.new()
            bm.from_mesh(tobj.data)
            area = sum(f.calc_area() for f in bm.faces)
            bm.free()
            #print(f"Area: {area}")
            if area > biggestArea:
                biggestArea = area
            if area >= col_Area:
                found = 1
                tobj.select_set(True)
                ctx.view_layer.objects.active = tobj
                #print(f"Area: {area}")
            else:
                mesh_data = tobj.data
                bpy.data.objects.remove(tobj, do_unlink=True)
                bpy.data.meshes.remove(mesh_data)
                #print("Removed")

            if found == 0:
                continue

        print(f"Biggest {kind} Found has a Area of: {biggestArea}")

        if biggestArea == 0:
            print("No Water Found on Tile")
            return
        
        bpy.ops.object.join()  # This merges them into the active object

        merged_object = ctx.view_layer.objects.active
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')


        #SETUP FOR MODIFIERS

        bpy.context.view_layer.objects.active = merged_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_region_move()
        bpy.ops.transform.translate(value=(0, 0, 200))#bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        merged_object.location.z -= 1


        #Add Decimate modifier
        #dec_mod = merged_object.modifiers.new(name="Decimate", type="DECIMATE")
        #dec_mod.decimate_type = "UNSUBDIV"
        #dec_mod.iterations = 1

        #bpy.ops.object.modifier_apply(modifier=dec_mod.name)

        recalculateNormals(merged_object)


        # Add boolean modifier
        bool_mod = merged_object.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = map
        bool_mod.operation = 'INTERSECT'
        bool_mod.solver = 'MANIFOLD'


        #appla boolean modifier
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)


        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(merged_object.data)

        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
 

        #Get lowest Vertice
        try:
            min_z = min(v.co.z for v in bm.verts)
        #IF NO VERTICES ARE LEFT, END FUNCTION
        except:
            bpy.ops.object.mode_set(mode='OBJECT')
            return
        
        tol = 0.1

        lowestVert = 100
        for v in bm.verts:
            if abs(v.co.z - min_z) < tol:
                v.select = True
            else:
                v.select = False
                if v.co.z < lowestVert:
                    lowestVert = v.co.z

        bpy.context.tool_settings.mesh_select_mode = (True, False, False)
        bmesh.ops.delete(bm, geom=[elem for elem in bm.verts[:] + bm.edges[:] + bm.faces[:] if elem.select], context='VERTS')
    
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_region_move()
        bpy.ops.transform.translate(value=(0, 0, -1))#bpy.ops.mesh.select_all(action='DESELECT')


        bmesh.update_edit_mesh(merged_object.data)
        bpy.ops.object.mode_set(mode="OBJECT")

        #recalculate normals again after the Boolean operation
        recalculateNormals(merged_object)

        #Disabled for now
        if col_KeepManifold == 0 and 1 == 0:
            delete_non_manifold(merged_object)

        #merged_object.location.z += 0.05
        merged_object.name = name + "_" + kind

        # Wave function removed here

        meshm = merged_object.data
        for i, vert in enumerate(meshm.vertices):
            vert.co.z -= 0.9
        merged_object.location.z = 0

        #bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

          
        if merged_object:
            #print(f"Merged obj: {merged_object}, Kind: {kind}")
            writeMetadata(merged_object,kind)
            mat = bpy.data.materials.get(kind)
            merged_object.data.materials.clear()
            merged_object.data.materials.append(mat)
        
        if col_PaintMap == False:
            export_to_STL(merged_object)

        if col_PaintMap == True:
            color_map_faces_by_terrain(map, merged_object)
            mesh_data = merged_object.data
            bpy.data.objects.remove(merged_object, do_unlink=True)
            bpy.data.meshes.remove(mesh_data)

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':  # make sure it's a 3D Viewport
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'  # switch shading 

    bpy.context.preferences.edit.use_global_undo = True

    if col_PaintMap == False:
        return merged_object
    else:
        return None

def color_map_faces_by_terrain(map_obj, terrain_obj, up_threshold=0.05):
    """
    Loops through every face of map_obj.
    If face is facing upwards, raycasts upwards to see if terrain_obj is above.
    If yes, colors the face with terrain_obj's material.
    
    up_threshold = dot(normal, Z) must be greater than this (0.5 ~ 60° angle limit).
    """
    if map_obj.type != 'MESH' or terrain_obj.type != 'MESH':
        print("Both inputs must be mesh objects.")
        return

    recalculateNormals(map_obj)

    #terrain_obj.location.z += 10

    # Ensure both have mesh data
    map_mesh = map_obj.data
    terrain_mesh = terrain_obj.data

    # Build bmesh for Map
    bm = bmesh.new()
    bm.from_mesh(map_mesh)
    bm.faces.ensure_lookup_table()

    # Build BVH tree for Terrain
    verts = [v.co for v in terrain_mesh.vertices]
    polys = [p.vertices for p in terrain_mesh.polygons]
    bvh = bvhtree.BVHTree.FromPolygons(verts, polys)

    # Get or create a material for terrain color
    if terrain_obj.active_material:
        mat = terrain_obj.active_material
    else:
        mat = bpy.data.materials.new(name="TerrainColor")
        terrain_obj.data.materials.append(mat)

    # Make sure Map has material slots
    if mat.name not in [m.name for m in map_mesh.materials]:
        map_mesh.materials.append(mat)
    mat_index = map_mesh.materials.find(mat.name)

    up = Vector((0, 0, 1))
    colored_count = 0

    for f in bm.faces:
        normal = f.normal.normalized()
        dot = normal.dot(up)
        # Only consider faces facing upward
        if dot > up_threshold:
            center = f.calc_center_median()
            loc, norm, idx, dist = bvh.ray_cast(center, up,1000)

            if loc is not None and dist > 0:
                # Assign terrain material to this face
                f.material_index = mat_index
                colored_count += 1

    bm.to_mesh(map_mesh)
    bm.free()

    print(f"Colored {colored_count} faces on {map_obj.name} based on {terrain_obj.name}")

          

def merge_with_map(mapobject, mergeobject):

    print(mapobject.name)
    print(mergeobject.name)
    print(mergeobject.type)


    if mergeobject.type == "CURVE":
        print("MERGE CURVE WITH MAP")
        
        duplicate  = mapobject.copy()
        duplicate.data = mapobject.data.copy()
        bpy.context.collection.objects.link(duplicate)
        #intersect_alltrails_with_existing_box(duplicate)
        intersect_trail_with_existing_box(duplicate,mergeobject)
        return duplicate
        bpy.ops.object.select_all(action="DESELECT")

    #if the mergeobject is a Text object -> Convert it into a mesh
    if mergeobject.type == "FONT":
        mergeobject.select_set(True)
        bpy.context.view_layer.objects.active = mergeobject
        bpy.ops.object.convert(target='MESH')

    if mergeobject.type == "CURVE":
        mergeobject.select_set(True)
        bpy.context.view_layer.objects.active = mergeobject
        bpy.ops.object.convert(target='MESH')

    bpy.context.view_layer.objects.active = mergeobject
    mergeobject.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move()
    bpy.ops.transform.translate(value=(0, 0, 200))#bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    mergeobject.location.z = -1

    recalculateNormals(mergeobject)
        
    # Add boolean modifier
    bool_mod = mergeobject.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.object = mapobject
    bool_mod.operation = 'INTERSECT'
    bool_mod.solver = 'MANIFOLD'

    #apply boolean modifier
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(mergeobject.data)

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
   
    try:
        min_z = min(v.co.z for v in bm.verts)
    except:
        bpy.ops.object.mode_set(mode='OBJECT')
        return
        
    tol = 0.1
    print(min_z)

    lowestVert = 100
       
    for v in bm.verts:
        if abs(v.co.z - min_z) < tol:
            v.select = True
        else:
            v.select = False
            if v.co.z < lowestVert:
                lowestVert = v.co.z

    print(lowestVert)


    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    #bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.select], context="FACES")
    #bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.delete(bm, geom=[elem for elem in bm.verts[:] + bm.edges[:] + bm.faces[:] if elem.select], context='VERTS')

    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move()
    bpy.ops.transform.translate(value=(0, 0, -1))#bpy.ops.mesh.select_all(action='DESELECT')
    

    bmesh.update_edit_mesh(mergeobject.data)
    bpy.ops.object.mode_set(mode="OBJECT")

    mergeobject.location.z += 0.05

    return mergeobject
    

def midpoint_spherical(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Convert to Cartesian coordinates
    x1 = math.cos(lat1_rad) * math.cos(lon1_rad)
    y1 = math.cos(lat1_rad) * math.sin(lon1_rad)
    z1 = math.sin(lat1_rad)

    x2 = math.cos(lat2_rad) * math.cos(lon2_rad)
    y2 = math.cos(lat2_rad) * math.sin(lon2_rad)
    z2 = math.sin(lat2_rad)

    # Average the vectors
    x = (x1 + x2) / 2
    y = (y1 + y2) / 2
    z = (z1 + z2) / 2

    # Convert back to spherical coordinates
    lon_mid = math.atan2(y, x)
    hyp = math.sqrt(x * x + y * y)
    lat_mid = math.atan2(z, hyp)

    # Convert radians back to degrees
    return math.degrees(lat_mid), math.degrees(lon_mid)

def move_coordinates(lat, lon, distance_km, direction):
    """
    Move a point a given distance (in km) in a cardinal direction (N, S, E, W).
    """
    R = 6371.0  # Earth radius in km
    direction = direction.lower()
    
    # Convert latitude and longitude from degrees to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    if direction == "n":
        lat_rad += distance_km / R
    elif direction == "s":
        lat_rad -= distance_km / R
    elif direction == "e":
        lon_rad += distance_km / (R * math.cos(lat_rad))
    elif direction == "w":
        lon_rad -= distance_km / (R * math.cos(lat_rad))
    else:
        raise ValueError("Direction must be 'n', 's', 'e', or 'w'")
    
    # Convert radians back to degrees
    new_lat = math.degrees(lat_rad)
    new_lon = math.degrees(lon_rad)

    return new_lat, new_lon

def delete_non_manifold(object):

    bpy.ops.object.select_all(action="DESELECT")

    #if the mergeobject is a Text object -> Convert it into a mesh
    object.select_set(True)
    bpy.context.view_layer.objects.active = object

    # Make sure you're in edit mode
    bpy.ops.object.mode_set(mode='EDIT')

    # Get the active mesh
    obj = bpy.context.edit_object
    me = obj.data

    # Access the BMesh representation
    bm = bmesh.from_edit_mesh(me)

    # Ensure the mesh has up-to-date normals and edges
    bm.normal_update()

    # Deselect everything first (optional)
    bpy.ops.mesh.select_all(action='DESELECT')

    # Select non-manifold edges
    bpy.ops.mesh.select_non_manifold()

    # (Optional) Update the mesh to reflect selection in UI
    bmesh.update_edit_mesh(me, loop_triangles=True)

    bpy.ops.mesh.delete(type='VERT')

    bpy.ops.object.mode_set(mode='OBJECT')

def plateInsert(plate,map):

    bpy.ops.object.select_all(action="DESELECT")

    tol = bpy.context.scene.tp3d.tolerance
    dist = bpy.context.scene.tp3d.plateInsertValue

    # Duplicate the map object
    map_copy = map.copy()
    map_copy.data = map.data.copy()
    bpy.context.collection.objects.link(map_copy)
    map_copy.scale *= (size + tol) / size
    
      
    plate.location.z += dist 
 
    map_copy.select_set(True)
    bpy.context.view_layer.objects.active = map_copy
    selectBottomFaces(map_copy)
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')

    bpy.ops.mesh.extrude_region_move()
    bpy.ops.transform.translate(value=(0, 0, 100))#bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    recalculateNormals(map_copy)
    bpy.ops.object.select_all(action="DESELECT")

    plate.select_set(True)
    bpy.context.view_layer.objects.active = plate

    mod = plate.modifiers.new(name="Boolean", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = "MANIFOLD"
    mod.object = map_copy

    bpy.ops.object.modifier_apply(modifier = mod.name)
    
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    bpy.data.objects.remove(map_copy, do_unlink=True)

def selectBottomFaces(obj):

    if obj is None or obj.type != 'MESH':
        raise Exception("Please select a mesh object.")
    
    # Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    mesh = bmesh.from_edit_mesh(obj.data)

    # Recalculate normals
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)

    # Threshold for downward-facing
    threshold = -0.99

    # Object world matrix for local-to-global transformation
    world_matrix = obj.matrix_world
    
    for f in mesh.faces:
        if f.normal.normalized().z < threshold:
            f.select = True  # Optional: visually select in viewport
        else:
            f.select = False

    # Update the mesh
    bmesh.update_edit_mesh(obj.data, loop_triangles=False)

def selectTopFaces(obj):
    if obj is None or obj.type != 'MESH':
        raise Exception("Please select a mesh object.")
    
    # Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    mesh = bmesh.from_edit_mesh(obj.data)

    # Recalculate normals
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)

    # Threshold for downward-facing
    threshold = 0.99

    # Object world matrix for local-to-global transformation
    world_matrix = obj.matrix_world
    
    for f in mesh.faces:
        if f.normal.normalized().z > threshold:
            f.select = True  # Optional: visually select in viewport
        else:
            f.select = False

    # Update the mesh
    bmesh.update_edit_mesh(obj.data, loop_triangles=False)

def set_origin_to_3d_cursor(tobj=None):
    if tobj is None:
        tobj = bpy.context.active_object

    bpy.ops.object.select_all(action='DESELECT')

    bpy.context.view_layer.objects.active = tobj
    tobj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

def recalculateNormals(obj):
    mesh = obj.data

    bm = bmesh.new()
    bm.from_mesh(mesh)

    # recalc normals outward
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

def writeMetadata(obj, type = "MAP"):
    
    try:
        # 尝试访问对象属性，如果对象已被删除会抛出 ReferenceError
        _ = obj.name
    except ReferenceError:
        print(f"writeMetadata: Object {obj} has been removed, skipping metadata write.")
        return
    
    if type == "MAP":
        obj["Object type"] = type
        obj["Addon"] = category
        obj["Version"] = str(AddonVersion[0]) + "," + str(AddonVersion[1])

        obj["Generation Duration"] = str( duration) + " seconds"
        obj["Shape"] = bpy.context.scene.tp3d.shape
        obj["Resolution"] = bpy.context.scene.tp3d.num_subdivisions
        obj["Elevation Scale"] = bpy.context.scene.tp3d.scaleElevation
        obj["objSize"] = bpy.context.scene.tp3d.objSize
        obj["pathThickness"] = round(bpy.context.scene.tp3d.pathThickness,2)
        obj["overwritePathElevation"] = bpy.context.scene.tp3d.overwritePathElevation
        obj["api"] = bpy.context.scene.tp3d.api
        obj["scalemode"] = bpy.context.scene.tp3d.scalemode
        obj["fixedElevationScale"] = bpy.context.scene.tp3d.fixedElevationScale
        obj["minThickness"] = bpy.context.scene.tp3d.minThickness
        obj["xTerrainOffset"] = bpy.context.scene.tp3d.xTerrainOffset
        obj["yTerrainOffset"] = bpy.context.scene.tp3d.yTerrainOffset
        obj["singleColorMode"] = bpy.context.scene.tp3d.singleColorMode
        obj["selfHosted"] = bpy.context.scene.tp3d.selfHosted
        obj["Horizontal Scale"] = round(bpy.context.scene.tp3d.sScaleHor,6)
        obj["Generate Water"] = bpy.context.scene.tp3d.col_wActive
        obj["MinWaterSize"] = bpy.context.scene.tp3d.col_wArea
        obj["Keep Non-Manifold"] = bpy.context.scene.tp3d.col_KeepManifold
        obj["Map Size in Km"] = round(bpy.context.scene.tp3d.sMapInKm,2)
        obj["Dovetail"] = False
        obj["MagnetHoles"] = False
        obj["BottomMark"] = False
        obj["AdditionalExtrusion"] = additionalExtrusion
        obj["lowestZ"] = lowestZ
        obj["highestZ"] = highestZ
        obj["dataset"] = bpy.context.scene.tp3d.dataset
        obj["name"] = bpy.context.scene.tp3d.name
        obj["pathScale"] = bpy.context.scene.tp3d.pathScale
        obj["scaleLon1"] = bpy.context.scene.tp3d.scaleLon1
        obj["scaleLat1"] = bpy.context.scene.tp3d.scaleLat1
        obj["scaleLon2"] = bpy.context.scene.tp3d.scaleLon2
        obj["scaleLat2"] = bpy.context.scene.tp3d.scaleLat2

        obj["shapeRotation"] = bpy.context.scene.tp3d.shapeRotation
        obj["pathVertices"] = bpy.context.scene.tp3d.o_verticesPath
        obj["mapVertices"] = bpy.context.scene.tp3d.o_verticesMap
        obj["mapScale"] = bpy.context.scene.tp3d.o_mapScale
        obj["centerx"] = bpy.context.scene.tp3d.o_centerx
        obj["centery"] = bpy.context.scene.tp3d.o_centery
        obj["sElevationOffset"] = bpy.context.scene.tp3d.sElevationOffset
        obj["sMapInKm"] = bpy.context.scene.tp3d.sMapInKm

        obj["col_wActive"] = bpy.context.scene.tp3d.col_wActive
        obj["col_wArea"] = bpy.context.scene.tp3d.col_wArea
        obj["col_fActive"] = bpy.context.scene.tp3d.col_fActive
        obj["col_fArea"] = bpy.context.scene.tp3d.col_fArea
        obj["col_cActive"] = bpy.context.scene.tp3d.col_cActive
        obj["col_cArea"] = bpy.context.scene.tp3d.col_cArea
        obj["col_glActive"] = bpy.context.scene.tp3d.col_glActive
        obj["col_glArea"] = bpy.context.scene.tp3d.col_glArea
    
    if type =="TRAIL":
        obj["Object type"] = type
        obj["Addon"] = category
        obj["Version"] = str(AddonVersion[0]) + "," + str(AddonVersion[1])

        obj["overwritePathElevation"] = bpy.context.scene.tp3d.overwritePathElevation
    
    if type == "CITY" or type == "WATER" or type == "FOREST":
        obj["Object type"] = type
        obj["Addon"] = category
        obj["Version"] = str(AddonVersion[0]) + "," + str(AddonVersion[1])
        obj["minThickness"] = bpy.context.scene.tp3d.minThickness

    if type == "PLATE":
        obj["Object type"] = type
        obj["Addon"] = category
        obj["Version"] = str(AddonVersion[0]) + "," + str(AddonVersion[1])
        obj["Shape"] = bpy.context.scene.tp3d.shape
        obj["textFont"] = bpy.context.scene.tp3d.textFont
        obj["textSize"] = bpy.context.scene.tp3d.textSize
        obj["overwriteLength"] = bpy.context.scene.tp3d.overwriteLength
        obj["overwriteHeight"] = bpy.context.scene.tp3d.overwriteHeight
        obj["overwriteTime"] = bpy.context.scene.tp3d.overwriteTime
        obj["outerBorderSize"] = bpy.context.scene.tp3d.outerBorderSize
        obj["shapeRotation"] = bpy.context.scene.tp3d.shapeRotation
        obj["name"] = bpy.context.scene.tp3d.name
        obj["plateThickness"] = bpy.context.scene.tp3d.plateThickness
        obj["plateInsertValue"] = bpy.context.scene.tp3d.plateInsertValue
        obj["textAngle"] = bpy.context.scene.tp3d.text_angle_preset
        obj["objSize"] = bpy.context.scene.tp3d.objSize * ((100 + bpy.context.scene.tp3d.outerBorderSize)/100)
        obj["MagnetHoles"] = False
        obj["Dovetail"] = False
    
    if type == "LINES":
        obj["Object type"] = type
        obj["cl_thickness"] = bpy.context.scene.tp3d.cl_thickness
        obj["cl_distance"] = bpy.context.scene.tp3d.cl_distance
        obj["cl_offset"] = bpy.context.scene.tp3d.cl_offset

def show_message_box(message, ic = "ERROR", ti = "ERROR"):
    #toggle_console()
    def draw(self, context):
        self.layout.label(text=message)
    print(message)
    bpy.context.window_manager.popup_menu(draw, title=ti, icon=ic)

def toggle_console():
    try:
        if platform.system() == "Windows":
            bpy.ops.wm.console_toggle()
    except Exception as e:
        print(f"Could not toggle console: {e}")
    
def runGeneration(type):

    #CHECK BLENDER VERSION
    # Minimum required version
    required_version = (4, 5, 0)

    if bpy.app.version < required_version:
        show_message_box(f"TrailPrint3D 2.1 requires Blender {required_version[0]}.{required_version[1]} or higher. (you are using {bpy.app.version_string}).  ")
        return 
        
    start_time = time.time()

    toggle_console()
    
    for i in range(30):
        print(" ")
    print("------------------------------------------------")
    print("SCRIPT STARTED - DO NOT CLOSE THIS WINDOW")
    print("------------------------------------------------")
    print(" ")

    # Path to your GPX file
    global gpx_file_path
    gpx_file_path = bpy.context.scene.tp3d.get('file_path', None)
    global gpx_chain_path
    gpx_chain_path = bpy.context.scene.tp3d.get('chain_path', None)
    global exportPath
    exportPath = bpy.context.scene.tp3d.get('export_path', None)
    global shape
    shape = (bpy.context.scene.tp3d.shape)
    global name
    name = bpy.context.scene.tp3d.get('trailName', "")
    global size
    size =  bpy.context.scene.tp3d.get('objSize', 100)
    global num_subdivisions
    num_subdivisions = bpy.context.scene.tp3d.get('num_subdivisions', 4)
    global scaleElevation
    scaleElevation = bpy.context.scene.tp3d.get('scaleElevation', 10)
    global pathThickness
    pathThickness = bpy.context.scene.tp3d.get('pathThickness', 1.2)
    global scalemode
    scalemode = bpy.context.scene.tp3d.scalemode
    global pathScale
    pathScale = bpy.context.scene.tp3d.get('pathScale', 0.8)
    global scaleLon1
    scaleLon1 = bpy.context.scene.tp3d.get('scaleLon1', 0)
    global scaleLat1
    scaleLat1 = bpy.context.scene.tp3d.get('scaleLat1', 0)
    global scaleLon2
    scaleLon2 = bpy.context.scene.tp3d.get('scaleLon2', 0)
    global scaleLat2
    scaleLat2 = bpy.context.scene.tp3d.get('scaleLat2', 0)
    global shapeRotation
    shapeRotation = bpy.context.scene.tp3d.get('shapeRotation', 0)
    global overwritePathElevation
    overwritePathElevation = bpy.context.scene.tp3d.get('overwritePathElevation', True)
    global api
    api = bpy.context.scene.tp3d.get('api',2)
    global dataset
    #dataset_int = bpy.context.scene.tp3d.get("dataset",1)
    dataset = bpy.context.scene.tp3d.dataset
    global selfHosted
    selfHosted = bpy.context.scene.tp3d.get("selfHosted","")
    global fixedElevationScale
    fixedElevationScale = bpy.context.scene.tp3d.get('fixedElevationScale', False)
    global minThickness
    minThickness = bpy.context.scene.tp3d.get("minThickness",2)
    global xTerrainOffset
    xTerrainOffset = bpy.context.scene.tp3d.get("xTerrainOffset",0)
    global yTerrainOffset
    yTerrainOffset = bpy.context.scene.tp3d.get("yTerrainOffset",0)
    global singleColorMode
    singleColorMode = bpy.context.scene.tp3d.get("singleColorMode",0)
    global disableCache
    disableCache = bpy.context.scene.tp3d.get("disableCache",0)
    global cacheSize
    cacheSize = bpy.context.scene.tp3d.get("ccacheSize",50000)

    #OTHER VARIABLES FOR TEXT BASED SHAPES
    #Add input fields
    global textFont
    textFont = bpy.context.scene.tp3d.get("textFont","")
    global textSize
    textSize = bpy.context.scene.tp3d.get("textSize",10)
    global overwriteLength
    overwriteLength = bpy.context.scene.tp3d.get("overwriteLength","")
    global overwriteHeight
    overwriteHeight = bpy.context.scene.tp3d.get("overwriteHeight","")
    global overwriteTime
    overwriteTime = bpy.context.scene.tp3d.get("overwriteTime","")
    global outerBorderSize
    outerBorderSize = bpy.context.scene.tp3d.get("outerBorderSize",20)
    global text_angle_preset
    text_angle_preset = int(bpy.context.scene.tp3d.text_angle_preset)
    global plateThickness
    plateThickness = bpy.context.scene.tp3d.get("plateThickness",5)

    col_wActive = (bpy.context.scene.tp3d.col_wActive)
    col_fActive = (bpy.context.scene.tp3d.col_fActive)
    col_cActive = (bpy.context.scene.tp3d.col_cActive)
    col_glActive = (bpy.context.scene.tp3d.col_glActive)

    global jMapLat
    jMapLat = bpy.context.scene.tp3d.get("jMapLat",49)
    global jMapLon
    jMapLon = bpy.context.scene.tp3d.get("jMapLon",9)
    global jMapRadius
    jMapRadius = bpy.context.scene.tp3d.get("jMapRadius",50)

    global jMapLat1
    jMapLat1 = bpy.context.scene.tp3d.get("jMapLat1",48)
    global jMapLon1
    jMapLon1 = bpy.context.scene.tp3d.get("jMapLon1",8)
    global jMapLat2
    jMapLat2 = bpy.context.scene.tp3d.get("jMapLat2",49)
    global jMapLon2
    jMapLon2 = bpy.context.scene.tp3d.get("jMapLon2",9)
 

    global buggyDataset
    buggyDataset = 0

    global exportformat
    exportformat = "STL"
    
      
    global opentopoAdress
    opentopoAdress = "https://api.opentopodata.org/v1/"
    if selfHosted != "" and selfHosted != None and api == 1:
        opentopoAdress = selfHosted
        print(f"!!using {opentopoAdress} instead of Opentopodata!!")
        
        
    #CHECK FOR VALID INPUTS
    if type == 0 or type == 4:
        
        if not gpx_file_path or gpx_file_path == "":
            show_message_box("File path is empty! Please select a valid file.")
            toggle_console()
            return
        
        if not os.path.isfile(gpx_file_path):
            show_message_box(f"无效的文件路径: {gpx_file_path}。请选择正确的文件。")
            toggle_console()
            return
        gpx_file_path = bpy.path.abspath(gpx_file_path)

        file_extension = os.path.splitext(gpx_file_path)[1].lower()
        if file_extension != '.gpx' and file_extension != ".igc":
            show_message_box(f"Invalid file format. Please Use a .GPX file")
            toggle_console()
            return

    if type == 1:
        if not gpx_chain_path or gpx_chain_path == "":
            show_message_box("CHAIN path is empty! Please select a valid folder.")
            toggle_console()
            return
        gpx_chain_path = bpy.path.abspath(gpx_chain_path)
    if type == 2:
        #check if inputs are valid
        pass
    if type == 3:
        #check if inputs are valid
        pass
    if exportPath == None:
        show_message_box("“导出路径”为空。请选择保存文件的文件夹。")
        return {'FINISHED'} 
    
    exportPath = bpy.path.abspath(exportPath)

    if not exportPath or exportPath == "":
        show_message_box("Export path is empty! Please select a valid folder.")
        toggle_console()
        return
    if not os.path.isdir(exportPath):
        show_message_box(f"Invalid export Directory: {exportPath}. Please select a valid Directory.")
        toggle_console()
        return
    

    if textFont == "":
        if platform.system() == "Windows":
            textFont = r"C:\Windows\Fonts\msyhbd.ttc"  # 修改这里
        elif platform.system() == "Darwin":
            textFont = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
        else:
            textFont = ""
            #show_message_box(f"Please select a font in the Shape Settings Tab.")
            #toggle_console()
            #return
            
    if name == "":
        if type == 0 or type == 4:
            name_with_ext = os.path.basename(gpx_file_path)
            name = os.path.splitext(name_with_ext)[0]
        if type == 1:
            name_with_ext = os.path.basename(os.path.normpath(gpx_chain_path))
            name = os.path.splitext(name_with_ext)[0]
        if type == 2 or type == 3:
            name = "T"
            
    #GENERATE COLORS IF THEY ARENT THERE YET
    setupColors()
        
    #CONSOLE MESSAGES
    if disableCache == 1:
        print("Cache Disabled (in Advanced Settings)")
    if overwritePathElevation == True and singleColorMode == False:
        print("Overwrite Path Elevation enabled: Path Elevation will be overwritten")
    if type == 0 or type == 1 or type == 4:
        if xTerrainOffset > 0:
            print(f"Map will be moved in X by {xTerrainOffset} (Advanced Settings -> Map -> xTerrainOffset)")
        if yTerrainOffset > 0:
            print(f"Map will be moved in Y by {yTerrainOffset} (Advanced Settings -> Map -> yTerrainOffset)")
     
    if singleColorMode == True:
        #overwritePathElevation = False
        print("Overwrite path Elevation was disabled as its not needed in Single Color mode")

    #STARTSETTINGS
    #Leave edit mode
     
    if bpy.context.object and bpy.context.object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Disable Auto Merge Vertices
    bpy.context.scene.tool_settings.use_mesh_automerge = False
    
    
    coordinates = []
    coordinates2 = []
    tempcoordinates = []
    separate_paths = []
    blender_coords_separate = []
    # Load GPX data
      
    if 1 == 1:
    #try:
        if type == 0:
            
            separate_paths = read_gpx_file()
        if type == 1:
            separate_paths = read_gpx_directory(gpx_chain_path)
        if type == 2 or type == 4:
            nlat,nlon = move_coordinates(jMapLat,jMapLon,jMapRadius,"e")
            separate_paths.append([(nlat,nlon,0,0)])
            nlat,nlon = move_coordinates(jMapLat,jMapLon,jMapRadius,"s")
            separate_paths.append([(nlat,nlon,0,0)])
            nlat,nlon = move_coordinates(jMapLat,jMapLon,jMapRadius,"w")
            separate_paths.append([(nlat,nlon,0,0)])
            nlat,nlon = move_coordinates(jMapLat,jMapLon,jMapRadius,"n")
            separate_paths.append([(nlat,nlon,0,0)])

            print(separate_paths)

            if type == 4:
                tempcoordinates = read_gpx_file()
                coordinates2 = [item for sublist in tempcoordinates for item in sublist]

        if type == 3:
            separate_paths.append([(jMapLat1,jMapLon1,0,0)])
            separate_paths.append([(jMapLat2,jMapLon2,0,0)])
    #except Exception as e:
    else:
        show_message_box(f"Something went Wrong reading the GPX. Type {type}")
        return
    coordinates = [item for sublist in separate_paths for item in sublist]
    #coordinates = separate_paths

    #print(f"separaite paits: {len(separate_paths)}")

            
    #Calculating some Stats about the path
    global total_length
    global total_elevation
    global total_time
    total_length = 0
    total_elevation = 0
    total_time = 0
    if type == 0 or type == 1:
        total_length = calculate_total_length(coordinates)
        total_elevation = calculate_total_elevation(coordinates)
        total_time = calculate_total_time(coordinates)
    
    hours = int(total_time)
    minutes = int((total_time - hours) * 60)
    global time_str
    time_str = f"{hours}h {minutes}m"

    while len(coordinates) < 300 and len(coordinates) > 1 and type != 2:
        i = 0
        while i < len(coordinates) - 1:
            p1 = coordinates[i]
            p2 = coordinates[i + 1]

            # Calculate midpoint (only for x, y, z)
            midpoint = (
                (p1[0] + p2[0]) / 2,
                (p1[1] + p2[1]) / 2,
                (p1[2] + p2[2]) / 2,
                (p1[3])  # Optional: interpolate time too
            )

            # Insert midpoint before p2
            coordinates.insert(i + 1, midpoint)

            # Skip over the new point and the original next point
            i += 2
    
    #CALCULATE biggest distance so you can calculate the value for the smoothing
    min_x = max(point[0] for point in coordinates)
    max_x = max(point[0] for point in coordinates)
    min_y = min(point[1] for point in coordinates)
    max_y = max(point[1] for point in coordinates)
    p1 = convert_to_blender_coordinates(min_x, min_y, 0,"")
    p2 = convert_to_blender_coordinates(max_x,max_y, 0,"")

    distance = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
  
    #CALCULATE SCALE

    global scaleHor

    scalecoords = coordinates
    if scalemode == "COORDINATES" and (type == 0 or type == 1):
        c2 = ((scaleLon1,scaleLat1),(scaleLon2,scaleLat2))
        scalecoords = c2
    
    scaleHor = calculate_scale(size, scalecoords, type)
    print(f"scaleHor: {scaleHor}")

    bpy.context.scene.tp3d["sScaleHor"] = scaleHor
            
    # Convert coordinates to Blender format and create a curve
    #print("Converting Coordinates to Blender format coordinates for X and Y coordsd")
    blender_coords = [convert_to_blender_coordinates(lat, lon, ele,timestamp) for lat, lon, ele, timestamp in coordinates]
    
    if type == 1 or len(separate_paths) > 1:
        blender_coords_separate = [
            [convert_to_blender_coordinates(lat, lon, ele, timestamp) for lat, lon, ele, timestamp in path]
            for path in separate_paths
            ]

    #CALCULATE CENTER
    min_x = min(point[0] for point in blender_coords)
    max_x = max(point[0] for point in blender_coords)
    min_y = min(point[1] for point in blender_coords)
    max_y = max(point[1] for point in blender_coords)
    
    global centerx
    global centery
    centerx = (max_x-min_x)/2 + min_x
    centery = (max_y-min_y)/2 + min_y

    #if type == 2:
    #centerx,centery,z = convert_to_blender_coordinates(jMapLat,jMapLon,0,0)
    
    bpy.context.scene.tp3d["o_centerx"] = centerx
    bpy.context.scene.tp3d["o_centery"] = centery

    #print(f"CenterX: {centerx}, CenterY: {centery}")
    
    #DELETE OBJECTS THAT SIT AT THE CENTER TO PREVENT OVERLAPPING
    target_location_2d = Vector((centerx,centery))
    target_location_2d_offset = Vector((centerx + xTerrainOffset, centery + yTerrainOffset))
    for obs in bpy.data.objects:
        obj_location_2d = Vector((obs.location.x, obs.location.y))
        if (obj_location_2d - target_location_2d).length <= 0.1 or (obj_location_2d - target_location_2d_offset).length <= 0.1:
            bpy.data.objects.remove(obs, do_unlink = True)
            print("deleted overlapping object (Previous generated objects)")

    bpy.ops.object.select_all(action='DESELECT')

    global MapObject
    # CREATE SHAPES
    #print("Creating MapObject")
    if shape == "HEXAGON": #hexagon
        MapObject = create_hexagon(size/2)
    elif shape == "SQUARE": #rectangle
        MapObject = create_rectangle(size,size)
    elif shape == "CIRCLE": # ADDED CIRCLE LOGIC HERE
        MapObject = create_circle(size/2)
    elif shape == "HEXAGON INNER TEXT": #Hexagon with inner text
        MapObject = create_hexagon(size/2)
    elif shape == "HEXAGON OUTER TEXT": #Hexagon with outer text
        MapObject = create_hexagon(size/2)
    elif shape == "HEXAGON FRONT TEXT": #Hexagon with front text
        MapObject = create_hexagon(size/2)
    else:
        MapObject = create_hexagon(size/2)
    
    recalculateNormals(MapObject)
    

    #SHAPE ROTATION
    MapObject.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    MapObject.select_set(True)
    bpy.context.view_layer.objects.active = MapObject
    bpy.ops.object.transform_apply(location = False, rotation=True, scale = False)

    targetx = centerx + xTerrainOffset
    targety = centery + yTerrainOffset
    #print(f"targetx: {targetx}, targety: {targety}")
    if scalemode == "COORDINATES" and type == 1:
        midLat, midLon = midpoint_spherical(scaleLat1,scaleLon1,scaleLat2,scaleLon2)
        targetx, targety, el = convert_to_blender_coordinates(midLat,midLon,0,0)
    #print(f"targetx: {targetx}, targety: {targety}")

    transform_MapObject(MapObject, targetx, targety)

    if type == 4:
        coordinates = coordinates2
    

    #fetch and apply the elevation
    print("------------------------------------------------")
    print("FETCHING ELEVATION DATA FOR THE MAP")
    print("------------------------------------------------")
    
    global autoScale
    bpy.ops.object.transform_apply(location = False, rotation = True, scale = True)
    tileVerts, diff = get_tile_elevation(MapObject)

    if len(tileVerts) < 2000:
            show_message_box(f"Mesh has only {len(tileVerts)} Points. Add more Points to Increase Resolution (e.G Subdivision)", "INFO", "INFO")

    if fixedElevationScale == True:
        if diff > 0:
            autoScale = 10/(diff/1000)
        else:
            autoScale = 10
    else:
        autoScale = scaleHor
    
    bpy.context.scene.tp3d["sAutoScale"] = autoScale
  
    if fixedElevationScale == False:
        if diff == 0:
            pass
            show_message_box("Terrain seems to be really Flat. Might not have Elevation data for that Region. Try Diffrent Api or diffrent Datasets", "INFO", "INFO")
        elif (diff/1000) * autoScale * scaleElevation < 2 :
            show_message_box("Terrain seems to be Flat. Increasing ScaleElevation could helpk", "INFO", "INFO")
    

    #RECALCULATE THE COORDS WITH AUTOSCALE APPLIED
    blender_coords = [convert_to_blender_coordinates(lat, lon, ele,timestamp) for lat, lon, ele, timestamp in coordinates]

    blender_coords = simplify_curve(blender_coords, .12)

    #PREVENT CLIPPING OF IDENTICAL COORDINATES
    blender_coords = separate_duplicate_xy(blender_coords, 0.05)
    

    if (type == 1 or len(separate_paths) > 1) and type != 4:
        blender_coords_separate = [
            [convert_to_blender_coordinates(lat, lon, ele, timestamp) for lat, lon, ele, timestamp in path]
            for path in separate_paths
            ]

    #calculate real Scale
    tdist = 0
    lat1 = coordinates[0][0]
    lon1 = coordinates[0][1]
    lat2 = coordinates[-1][0]
    lon2 = coordinates[-1][1]
    tdist = haversine(lat1,lon1 ,lat2 , lon2)
    #print(f"lat1: {lat1} | lon1: {lon1} ||| lat2: {lat2} | lon2: {lon2}")
    #print(f"tdist:{tdist}")
    mscale = (tdist/size) * 1000000
    #print(f"scale: {mscale}")
    bpy.context.scene.tp3d["o_mapScale"] = f"{mscale:.0f}"

    #------------------------------------------------------------------------------------------------------------------------
    #CREATE THE PATH
    #print("Creating Curve")
    global curveObj
    curveObj = None

    print("YES=")
    print(f"paths: {len(blender_coords_separate)}")
    #if 1 == 1:
    try:
        if (type == 0 and len(blender_coords_separate) <= 1) and type != 2 or type == 4:
            #print(blender_coords)
            print("YES")
            create_curve_from_coordinates(blender_coords)
            curveObj = bpy.context.view_layer.objects.active
        elif (type == 1 or len(blender_coords_separate) > 1) and type != 4 and type != 2:
            for crds in blender_coords_separate:
                create_curve_from_coordinates(crds)
                
                bpy.ops.object.join()
                curveObj = bpy.context.view_layer.objects.active
    except Exception as e:
    #else:
        show_message_box("Bad Response from API while creating the curve. If this happens everytime contact dev")
        return 
    
    bpy.ops.object.select_all(action='DESELECT')


    #APPLY TERRAIN ELEVATION
    mesh = MapObject.data

    global lowestZ
    global highestZ
  
    lowestZ = 1000
    highestZ = 0
    for i, vert in enumerate(mesh.vertices):
        vert.co.z = (tileVerts[i] - elevationOffset)/1000 * scaleElevation * autoScale
        if vert.co.z < lowestZ:
            lowestZ = vert.co.z
        if vert.co.z > highestZ:
            highestZ = vert.co.z
            
    global additionalExtrusion
    additionalExtrusion = lowestZ
    
    bpy.context.scene.tp3d["sAdditionalExtrusion"] = additionalExtrusion
    
    #Raycast the curve points onto the Mesh surface
    if overwritePathElevation == True and curveObj != None:
        RaycastCurveToMesh(curveObj, MapObject)

    # Extrude hexagon to z=0 and scale bottom face
    #bpy.context.scene.tool_settings.transform_pivot_point = 'CURSOR'
    bpy.context.view_layer.objects.active = MapObject
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move()
    bpy.ops.mesh.dissolve_faces() #Merge the bottom faces to a single face
    bpy.ops.transform.translate(value=(0, 0, -1))#bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    global obj
    obj = bpy.context.object 

    # Get the mesh data
    mesh = obj.data
    # Get selected faces
    selected_faces = [face for face in mesh.polygons if face.select]
    
    if selected_faces:
        for face in selected_faces:
            for vert_idx in face.vertices:
                vert = mesh.vertices[vert_idx]
                vert.co.z = additionalExtrusion - minThickness
    else:
        print("No face selected.")

    #CHANGE OBJECT ORIGIN
    bpy.context.view_layer.objects.active = MapObject
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.translate(value=(0, 0, -additionalExtrusion+minThickness))#bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    if curveObj:
        bpy.context.view_layer.objects.active = curveObj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.transform.translate(value=(0, 0, -additionalExtrusion+minThickness))#bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
      
    #sets 3D cursor to origin of tile
    location = obj.location
    bpy.context.scene.cursor.location = location
    if curveObj:
        curveObj.select_set(True)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    
    #Set tile as parent to path
    #curveObj.parent = obj
    #curveObj.matrix_parent_inverse = obj.matrix_world.inverted()

    recalculateNormals(obj)
  
    #ADDITIONAL SHAPE STUFF
    if shape == "HEXAGON INNER TEXT":
        HexagonInnerText()
    if shape == "HEXAGON OUTER TEXT":
        HexagonOuterText()
        obj.location.z += plateThickness
        curveObj.location.z += plateThickness
    if shape == "OCTAGON OUTER TEXT":
        #OctagonOuterText() 
        obj.location.z += plateThickness
        curveObj.location.z += plateThickness
    if shape == "HEXAGON FRONT TEXT":
        HexagonFrontText()
        obj.location.z += plateThickness
        curveObj.location.z += plateThickness
    else:
        pass
        #BottomText()
          
    #PLATESHAPE INSERT
    bpy.ops.object.select_all(action='DESELECT')
    dist = bpy.context.scene.tp3d.plateInsertValue
    if shape == "HEXAGON OUTER TEXT" or shape == "OCTAGON OUTER TEXT" or shape == "HEXAGON FRONT TEXT":
        #plate = bpy.data.objects.get(name + "_Plate")
        #text = bpy.data.objects.get(name + "_Text")
        plate = plateobj
        text = textobj
        if dist > 0:
            plateInsert(plate, obj)
            text.location.z += dist
        print("SHeesh")
        print(xTerrainOffset)
        print(yTerrainOffset)
        transform_MapObject(plate, xTerrainOffset, yTerrainOffset)
        transform_MapObject(text, xTerrainOffset, yTerrainOffset)
        set_origin_to_3d_cursor(plate)
        set_origin_to_3d_cursor(text)
        if shapeRotation != 0:
            text.rotation_euler[2] += shapeRotation * (3.14159265 / 180)
    
    #ADD COLORS TO OBJECTS
    mat = bpy.data.materials.get("BASE")
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    #MATERIAL PREVIEW MODE
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':  # make sure it's a 3D Viewport
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'  # switch shading

    #WATER MESH
    if col_wActive == 1:
        objWater = coloring_main(obj, "WATER")
    if col_fActive == 1:
        objForest = coloring_main(obj, "FOREST")
    if col_cActive == 1:
        objCity = coloring_main(obj, "CITY")
    if col_glActive == 1:
        objGlacier = coloring_main(obj, "GLACIER")
      
    #bpy.ops.object.select_all(action='DESELECT')
    #obj.select_set(True)
    #SINGLE COLOR 

    if singleColorMode == 1:
        single_color_mode(curveObj,obj.name)

    #SCM for Elements Currently Paused because it doesnt work if the Water object is Non-manifold
    #    if col_wActive == 1 and objWater != None:
    #        single_color_mode(objWater,obj.name)
 
    if curveObj:
        mat = bpy.data.materials.get("TRAIL")
        curveObj.data.materials.clear()
        curveObj.data.materials.append(mat)
 
    #ZOOM TO OBJECT
    zoom_camera_to_selected(obj)
    
    bpy.ops.object.select_all(action='DESELECT')
    
    #EXPORT STL
    if curveObj:
        export_to_STL(curveObj,exportformat)
    export_to_STL(obj, exportformat)
    
    if shape in ["HEXAGON INNER TEXT", "HEXAGON OUTER TEXT", "OCTAGON OUTER TEXT", "HEXAGON FRONT TEXT"]:
        tobj = textobj
        mat = bpy.data.materials.get("WHITE")
        if shape == "HEXAGON INNER TEXT":
            mat = bpy.data.materials.get("TRAIL")
        
        if tobj:
            tobj.data.materials.clear()
            tobj.data.materials.append(mat)
            export_to_STL(tobj, exportformat)

    # 如果有底盘对象，写入元数据并导出
    if plateobj:
        try:
            writeMetadata(plateobj, "PLATE")
            export_to_STL(plateobj, exportformat)
        except ReferenceError:
            print("plateobj was removed before metadata could be written.")

    # 为主地图写入元数据
    writeMetadata(obj, "MAP")
    
    # 计算生成耗时
    end_time = time.time()
    global duration
    duration = round(end_time - start_time, 2)
    bpy.context.scene.tp3d.o_time = f"生成耗时: {duration}s"
    
    print("------------------------------------------------")
    print(f"生成完成！总耗时: {duration} 秒")
    print("------------------------------------------------")
    
    toggle_console()
    
    return {'FINISHED'}


# 确保脚本可以直接运行或作为插件加载
if __name__ == "__main__":
    register()