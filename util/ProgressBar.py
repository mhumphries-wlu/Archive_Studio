# util/ProgressBar.py

# This file contains the ProgressBar class, which is used to handle
# the progress bar for the application. 

import tkinter as tk
from tkinter import ttk

class ProgressBar:
    def __init__(self, master):
        """
        Initialize the ProgressBar class.
        
        Args:
            master: The parent tkinter window
        """
        self.master = master
        self.progress_window = None
        self.progress_bar = None
        self.progress_label = None

    def set_total_steps(self, total_steps):
        """
        Set the maximum value for the progress bar.
        
        Args:
            total_steps (int): The total number of steps (e.g., pages, files).
        """
        if self.progress_bar:
            self.progress_bar['maximum'] = total_steps

    def create_progress_window(self, title):
        """
        Create and display a progress window with a progress bar.
        
        Args:
            title (str): The title for the progress window
            
        Returns:
            tuple: (progress_window, progress_bar, progress_label)
        """
        # Create a new Tkinter window for the progress bar
        self.progress_window = tk.Toplevel(self.master)
        self.progress_window.title(title)
        self.progress_window.geometry("400x100")

        # Create a progress bar
        self.progress_bar = ttk.Progressbar(
            self.progress_window, 
            length=350, 
            mode='determinate'
        )
        self.progress_bar.pack(pady=20)

        # Create a label to display the progress percentage
        self.progress_label = tk.Label(self.progress_window, text="0%")
        self.progress_label.pack()

        # Ensure the progress window is displayed on top of the main window
        self.progress_window.attributes("-topmost", True)

        return self.progress_window, self.progress_bar, self.progress_label

    def update_progress(self, processed_rows, total_rows):
        """
        Update the progress bar and label with current progress.
        
        Args:
            processed_rows (int): Number of processed rows
            total_rows (int): Total number of rows to process
        """
        # Calculate the progress percentage
        if total_rows > 0:
            progress = (processed_rows / total_rows) * 100
            self.progress_bar['value'] = processed_rows
            self.progress_label.config(text=f"{progress:.2f}%")
        
        # Update the progress bar and label
        self.progress_bar.update()
        self.progress_label.update()

    def close_progress_window(self):
        """
        Close the progress window.
        """
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
            self.progress_bar = None
            self.progress_label = None