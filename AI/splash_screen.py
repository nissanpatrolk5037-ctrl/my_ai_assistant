import customtkinter as ctk
import time

# Initialize the customtkinter theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure the splash screen window
        self.overrideredirect(True)  # Remove window decorations (title bar, borders)
        self.attributes("-topmost", True)  # Keep the window on top
        self.title("Splash Screen")
        self.configure(fg_color="#05edbb")  # Set the background color using fg_color
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        window_width = 400
        window_height = 300
        x = (width // 2) - (window_width // 2)
        y = (height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add a label for the splash screen text
        self.label = ctk.CTkLabel(
            self, 
            text="Welcome to Lyra!", 
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color="black"
        )
        self.label.pack(expand=True)
        
        # Add a progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=300, bg_color="white", fg_color="black")
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)  # Set initial progress to 0
        
        self.after(100, self.update_progress)  # Start updating progress

    def update_progress(self):
        current_value = self.progress_bar.get()
        if current_value < 1:
            self.progress_bar.set(current_value + 0.01)  # Increment progress
            self.after(25, self.update_progress)  # Update every 50ms
        else:
            self.destroy() 


