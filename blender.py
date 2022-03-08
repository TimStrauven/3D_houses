
import bpy
from math import radians
from mathutils import Euler
import csv
import os
from operator import itemgetter

downloadfolder = f"{os.getcwd()}/"
outputfolder = f"{os.getcwd()}/output/"

def deleteAllObjects():
    """
    Deletes all objects in the current scene
    """
    deleteListObjects = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL',
                         'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'LIGHT_PROBE', 'CAMERA', 'SPEAKER']

    # Select all objects in the scene to be deleted:

    for o in bpy.context.scene.objects:
        for i in deleteListObjects:
            if o.type == i:
                o.select_set(False)
            else:
                o.select_set(True)
    # Deletes all selected objects in the scene:

    bpy.ops.object.delete()

def create_from_csv(myname, my_csv):
    csvfile = open(my_csv)

    inFile = csv.reader(csvfile, delimiter=',', quotechar='"')
    # skip header
    inFile.__next__()

    # Read and sort the vertices coordinates (sort by x and y)
    vertices = sorted([(float(r[0]), float(r[1]), float(r[2])) for r in inFile], key=itemgetter(0, 1))

    # ********* Assuming we have a rectangular grid *************
    # Find the first change in X
    xSize = next(i for i in range(len(vertices)) if vertices[i][0] != vertices[i + 1][0]) + 1
    ySize = len(vertices) // xSize

    # Generate the polygons (four vertices linked in a face)
    polygons = [(i, i - 1, i - 1 + xSize, i + xSize) for i in range(1, len(vertices) - xSize) if i % xSize != 0]

    name = myname
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    # Associate vertices and polygons
    obj.data.from_pydata(vertices, [], polygons)

    # obj.scale = (1, 5, 0.2) #Scale it (if needed)
    # Set smooth shading (if needed)
    for p in obj.data.polygons:
        p.use_smooth = False

    # link obj to scene
    bpy.context.collection.objects.link(obj)


def add_hdri():

    C = bpy.context
    scn = C.scene

    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            space = a.spaces.active
            v3d = space.region_3d
            q = Euler((radians(70), radians(0), radians(290)), 'XYZ').to_quaternion()
            v3d.view_rotation = q
            for s in a.spaces:
                if s.type == 'VIEW_3D':
                    s.clip_end = 10000
                    s.shading.type = 'RENDERED'
                    s.overlay.show_floor = False
                    s.overlay.show_axis_x = False
                    s.overlay.show_axis_y = False
                    s.overlay.show_cursor = False
                    s.lens = 25

    # Get the environment node tree of the current scene
    node_tree = scn.world.node_tree
    tree_nodes = node_tree.nodes

    # Clear all nodes
    tree_nodes.clear()

    # Add Background node
    node_background = tree_nodes.new(type='ShaderNodeBackground')

    # Add Environment Texture node
    node_environment = tree_nodes.new('ShaderNodeTexEnvironment')
    # Load and assign the image to the node property
    hdripath = os.path.join(outputfolder, "HDRI.exr")
    node_environment.image = bpy.data.images.load(hdripath)

    # Add Output node
    node_output = tree_nodes.new(type='ShaderNodeOutputWorld')

    # Link all nodes
    links = node_tree.links
    link = links.new(node_environment.outputs["Color"], node_background.inputs["Color"])
    link = links.new(node_background.outputs["Background"], node_output.inputs["Surface"])
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 5


def set_material_to(objectname, color):
    objref = bpy.data.objects[objectname]
    mymat = bpy.data.materials.new(f"mat_{objectname}")
    mymat.diffuse_color = color
    objref.data.materials.append(mymat)

def set_texture_material_to(objectname, texture, specular):
    objref = bpy.data.objects[objectname]
    mymat = bpy.data.materials.new(f"mat_{objectname}")
    mymat.use_nodes = True
    bsdf = mymat.node_tree.nodes["Principled BSDF"]
    texImage = mymat.node_tree.nodes.new('ShaderNodeTexImage')
    texImage.image = bpy.data.images.load(texture)
    mymat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
    myvector = mymat.node_tree.nodes.new('ShaderNodeTexCoord')
    reflect = mymat.node_tree.nodes.new('ShaderNodeTexCoord')
    mymat.node_tree.links.new(texImage.inputs['Vector'], myvector.outputs['Generated'])
    mymat.node_tree.links.new(bsdf.inputs['Normal'], reflect.outputs['Reflection'])
    mymat.node_tree.nodes["Image Texture"].extension = 'EXTEND'
    mymat.node_tree.nodes["Principled BSDF"].inputs[7].default_value = 0.75
    mymat.node_tree.nodes["Principled BSDF"].inputs[5].default_value = specular

    mymat.shadow_method = 'NONE'

    objref.data.materials.append(mymat)

def hide_object_by_name(objectname):
    objref = bpy.data.objects[objectname]
    objref.hide_set(True)

def select_all_obj():
    # Select all objects in the scene to be deleted:
    selectListObjects = ['MESH', 'CURVE', 'SURFACE', 'META', 'POINTCLOUD', 'VOLUME', 'LATTICE', 'EMPTY']
    for o in bpy.context.scene.objects:
        for i in selectListObjects:
            if o.type == i:
                o.select_set(False)
            else:
                o.select_set(True)

def select_none_obj():
    # Select all objects in the scene to be deleted:
    selectListObjects = ['MESH', 'CURVE', 'SURFACE', 'META', 'POINTCLOUD', 'VOLUME', 'LATTICE', 'EMPTY']
    for o in bpy.context.scene.objects:
        for i in selectListObjects:
            if o.type == i:
                o.select_set(True)
            else:
                o.select_set(False)

def select_by_name(name):
    select_none_obj()
    bpy.data.objects[name].select_set(True)

def centerscreen():
    select_all_obj()
    for screen in bpy.data.screens:
        for area in (a for a in screen.areas if a.type == 'VIEW_3D'):
            region = next((region for region in area.regions if region.type == 'WINDOW'), None)
            if region is not None:
                override = {'area': area, 'region': region}  # !!the first important bit!!
                bpy.ops.view3d.view_selected(override)


blue = (0.0531328, 0.0592434, 0.8, 1)
red = (0.8, 0.105578, 0.0794387, 1)

deleteAllObjects()
add_hdri()
create_from_csv("2_Surroundings", os.path.join(outputfolder, "final.csv"))
create_from_csv("3_Property", os.path.join(outputfolder, "final_plot.csv"))
create_from_csv("4_Building", os.path.join(outputfolder, "final_building.csv"))
centerscreen()
create_from_csv("1_groundplane", os.path.join(outputfolder, "plane.csv"))
create_from_csv("1_groundplane2", os.path.join(outputfolder, "plane2.csv"))
create_from_csv("1_groundplane3", os.path.join(outputfolder, "plane3.csv"))
select_none_obj()
set_material_to('3_Property', blue)
set_material_to('4_Building', red)
hide_object_by_name("3_Property")
hide_object_by_name("4_Building")
hide_object_by_name("1_groundplane3")
set_texture_material_to("2_Surroundings", os.path.join(outputfolder, "texture.jpeg"), 0.14)
set_texture_material_to("1_groundplane", os.path.join(outputfolder, "texture_plane_10000.jpeg"), 0)
set_texture_material_to("1_groundplane2", os.path.join(outputfolder, "texture_plane_2000.jpeg"), 0.05)
set_texture_material_to("1_groundplane3", os.path.join(outputfolder, "texture_plane_150000.jpeg"), 0)
