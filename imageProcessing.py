import pygame

import numpy as np
from PIL import Image
from rembg import remove
import io
def gaussian_blur(surface, sigma=5):
    """
    Apply a Gaussian blur to a Pygame surface.

    Args:
        surface (pygame.Surface): The surface to blur.
        sigma (float): The standard deviation for the Gaussian kernel.

    Returns:
        pygame.Surface: A new surface with the Gaussian blur applied.
    """
    # Convert surface to an array
    width, height = surface.get_size()
    
    # Get the RGB and alpha channels
    rgb_array = pygame.surfarray.array3d(surface)
    alpha_array = pygame.surfarray.array_alpha(surface)

    # Create a Gaussian kernel
    kernel_size = int(2 * (sigma + 0.5)) + 1
    kernel = np.fromfunction(
        lambda x, y: (1 / (2 * np.pi * sigma ** 2)) * 
                      np.exp(-((x - (kernel_size - 1) / 2) ** 2 + (y - (kernel_size - 1) / 2) ** 2) / (2 * sigma ** 2)),
        (kernel_size, kernel_size)
    )
    kernel /= np.sum(kernel)  # Normalize the kernel

    # Pad the RGB and alpha arrays
    pad_width = kernel_size // 2
    padded_rgb = np.pad(rgb_array, ((pad_width, pad_width), (pad_width, pad_width), (0, 0)), mode='reflect')
    padded_alpha = np.pad(alpha_array, ((pad_width, pad_width), (pad_width, pad_width)), mode='reflect')

    # Create an output array for RGB and alpha
    output_rgb = np.zeros_like(rgb_array)
    output_alpha = np.zeros_like(alpha_array)

    # Apply the Gaussian blur for each color channel
    for i in range(width):
        for j in range(height):
            # Extract the region of interest for the current pixel
            region_rgb = padded_rgb[i:i + kernel_size, j:j + kernel_size]
            region_alpha = padded_alpha[i:i + kernel_size, j:j + kernel_size]
            # Apply the kernel to each color channel
            for channel in range(3):  # Loop over the RGB channels
                output_rgb[i, j, channel] = np.sum(kernel * region_rgb[:, :, channel])
            # Average the alpha value
            output_alpha[i, j] = np.sum(kernel * region_alpha)

    # Create a new RGBA surface
    blurred_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # Set the RGB values
    pygame.surfarray.blit_array(blurred_surface, output_rgb)

    # Set the alpha values manually
    for i in range(width):
        for j in range(height):
            blurred_surface.set_at((i, j), (*output_rgb[i, j], output_alpha[i, j]))

    return blurred_surface





def remove_background(input_path, output_path):
    print("Removing:", input_path)
    # Open the input image file
    with open(input_path, 'rb') as input_file:
        input_image = input_file.read()

    # Remove the background
    output_image = remove(input_image)

    # Convert the output bytes to an image and save it
    img = Image.open(io.BytesIO(output_image))
    img.save(output_path)

    print(f"Background removed and saved to {output_path}")

def trim_surface(surface):
    # Get the surface size
    width, height = surface.get_size()

    # Lock the surface to directly access the pixel array
    surface.lock()

    # Create a mask based on alpha transparency (non-zero alpha means non-transparent)
    mask = pygame.mask.from_surface(surface)

    # Get the bounding box of the non-transparent area
    rects = mask.get_bounding_rects()


    
    if rects:
        rects.sort(key=lambda r: r.width * r.height, reverse=True)
        # If a bounding box is found, crop the surface to that bounding box
        trimmed_surface = surface.subsurface(rects[0]).copy()
    else:
        # If no bounding box is found (fully transparent image), return the original surface
        trimmed_surface = surface.copy()

    # Unlock the surface after accessing the pixels
    surface.unlock()

    return trimmed_surface
