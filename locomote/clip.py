from numpy import array as np_array
from PIL.Image import Image
from moviepy.editor import ImageSequenceClip


async def create_clip_from_images(image_sequence: list[Image]) -> ImageSequenceClip:
    arrays = [np_array(img) for img in image_sequence]
    return ImageSequenceClip(arrays, fps=10)
