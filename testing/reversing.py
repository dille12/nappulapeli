import torch
from diffusers import StableDiffusionImg2ImgPipeline
from diffusers import LMSDiscreteScheduler
from torch import autocast


from PIL import Image
import numpy
import cv2
# Device setup
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load the inpainting model (smaller variant recommended for speed)
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
)

pipe.safety_checker = lambda images, **kwargs: (images, [False] * len(images))


pipe = pipe.to(device)
pipe.enable_attention_slicing()  # saves VRAM

lms = LMSDiscreteScheduler(beta_start=0.00085, beta_end=0.012, beta_schedule="scaled_linear")
pipe.scheduler = lms

#pipe.enable_xformers_memory_efficient_attention()

# Load your front-face sprite (PIL image)

im = "untexturedLevel.png"


img = Image.open(im)
front_face = img.resize((1200, 800))
#front_face.show()


# Prompt describing the back of head
prompt = (
    "A detailed top-down view of a factory floor"
)

negative = ("blurry, low-resolution, distorted hands, deformed face, poorly drawn anatomy, no face")

# Generate
output = pipe(prompt=prompt, negative_prompt=negative, image=front_face, strength=0.9, guidance_scale=7.5).images[0]

# Save
output.save("back_of_head.png")
