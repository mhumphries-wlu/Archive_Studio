import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class HourglassAnimation(tk.Toplevel):
    def __init__(self, master=None, delay=200, icon_paths=None):
        super().__init__(master)
        self.title("Please Wait...")
        self.resizable(False, False)
        self.geometry("150x150")
        self.configure(bg="white")
        self.delay = delay

        # If no icon_paths are provided, use default names.
        if icon_paths is None:
            icon_paths = [
                "hourglass1.png",
                "hourglass2.png",
                "hourglass3.png",
                "hourglass4.png"
            ]
        self.frames = []
        for path in icon_paths:
            try:
                img = Image.open(path)
                # Resize the icons to a uniform size (e.g., 64x64 pixels)
                img = img.resize((64, 64), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(img)
                self.frames.append(photo)
            except Exception as e:
                print(f"Error loading {path}: {e}")
        
        if not self.frames:
            raise ValueError("No valid hourglass images were loaded.")

        self.current_frame = 0
        self.label = ttk.Label(self, image=self.frames[self.current_frame], background="white")
        self.label.pack(expand=True)

        # Start the animation loop.
        self.after(self.delay, self.animate)

    def animate(self):
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.label.configure(image=self.frames[self.current_frame])
        self.after(self.delay, self.animate)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main root window.
    # Provide the list of icon file paths for the hourglass animation.
    hourglass_icons = ["hourglass1.png", "hourglass2.png", "hourglass3.png", "hourglass4.png"]
    animation = HourglassAnimation(root, delay=200, icon_paths=hourglass_icons)
    animation.mainloop()
