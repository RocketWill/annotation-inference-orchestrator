'''
Date: 2021-12-20 10:31:07
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2021-12-29 00:46:33
'''
import os
import tempfile
import shutil
import zipfile
import io
import ntpath
import itertools
import struct
from abc import ABC, abstractmethod
from contextlib import closing

import av
import numpy as np
from PIL import Image, ImageFile
import open3d as o3d

from utils import rotate_image
from mime_types import mimetypes
from models import DimensionType

def get_mime(name):
    for type_name, type_def in MEDIA_TYPES.items():
        if type_def['has_mime_type'](name):
            return type_name

    return 'unknown'

def create_tmp_dir():
    return tempfile.mkdtemp(prefix='cvat-', suffix='.data')

def delete_tmp_dir(tmp_dir):
    if tmp_dir:
        shutil.rmtree(tmp_dir)

def files_to_ignore(directory):
    ignore_files = ('__MSOSX', '._.DS_Store', '__MACOSX', '.DS_Store')
    if not any(ignore_file in directory for ignore_file in ignore_files):
        return True
    return False

class IMediaReader(ABC):
    def __init__(self, source_path, step, start, stop, dimension):
        self._source_path = sorted(source_path, key=lambda kv: int(ntpath.basename(kv).rsplit(".", 1)[0]))
        self._step = step
        self._start = start
        self._stop = stop
        self._dimension = dimension

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def get_preview(self):
        pass

    @abstractmethod
    def get_progress(self, pos):
        pass

    @staticmethod
    def _get_preview(obj):
        PREVIEW_SIZE = (256, 256)
        if isinstance(obj, io.IOBase):
            preview = Image.open(obj)
        else:
            preview = obj
        preview.thumbnail(PREVIEW_SIZE)

        return preview.convert('RGB')

    @abstractmethod
    def get_image_size(self, i):
        pass

    def __len__(self):
        return len(self.frame_range)

    @property
    def frame_range(self):
        return range(self._start, self._stop, self._step)

