import os
import cv2
from tkinter import Tk, filedialog, messagebox
from PIL import Image
import pytesseract

# Set the path to Tesseract executable if needed
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(image_path):
    """Preprocess the image for better OCR results."""
    # Load the image in grayscale
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Resize the image to improve OCR accuracy
    scale_factor = 2  # Scale up by 2x
    image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    
    # Apply adaptive thresholding for binarization
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Save preprocessed image for debugging (optional)
    preprocessed_path = "preprocessed_temp.png"
    cv2.imwrite(preprocessed_path, image)
    
    return preprocessed_path

def select_folder():
    """Open folder selection dialog."""
    folder = filedialog.askdirectory(title="Select Folder with Images")
    if folder:
        process_images(folder)

def process_images(folder):
    """Process all images in the selected folder."""
    output_folder = filedialog.askdirectory(title="Select Output Folder")
    if not output_folder:
        messagebox.showinfo("Cancelled", "No output folder selected.")
        return
    
    # Get list of image files
    image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")
    images = [f for f in os.listdir(folder) if f.lower().endswith(image_extensions)]

    if not images:
        messagebox.showwarning("No Images Found", "No valid image files found in the selected folder.")
        return
    
    # Process each image
    for image_file in images:
        image_path = os.path.join(folder, image_file)
        output_text_path = os.path.join(output_folder, os.path.splitext(image_file)[0] + ".txt")

        # Print the name of the image being processed
        print(f"Processing: {image_file}")
        
        try:
            # Preprocess the image for better OCR
            preprocessed_image_path = preprocess_image(image_path)
            
            # OCR the image with JPN vertical text
            custom_config = r'--psm 5 -l jpn_vert'
            text = pytesseract.image_to_string(Image.open(preprocessed_image_path), config=custom_config)
            
            # Save the output
            with open(output_text_path, "w", encoding="utf-8") as output_file:
                output_file.write(text)
                
            # Cleanup temporary preprocessed image
            os.remove(preprocessed_image_path)
            
        except Exception as e:
            print(f"Error processing {image_file}: {e}")
            messagebox.showerror("Error", f"Error processing {image_file}: {e}")
    
    messagebox.showinfo("Completed", "Batch OCR completed successfully!")

def create_gui():
    """Create the tkinter GUI."""
    root = Tk()
    root.title("Batch OCR for Japanese Vertical Text")
    root.geometry("400x200")
    
    # Buttons
    select_button = filedialog.Button(
        root,
        text="Select Folder of Images",
        command=select_folder,
        padx=10,
        pady=10
    )
    select_button.pack(pady=20)
    
    exit_button = filedialog.Button(
        root,
        text="Exit",
        command=root.quit,
        padx=10,
        pady=10
    )
    exit_button.pack(pady=20)
    
    root.mainloop()

# Run the GUI
if __name__ == "__main__":
    create_gui()
