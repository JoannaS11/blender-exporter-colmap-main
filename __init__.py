bl_info = {
    "name": "Scene exporter for colmap",
    "description": "Generates a dataset for colmap by exporting blender camera poses and rendering scene.",
    "author": "Ohayoyogi",
    "version": (0,0,1),
    "blender": (3,6,0),
    "location": "File/Export",
    "warning": "",
    "wiki_url": "https://github.com/ohayoyogi/blender-exporter-colmap",
    "tracker_url": "https://github.com/ohayoyogi/blender-exporter-colmap/issues",
    "category": "Import-Export"
}

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

import mathutils
from pathlib import Path
from mathutils import Vector, Matrix
from math import radians


class BlenderExporterForColmap(bpy.types.Operator, ExportHelper):
    bl_idname = "object.colmap_dataset_generator"
    bl_label = "Export as colmap dataset"
    bl_options = {"PRESET"}
    
    filename_ext = "."
    
    directory: StringProperty()
    
    filter_folder = True

    def export_dataset(self, context, dirpath: Path):
        scene = context.scene
        cameras = [ i for i in scene.objects if i.type == "CAMERA"]
        mesh = bpy.data.meshes["Cylinder"]
        obj = bpy.data.objects['Cylinder']
        #mesh2 = bpy.types.MeshPolygon.vertices
        #print(mesh2)

        scale = scene.render.resolution_percentage / 100.0

        output_dir = dirpath
        cameras_file = output_dir / 'cameras.txt'
        images_file = output_dir / 'images.txt'
        images_dir = output_dir / 'images'
        points_file = output_dir / 'points3D.txt'
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(cameras_file, 'w') as f_cam, open(images_file, 'w') as f_img, open(points_file, 'w') as f_points:
            f_cam.write(f'# Camera list generated by blender-exporter-colmap\n')
            f_img.write(f'# Image list generated by blender-exporter-colmap\n')
            f_points.write(f'# 3D point list generated by blender-exporter-colmap\n')
            f_points.write(f'# POINTS-ID X Y Z R G B NX NY NZ\n')

            obj = bpy.data.objects.get("Cylinder")

            scene = bpy.context.scene
            camera = scene.camera
            frame_start = scene.frame_start
            frame_end = scene.frame_end

            x=0
            idx = 1
            # animation assumed
            for frame in range(frame_start, frame_end + 1):
                # set camera of current frame to the current camera
                filename = frame
                scene.frame_set(frame)
                camera = scene.camera

                # extract intrinsic parameter of the camera
                focal_length = camera.data.lens
                width = scene.render.resolution_x
                height = scene.render.resolution_y
                f = focal_length * (width / camera.data.sensor_width)
                params = [f, width // 2, height // 2]

                # only one camera assumed, so the intrinsic parameters only needs to be saved once.
                if frame == 1:
                    f_cam.write(f'{frame+x} SIMPLE_PINHOLE {width} {height} {" ".join(map(str,params))}\n')

                rotation_mode_bk = camera.rotation_mode
                
                # coordinate system needs to be changed from the blender one to the colmap one
                camera.rotation_mode = "QUATERNION"
                loc, rot, scale = bpy.context.scene.camera.matrix_world.decompose()
                rot_matrix = mathutils.Quaternion((rot.x, rot.w, rot.z, -rot.y))

                # position needs to be transformed in the new coordinate system
                loc = rot_matrix.to_matrix() @ -loc

                # save current camera extrinsics and rendered image name
                f_img.write(f'{idx} {rot.x} {rot.w} {rot.z} {-rot.y} {loc.x} {loc.y} {loc.z} {1} frame_{filename}.jpg\n')
                f_img.write(f'\n')

                # render current view and save image
                bpy.ops.render.render()
                bpy.data.images['Render Result'].save_render(str(images_dir / f'frame_{filename}.jpg'))
                idx += 1
        
        yield 100.0

    def execute(self, context):
        dirpath = Path(self.directory)
        if not dirpath.is_dir():
            return { "WARNING", "Illegal directory was passed: " + self.directory }

        context.window_manager.progress_begin(0, 100)
        for progress in self.export_dataset(context, dirpath):
            context.window_manager.progress_update(progress)
        context.window_manager.progress_end()

        return {"FINISHED"}

def _blender_export_operator_function(topbar_file_import, context):
    topbar_file_import.layout.operator(
        BlenderExporterForColmap.bl_idname, text="Colmap dataset"
    )

def register():
    bpy.utils.register_class(BlenderExporterForColmap)
    bpy.types.TOPBAR_MT_file_export.append(_blender_export_operator_function)

def unregister():
    bpy.utils.unregister_class(BlenderExporterForColmap)

if __name__ == "__main__":
    register()