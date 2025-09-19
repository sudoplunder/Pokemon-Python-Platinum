"""Beautiful Pokemon game window using tkinter for enhanced visuals."""

import tkinter as tk
from tkinter import font as tkfont, messagebox
import threading
import queue
import sys
from io import StringIO
from rich.console import Console
from rich.text import Text
import re

class PokemonGameWindow:
    """A beautiful game window that captures Rich output and displays it with proper styling."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pokemon Platinum Text - Enhanced Edition")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")
        
        # Create fonts
        self.mono_font = tkfont.Font(family="Consolas", size=12)
        self.title_font = tkfont.Font(family="Consolas", size=16, weight="bold")
        
        # Create main frame
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create title
        title_label = tk.Label(
            main_frame,
            text="POKEMON PLATINUM - ENHANCED EDITION",
            font=self.title_font,
            bg="#1a1a2e",
            fg="#ffd700"
        )
        title_label.pack(pady=(0, 20))
        
        # Create text widget with scrollbar
        text_frame = tk.Frame(main_frame, bg="#1a1a2e")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget
        self.text_widget = tk.Text(
            text_frame,
            font=self.mono_font,
            bg="#0f3460",
            fg="#ffffff",
            insertbackground="#ffd700",
            selectbackground="#16537e",
            selectforeground="#ffffff",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Configure text tags for colors
        self._setup_color_tags()
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg="#1a1a2e")
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(
            input_frame,
            text=">",
            font=self.mono_font,
            bg="#1a1a2e",
            fg="#ffd700"
        ).pack(side=tk.LEFT)
        
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_frame,
            textvariable=self.input_var,
            font=self.mono_font,
            bg="#0f3460",
            fg="#ffffff",
            insertbackground="#ffd700",
            selectbackground="#16537e"
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Bind input
        self.input_entry.bind("<Return>", self._on_input)
        self.input_entry.focus()
        
        # Queue for thread communication
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        
        # Start output monitoring
        self._check_output_queue()
        
    def _setup_color_tags(self):
        """Setup color tags for Rich text styling."""
        # Basic colors
        self.text_widget.tag_configure("red", foreground="#ff6b6b")
        self.text_widget.tag_configure("green", foreground="#51cf66")
        self.text_widget.tag_configure("blue", foreground="#339af0")
        self.text_widget.tag_configure("yellow", foreground="#ffd43b")
        self.text_widget.tag_configure("cyan", foreground="#22b8cf")
        self.text_widget.tag_configure("magenta", foreground="#f06595")
        self.text_widget.tag_configure("white", foreground="#ffffff")
        
        # Bright colors
        self.text_widget.tag_configure("bright_red", foreground="#ff8787")
        self.text_widget.tag_configure("bright_green", foreground="#69db7c")
        self.text_widget.tag_configure("bright_blue", foreground="#4dabf7")
        self.text_widget.tag_configure("bright_yellow", foreground="#ffe066")
        self.text_widget.tag_configure("bright_cyan", foreground="#3bc9db")
        self.text_widget.tag_configure("bright_magenta", foreground="#f783ac")
        self.text_widget.tag_configure("bright_white", foreground="#ffffff")
        
        # Styles
        self.text_widget.tag_configure("bold", font=(self.mono_font.cget("family"), self.mono_font.cget("size"), "bold"))
        self.text_widget.tag_configure("dim", foreground="#666666")
        
    def _on_input(self, event):
        """Handle user input."""
        text = self.input_var.get()
        self.input_var.set("")
        self.input_queue.put(text)
        
    def _check_output_queue(self):
        """Check for output from the game thread."""
        try:
            while True:
                text = self.output_queue.get_nowait()
                self._display_text(text)
        except queue.Empty:
            pass
        
        self.root.after(50, self._check_output_queue)
        
    def _display_text(self, text):
        """Display text with Rich formatting."""
        self.text_widget.config(state=tk.NORMAL)
        
        # Simple Rich markup parser for basic styling
        current_pos = self.text_widget.index(tk.END)
        
        # Remove Rich markup and apply colors
        clean_text = self._parse_rich_markup(text)
        
        self.text_widget.insert(tk.END, clean_text + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)
        
    def _parse_rich_markup(self, text):
        """Parse basic Rich markup and return clean text."""
        # This is a simple parser - Rich has complex markup
        # For now, just strip the markup and return clean text
        # You could enhance this to apply actual formatting
        clean = re.sub(r'\[/?[^\]]*\]', '', text)
        return clean
        
    def write_output(self, text):
        """Write output to the window (thread-safe)."""
        self.output_queue.put(text)
        
    def get_input(self, prompt=""):
        """Get input from user (blocking)."""
        if prompt:
            self.write_output(prompt)
        
        # Wait for input
        while True:
            try:
                return self.input_queue.get(timeout=0.1)
            except queue.Empty:
                self.root.update()
                
    def run(self):
        """Start the window."""
        self.root.mainloop()
        
    def close(self):
        """Close the window."""
        self.root.quit()


# Global window instance
game_window = None

def init_game_window():
    """Initialize the game window."""
    global game_window
    game_window = PokemonGameWindow()
    return game_window

def get_game_window():
    """Get the current game window."""
    return game_window