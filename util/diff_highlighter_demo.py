import tkinter as tk
from AdvancedDiffHighlighting import AdvancedDiffHighlighter

class DiffHighlighterDemo:
    def __init__(self):
        # Create a root window
        self.root = tk.Tk()
        self.root.title("Advanced Diff Highlighter Demo")
        self.root.geometry("800x600")
        
        # Create a frame for text inputs
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", pady=10)
        
        # Labels
        tk.Label(input_frame, text="Previous Text:").grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(input_frame, text="Current Text:").grid(row=0, column=1, sticky="w", padx=5)
        
        # Text inputs
        self.previous_text = tk.Text(input_frame, height=8, width=40)
        self.previous_text.grid(row=1, column=0, padx=5)
        
        self.current_text = tk.Text(input_frame, height=8, width=40)
        self.current_text.grid(row=1, column=1, padx=5)
        
        # Button to highlight differences
        highlight_button = tk.Button(self.root, text="Highlight Differences", command=self.highlight_differences)
        highlight_button.pack(pady=10)
        
        # Frame for the result
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Label for result
        tk.Label(result_frame, text="Result with Highlighting:").pack(anchor="w")
        
        # Result text widget (where highlighting will be shown)
        self.result_text = tk.Text(result_frame, height=15, width=80)
        self.result_text.pack(fill="both", expand=True)
        
        # Initialize the highlighter
        self.highlighter = AdvancedDiffHighlighter(self.result_text)
        
        # Load sample text
        self.load_sample_text()
        
    def load_sample_text(self):
        """Load sample text for demonstration"""
        sample_previous = ("This is a sample text.\n"
                          "This line will be changed.\n"
                          "This line will be deleted.\n"
                          "This line stays the same.\n"
                          "Some words in this line will change.")
        
        sample_current = ("This is a sample text.\n"
                         "This line has been changed completely.\n"
                         "This line stays the same.\n"
                         "Some words in this line will be modified.\n"
                         "This is a new line that was added.")
        
        self.previous_text.delete("1.0", tk.END)
        self.previous_text.insert("1.0", sample_previous)
        
        self.current_text.delete("1.0", tk.END)
        self.current_text.insert("1.0", sample_current)
    
    def highlight_differences(self):
        """Highlight the differences between previous and current text"""
        # Get text from the input widgets
        previous = self.previous_text.get("1.0", "end-1c")
        current = self.current_text.get("1.0", "end-1c")
        
        # Display the current text in the result widget
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", current)
        
        # Apply highlighting
        self.highlighter.highlight_differences(previous, current)
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = DiffHighlighterDemo()
    app.run() 