class ImageListReader(IMediaReader):
    def __init__(self, source_path, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        if not source_path:
            raise Exception('No image found')

        if stop is None:
            stop = len(source_path)
        else:
            stop = min(len(source_path), stop + 1)
        step = max(step, 1)
        assert stop > start

        super().__init__(
            source_path=source_path,
            step=step,
            start=start,
            stop=stop,
            dimension=dimension
        )

    def __iter__(self):
        for i in range(self._start, self._stop, self._step):
            yield (self.get_image(i), self.get_path(i), i)

    def filter(self, callback):
        source_path = list(filter(callback, self._source_path))
        ImageListReader.__init__(
            self,
            source_path,
            step=self._step,
            start=self._start,
            stop=self._stop,
            dimension=self._dimension
        )

    def get_path(self, i):
        return self._source_path[i]

    def get_image(self, i):
        return self._source_path[i]

    def get_progress(self, pos):
        return (pos - self._start + 1) / (self._stop - self._start)

    def get_preview(self):
        if self._dimension == DimensionType.DIM_3D:
            fp = open(os.path.join(os.path.dirname(__file__), 'assets/3d_preview.jpeg'), "rb")
        else:
            fp = open(self._source_path[0], "rb")
        return self._get_preview(fp)

    def get_image_size(self, i):
        if self._dimension == DimensionType.DIM_3D:
            with open(self.get_path(i), 'rb') as f:
                properties = ValidateDimension.get_pcd_properties(f)
                return int(properties["WIDTH"]),  int(properties["HEIGHT"])
        img = Image.open(self._source_path[i])
        return img.width, img.height

    def reconcile(self, source_files, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        # FIXME
        ImageListReader.__init__(self,
            source_path=source_files,
            step=step,
            start=start,
            stop=stop
        )
        self._dimension = dimension

    @property
    def absolute_source_paths(self):
        return [self.get_path(idx) for idx, _ in enumerate(self._source_path)]

class DirectoryReader(ImageListReader):
    def __init__(self, source_path, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        image_paths = []
        for source in source_path:
            for root, _, files in os.walk(source):
                paths = [os.path.join(root, f) for f in files]
                paths = filter(lambda x: get_mime(x) == 'image', paths)
                image_paths.extend(paths)
        super().__init__(
            source_path=image_paths,
            step=step,
            start=start,
            stop=stop,
            dimension=dimension,
        )

class ZipReader(ImageListReader):
    def __init__(self, source_path, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        self._zip_source = zipfile.ZipFile(source_path[0], mode='r')
        self.extract_dir = source_path[1] if len(source_path) > 1 else None
        file_list = [f for f in self._zip_source.namelist() if files_to_ignore(f) and get_mime(f) == 'image']
        # file_list = sorted(file_list, key=lambda kv: int(kv.rsplit(".", 1)[0]))
        super().__init__(file_list, step=step, start=start, stop=stop, dimension=dimension)

    def __del__(self):
        self._zip_source.close()

    def get_preview(self):
        if self._dimension == DimensionType.DIM_3D:
            # TODO
            fp = open(os.path.join(os.path.dirname(__file__), 'assets/3d_preview.jpeg'), "rb")
            return self._get_preview(fp)
        io_image = io.BytesIO(self._zip_source.read(self._source_path[0]))
        return self._get_preview(io_image)

    def get_image_size(self, i):
        if self._dimension == DimensionType.DIM_3D:
            with open(self.get_path(i), 'rb') as f:
                properties = ValidateDimension.get_pcd_properties(f)
                return int(properties["WIDTH"]),  int(properties["HEIGHT"])
        img = Image.open(io.BytesIO(self._zip_source.read(self._source_path[i])))
        return img.width, img.height

    def get_image(self, i):
        if self._dimension == DimensionType.DIM_3D:
            return self.get_path(i)
        return io.BytesIO(self._zip_source.read(self._source_path[i]))

    def get_zip_filename(self):
        return self._zip_source.filename

    def get_path(self, i):
        if self._zip_source.filename:
            return os.path.join(os.path.dirname(self._zip_source.filename), self._source_path[i]) \
                if not self.extract_dir else os.path.join(self.extract_dir, self._source_path[i])
        else: # necessary for mime_type definition
            return self._source_path[i]

    def reconcile(self, source_files, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        super().reconcile(
            source_files=source_files,
            step=step,
            start=start,
            stop=stop,
            dimension=dimension,
        )

    def extract(self):
        self._zip_source.extractall(self.extract_dir if self.extract_dir else os.path.dirname(self._zip_source.filename))
        if not self.extract_dir:
            os.remove(self._zip_source.filename)

class VideoReader(IMediaReader):
    """
    (<av.VideoFrame #31, pts=15872 yuv420p 2020x1136 at 0x7fd520f5c528>, '/app/temp/data/1/original/0.mp4', 15872)
    """
    def __init__(self, source_path, step=1, start=0, stop=None, dimension=DimensionType.DIM_2D):
        super().__init__(
            source_path=source_path,
            step=step,
            start=start,
            stop=stop + 1 if stop is not None else stop,
            dimension=dimension,
        )

    def _has_frame(self, i):
        if i >= self._start:
            if (i - self._start) % self._step == 0:
                if self._stop is None or i < self._stop:
                    return True

        return False

    def _decode(self, container):
        frame_num = 0
        for packet in container.demux():
            if packet.stream.type == 'video':
                for image in packet.decode():
                    frame_num += 1
                    if self._has_frame(frame_num - 1):
                        if packet.stream.metadata.get('rotate'):
                            old_image = image
                            image = av.VideoFrame().from_ndarray(
                                rotate_image(
                                    image.to_ndarray(format='bgr24'),
                                    360 - int(container.streams.video[0].metadata.get('rotate'))
                                ),
                                format ='bgr24'
                            )
                            image.pts = old_image.pts
                        yield (image, self._source_path[0], image.pts)

    def __iter__(self):
        container = self._get_av_container()
        source_video_stream = container.streams.video[0]
        source_video_stream.thread_type = 'AUTO'

        return self._decode(container)

    def get_progress(self, pos):
        duration = self._get_duration()
        return pos / duration if duration else None

    def _get_av_container(self):
        if isinstance(self._source_path[0], io.BytesIO):
            self._source_path[0].seek(0) # required for re-reading
        return av.open(self._source_path[0])

    def _get_duration(self):
        container = self._get_av_container()
        stream = container.streams.video[0]
        duration = None
        if stream.duration:
            duration = stream.duration
        else:
            # may have a DURATION in format like "01:16:45.935000000"
            duration_str = stream.metadata.get("DURATION", None)
            tb_denominator = stream.time_base.denominator
            if duration_str and tb_denominator:
                _hour, _min, _sec = duration_str.split(':')
                duration_sec = 60*60*float(_hour) + 60*float(_min) + float(_sec)
                duration = duration_sec * tb_denominator
        return duration

    def get_preview(self):
        container = self._get_av_container()
        stream = container.streams.video[0]
        preview = next(container.decode(stream))
        return self._get_preview(preview.to_image() if not stream.metadata.get('rotate') \
            else av.VideoFrame().from_ndarray(
                rotate_image(
                    preview.to_ndarray(format='bgr24'),
                    360 - int(container.streams.video[0].metadata.get('rotate'))
                ),
                format ='bgr24'
            ).to_image()
        )

    def get_image_size(self, i):
        image = (next(iter(self)))[0]
        return image.width, image.height

class FragmentMediaReader:
    def __init__(self, chunk_number, chunk_size, start, stop, step=1):
        self._start = start
        self._stop = stop + 1 # up to the last inclusive
        self._step = step
        self._chunk_number = chunk_number
        self._chunk_size = chunk_size
        self._start_chunk_frame_number = \
            self._start + self._chunk_number * self._chunk_size * self._step
        self._end_chunk_frame_number = min(self._start_chunk_frame_number \
            + (self._chunk_size - 1) * self._step + 1, self._stop)
        self._frame_range = self._get_frame_range()

    @property
    def frame_range(self):
        return self._frame_range

    def _get_frame_range(self):
        frame_range = []
        for idx in range(self._start, self._stop, self._step):
            if idx < self._start_chunk_frame_number:
                continue
            elif idx < self._end_chunk_frame_number and \
                    not ((idx - self._start_chunk_frame_number) % self._step):
                frame_range.append(idx)
            elif (idx - self._start_chunk_frame_number) % self._step:
                continue
            else:
                break
        return frame_range

class ImageDatasetManifestReader(FragmentMediaReader):
    def __init__(self, manifest_path, **kwargs):
        super().__init__(**kwargs)
        self._manifest = ImageManifestManager(manifest_path)
        self._manifest.init_index()

    def __iter__(self):
        for idx in self._frame_range:
            yield self._manifest[idx]

class VideoDatasetManifestReader(FragmentMediaReader):
    def __init__(self, manifest_path, **kwargs):
        self.source_path = kwargs.pop('source_path')
        super().__init__(**kwargs)
        self._manifest = VideoManifestManager(manifest_path)
        self._manifest.init_index()

    def _get_nearest_left_key_frame(self):
        if self._start_chunk_frame_number >= \
                self._manifest[len(self._manifest) - 1].get('number'):
            left_border = len(self._manifest) - 1
        else:
            left_border = 0
            delta = len(self._manifest)
            while delta:
                step = delta // 2
                cur_position = left_border + step
                if self._manifest[cur_position].get('number') < self._start_chunk_frame_number:
                    cur_position += 1
                    left_border = cur_position
                    delta -= step + 1
                else:
                    delta = step
            if self._manifest[cur_position].get('number') > self._start_chunk_frame_number:
                left_border -= 1
        frame_number = self._manifest[left_border].get('number')
        timestamp = self._manifest[left_border].get('pts')
        return frame_number, timestamp

    def __iter__(self):
        start_decode_frame_number, start_decode_timestamp = self._get_nearest_left_key_frame()
        with closing(av.open(self.source_path, mode='r')) as container:
            video_stream = next(stream for stream in container.streams if stream.type == 'video')
            video_stream.thread_type = 'AUTO'

            container.seek(offset=start_decode_timestamp, stream=video_stream)

            frame_number = start_decode_frame_number - 1
            for packet in container.demux(video_stream):
                for frame in packet.decode():
                    frame_number += 1
                    if frame_number in self._frame_range:
                        if video_stream.metadata.get('rotate'):
                            frame = av.VideoFrame().from_ndarray(
                                rotate_image(
                                    frame.to_ndarray(format='bgr24'),
                                    360 - int(container.streams.video[0].metadata.get('rotate'))
                                ),
                                format ='bgr24'
                            )
                        yield frame
                    elif frame_number < self._frame_range[-1]:
                        continue
                    else:
                        return

class ValidateDimension:

    def __init__(self, path=None):
        self.dimension = DimensionType.DIM_2D
        self.path = path
        self.related_files = {}
        self.image_files = {}
        self.converted_files = []

    @staticmethod
    def get_pcd_properties(fp, verify_version=False):
        kv = {}
        pcd_version = ["0.7", "0.6", "0.5", "0.4", "0.3", "0.2", "0.1",
                       ".7", ".6", ".5", ".4", ".3", ".2", ".1"]
        try:
            for line in fp:
                line = line.decode("utf-8")
                if line.startswith("#"):
                    continue
                k, v = line.split(" ", maxsplit=1)
                kv[k] = v.strip()
                if "DATA" in line:
                    break
            if verify_version:
                if "VERSION" in kv and kv["VERSION"] in pcd_version:
                    return True
                return None
            return kv
        except AttributeError:
            return None

    @staticmethod
    def convert_bin_to_pcd(path, delete_source=True):
        list_pcd = []
        with open(path, "rb") as f:
            size_float = 4
            byte = f.read(size_float * 4)
            while byte:
                x, y, z, _ = struct.unpack("ffff", byte)
                list_pcd.append([x, y, z])
                byte = f.read(size_float * 4)
        np_pcd = np.asarray(list_pcd)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np_pcd)
        pcd_filename = path.replace(".bin", ".pcd")
        o3d.io.write_point_cloud(pcd_filename, pcd)
        if delete_source:
            os.remove(path)
        return pcd_filename

    def set_path(self, path):
        self.path = path

    def bin_operation(self, file_path, actual_path):
        pcd_path = ValidateDimension.convert_bin_to_pcd(file_path)
        self.converted_files.append(pcd_path)
        return pcd_path.split(actual_path)[-1][1:]

    @staticmethod
    def pcd_operation(file_path, actual_path):
        with open(file_path, "rb") as file:
            is_pcd = ValidateDimension.get_pcd_properties(file, verify_version=True)
        return file_path.split(actual_path)[-1][1:] if is_pcd else file_path

    def process_files(self, root, actual_path, files):
        pcd_files = {}

        for file in files:
            file_name, file_extension = os.path.splitext(file)
            file_path = os.path.abspath(os.path.join(root, file))

            if file_extension == ".bin":
                path = self.bin_operation(file_path, actual_path)
                pcd_files[file_name] = path
                self.related_files[path] = []

            elif file_extension == ".pcd":
                path = ValidateDimension.pcd_operation(file_path, actual_path)
                if path == file_path:
                    self.image_files[file_name] = file_path
                else:
                    pcd_files[file_name] = path
                    self.related_files[path] = []
            else:
                if _is_image(file_path):
                    self.image_files[file_name] = file_path
        return pcd_files

    def validate(self):
        """
            Validate the directory structure for kitty and point cloud format.
        """
        if not self.path:
            return
        actual_path = self.path
        for root, _, files in os.walk(actual_path):
            if not files_to_ignore(root):
                continue

            self.process_files(root, actual_path, files)

        if len(self.related_files.keys()):
            self.dimension = DimensionType.DIM_3D

def _is_archive(path):
    mime = mimetypes.guess_type(path)
    mime_type = mime[0]
    encoding = mime[1]
    supportedArchives = ['application/x-rar-compressed',
        'application/x-tar', 'application/x-7z-compressed', 'application/x-cpio',
        'gzip', 'bzip2']
    return mime_type in supportedArchives or encoding in supportedArchives

def _is_video(path):
    mime = mimetypes.guess_type(path)
    return mime[0] is not None and mime[0].startswith('video')

def _is_image(path):
    mime = mimetypes.guess_type(path)
    # Exclude vector graphic images because Pillow cannot work with them
    return mime[0] is not None and mime[0].startswith('image') and \
        not mime[0].startswith('image/svg')

def _is_dir(path):
    return os.path.isdir(path)

def _is_pdf(path):
    mime = mimetypes.guess_type(path)
    return mime[0] == 'application/pdf'

def _is_zip(path):
    mime = mimetypes.guess_type(path)
    mime_type = mime[0]
    encoding = mime[1]
    supportedArchives = ['application/zip']
    return mime_type in supportedArchives or encoding in supportedArchives

MEDIA_TYPES = {
    'image': {
        'has_mime_type': _is_image,
        'extractor': ImageListReader,
        'mode': 'annotation',
        'unique': False,
    },
    'video': {
        'has_mime_type': _is_video,
        'extractor': VideoReader,
        'mode': 'interpolation',
        'unique': True,
    },
    # 'archive': {
    #     'has_mime_type': _is_archive,
    #     'extractor': ArchiveReader,
    #     'mode': 'annotation',
    #     'unique': True,
    # },
    # 'directory': {
    #     'has_mime_type': _is_dir,
    #     'extractor': DirectoryReader,
    #     'mode': 'annotation',
    #     'unique': False,
    # },
    # 'pdf': {
    #     'has_mime_type': _is_pdf,
    #     'extractor': PdfReader,
    #     'mode': 'annotation',
    #     'unique': True,
    # },
    'zip': {
        'has_mime_type': _is_zip,
        'extractor': ZipReader,
        'mode': 'annotation',
        'unique': True,
    }
}

# if __name__ == "__main__":
#     import glob
#     vs = glob.glob("/app/temp/data/1/original/*.mp4")
#     print(vs)
#     vr = VideoReader(source_path=vs, stop=None)
#     print(dir(vr))
#     # print(vr.get_image_size(1))
#     index = 0
#     for i in vr:
#         index+=1
#         print(i)
#     print(index)