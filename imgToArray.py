from PIL import Image
import io
import numpy as np
import os
from datetime import datetime

def img_to_array(image, orientation='portrait'):
    """
    Convert an image to a format suitable for e-paper displays.
    
    Args:
        image: PIL Image object
        orientation: The desired orientation ('portrait' or 'landscape')
        
    Returns:
        bytes: Raw bytes of the image data in the format expected by the e-paper display
    """
    
    # Ensure image is in RGB mode (not RGBA)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Determine if we need to rotate the image
    is_image_landscape = image.width > image.height
    is_target_landscape = orientation.lower() == 'landscape'
    
    # Rotate if needed to match the desired orientation
    if is_image_landscape != is_target_landscape:
        try:
            # For newer versions of PIL
            from PIL.Image import Transpose
            image = image.transpose(Transpose.ROTATE_90)
        except (ImportError, AttributeError):
            # For older versions of PIL
            image = image.transpose(Image.ROTATE_90)
    
    # Target dimensions for the e-paper display
    target_width, target_height = 1200, 1600
    
    # Resize to FILL the target dimensions (will crop if necessary)
    if image.size != (target_width, target_height):
        # Calculate the resize ratio for both dimensions
        width_ratio = target_width / image.width
        height_ratio = target_height / image.height
        
        # Use the LARGER ratio to ensure the image fills the target dimensions
        # This will result in cropping, but no white bars
        resize_ratio = max(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(image.width * resize_ratio)
        new_height = int(image.height * resize_ratio)
        
        # Resize the image to fill or exceed the target dimensions
        image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # If the image is now larger than the target, crop it to the center
        if new_width > target_width or new_height > target_height:
            # Calculate crop box (centered)
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            
            # Crop the image to the target dimensions
            image = image.crop((left, top, right, bottom))
    
    # Create a palette image with the 7 colors used by the e-paper display
    pal_image = Image.new('P', (1, 1))
    # The palette order is: Black, White, Yellow, Red, Black(duplicate), Blue, Green
    pal_image.putpalette((0,0,0, 255,255,255, 255,255,0, 255,0,0, 0,0,0, 0,0,255, 0,255,0) + (0,0,0)*249)
    
    # Convert the source image to the 7 colors, dithering if needed
    image_7color = image.convert("RGB").quantize(palette=pal_image)
    
    # Get the raw bytes of the quantized image
    buf_7color = bytearray(image_7color.tobytes('raw'))
    
    # PIL does not support 4 bit color, so pack the 4 bits of color
    # into a single byte to transfer to the panel
    buf = bytearray(int(image.width * image.height / 2))
    idx = 0
    
    # Pack two 4-bit color values into each byte
    for i in range(0, len(buf_7color), 2):
        if i + 1 < len(buf_7color):
            buf[idx] = (buf_7color[i] << 4) | buf_7color[i+1]
        else:
            # If we have an odd number of pixels, pad with white (1)
            buf[idx] = (buf_7color[i] << 4) | 1
        idx += 1
    
    return bytes(buf) 

def generate_demonstration_images(input_image_path, output_dir="upload/temp"):
    """
    Process an image through the conversion pipeline and save visualizations 
    of each step to help understand the process.
    
    Args:
        input_image_path: Path to the input image
        output_dir: Directory to save output images (default: "upload/temp")
    
    Returns:
        list: Paths to all generated images
    """
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Load the original image
    original_image = Image.open(input_image_path)
    
    # Save the original image
    original_path = os.path.join(output_dir, f"{timestamp}_1_original.jpg")
    original_image.save(original_path)
    
    # Ensure RGB mode
    if original_image.mode != 'RGB':
        original_image = original_image.convert('RGB')
    
    # Determine orientation and rotate if needed
    is_image_landscape = original_image.width > original_image.height
    oriented_image = original_image
    
    if is_image_landscape:
        try:
            # For newer versions of PIL
            from PIL.Image import Transpose
            oriented_image = original_image.transpose(Transpose.ROTATE_270)
        except (ImportError, AttributeError):
            # For older versions of PIL
            oriented_image = original_image.transpose(Image.ROTATE_270)
        
        oriented_path = os.path.join(output_dir, f"{timestamp}_2_rotated.jpg")
        oriented_image.save(oriented_path)
    
    # Target dimensions for the e-paper display
    target_width, target_height = 1200, 1600
    
    # Resize image to fill target dimensions
    width_ratio = target_width / oriented_image.width
    height_ratio = target_height / oriented_image.height
    resize_ratio = max(width_ratio, height_ratio)
    
    new_width = int(oriented_image.width * resize_ratio)
    new_height = int(oriented_image.height * resize_ratio)
    
    resized_image = oriented_image.resize((new_width, new_height), Image.LANCZOS)
    resized_path = os.path.join(output_dir, f"{timestamp}_3_resized.jpg")
    resized_image.save(resized_path)
    
    # Crop if needed
    if new_width > target_width or new_height > target_height:
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        cropped_image = resized_image.crop((left, top, right, bottom))
        cropped_path = os.path.join(output_dir, f"{timestamp}_4_cropped.jpg")
        cropped_image.save(cropped_path)
    else:
        cropped_image = resized_image
        cropped_path = resized_path
    
    # Create a palette image with the 7 colors used by the e-paper display
    pal_image = Image.new('P', (1, 1))
    # The palette order is: Black, White, Yellow, Red, Black(duplicate), Blue, Green
    pal_image.putpalette((0,0,0, 255,255,255, 255,255,0, 255,0,0, 0,0,0, 0,0,255, 0,255,0) + (0,0,0)*249)
    
    # Convert the source image to the 7 colors
    quantized_image = cropped_image.quantize(palette=pal_image)
    quantized_path = os.path.join(output_dir, f"{timestamp}_5_quantized.jpg")
    quantized_image.convert('RGB').save(quantized_path)
    
    # Create a visualization of the final byte array
    buf_7color = bytearray(quantized_image.tobytes('raw'))
    
    # This converts the byte array back to a viewable image to show what is sent to display
    reconstructed = Image.new('P', (target_width, target_height))
    reconstructed.putpalette((0,0,0, 255,255,255, 255,255,0, 255,0,0, 0,0,0, 0,0,255, 0,255,0) + (0,0,0)*249)
    reconstructed.putdata(buf_7color)
    
    final_path = os.path.join(output_dir, f"{timestamp}_6_final.jpg")
    reconstructed.convert('RGB').save(final_path)
    
    # Also save a visualization of how the actual bytes would look
    # (unpacking the 4-bit values that would be packed in the actual data)
    final_bytes_path = os.path.join(output_dir, f"{timestamp}_7_byte_representation.jpg")
    
    # Create an array to represent unpacked bytes
    width = target_width
    height = target_height
    unpacked_data = []
    
    # Simulate the packing/unpacking process
    buf = bytearray(int(width * height / 2))
    idx = 0
    
    for i in range(0, len(buf_7color), 2):
        if i + 1 < len(buf_7color):
            buf[idx] = (buf_7color[i] << 4) | buf_7color[i+1]
            unpacked_data.append(buf_7color[i])
            unpacked_data.append(buf_7color[i+1])
        else:
            buf[idx] = (buf_7color[i] << 4) | 1
            unpacked_data.append(buf_7color[i])
            unpacked_data.append(1)  # white padding
        idx += 1
    
    # Create image from unpacked data
    unpacked_image = Image.new('P', (width, height))
    unpacked_image.putpalette((0,0,0, 255,255,255, 255,255,0, 255,0,0, 0,0,0, 0,0,255, 0,255,0) + (0,0,0)*249)
    unpacked_image.putdata(unpacked_data)
    unpacked_image.convert('RGB').save(final_bytes_path)
    
    # Return paths to all generated images
    return [
        original_path,
        oriented_path if is_image_landscape else None,
        resized_path,
        cropped_path if cropped_path != resized_path else None,
        quantized_path,
        final_path,
        final_bytes_path
    ]

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python imgToArray.py <input_image_path> [output_directory]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "upload/temp"
    
    generated_images = generate_demonstration_images(input_path, output_dir)
    
    print(f"Generated demonstration images in {output_dir}:")
    for img_path in generated_images:
        if img_path:
            print(f"- {img_path}")