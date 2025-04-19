"""
WordPress Posting module for the novel translation tool.

This module provides functionality for:
- Posting translated content to WordPress
- Managing WordPress credentials
- Handling batch posting of translated files
"""

import os
import re
import time
import tkinter as tk
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.methods.media import UploadFile

class WordPressPoster:
    """
    Handles posting translated content to WordPress.
    
    This class provides functionality for:
    - Connecting to WordPress sites
    - Posting translated content as WordPress posts
    - Managing WordPress credentials through a GUI
    """
    
    def __init__(self, log_message=None):
        self.log_message = log_message or print

    def post_to_wordpress(
        self,
        site_url: str,
        username: str,
        password: str,
        output_dir: str,
        category: str = "Novel",
        status: str = "draft"  # or "publish"
    ):
        """
        Posts all translated .txt files to WordPress as posts.
        
        Args:
            site_url: Your WordPress site URL (e.g., 'https://yoursite.wordpress.com')
            username: Your WordPress username
            password: Your WordPress application password
            output_dir: Directory containing the translated .txt files
            category: Category to assign to posts
            status: Post status ('draft' or 'publish')
        """
        try:
            # Initialize WordPress client
            wp = Client(f"{site_url}/xmlrpc.php", username, password)
            self.log_message("[WORDPRESS] Connected to WordPress site successfully.")

            # Get all translated .txt files
            text_files = [f for f in os.listdir(output_dir) if f.startswith("translated_") and f.endswith(".txt")]
            text_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))

            # Process files in batches of 5 with 10-second delay
            for i in range(0, len(text_files), 5):
                batch = text_files[i:i+5]
                self.log_message(f"\n=== Processing batch {i//5 + 1} of {(len(text_files)-1)//5 + 1} ===")

                for fname in batch:
                    try:
                        # Read the file content
                        file_path = os.path.join(output_dir, fname)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Create post title from filename (remove 'translated_' and '.txt')
                        title = fname.replace("translated_", "").replace(".txt", "")
                        
                        # Create WordPress post
                        post = WordPressPost()
                        post.title = title
                        post.content = content
                        post.post_status = status
                        post.terms_names = {
                            'category': [category]
                        }
                        post.date = datetime.now()

                        # Post to WordPress
                        post_id = wp.call(NewPost(post))
                        self.log_message(f"[WORDPRESS] Posted {fname} as post ID: {post_id}")

                    except Exception as e:
                        self.log_message(f"[ERROR] Failed to post {fname}: {e}")

                # Wait 10 seconds between batches if there are more files
                if i + 5 < len(text_files):
                    self.log_message("Waiting 10 seconds before next batch...")
                    time.sleep(10)

            self.log_message("[WORDPRESS] All files have been posted successfully.")

        except Exception as e:
            self.log_message(f"[ERROR] WordPress connection failed: {e}")

    def get_credentials(self):
        """
        Shows a dialog to get WordPress credentials from the user.
        Returns a tuple of (site_url, username, password) or None if cancelled.
        """
        class WordPressCredentialsDialog(tk.Toplevel):
            def __init__(self, parent):
                super().__init__(parent)
                self.title("WordPress Credentials")
                self.geometry("500x400")
                
                # Make window modal
                self.transient(parent)
                self.grab_set()
                
                # Instructions
                instructions = """
To post to WordPress, you'll need:
1. Your WordPress site URL
2. Your WordPress username
3. An Application Password

The following credentials are pre-filled:
Site: https://theundeadmachinetranslator.wordpress.com/
Password: q45w peed nrcd abrf

To get an Application Password:
- WordPress.com: Go to Settings → Security → Application Passwords
- WordPress.org: Go to Users → Profile → Application Passwords

The password will look like: q45w peed nrcd abrf
"""
                tk.Label(self, text=instructions, wraplength=450, justify=tk.LEFT).pack(pady=10, padx=10)
                
                # Site URL
                tk.Label(self, text="WordPress Site URL:").pack(pady=5)
                self.site_url = tk.Entry(self, width=50)
                self.site_url.insert(0, "https://theundeadmachinetranslator.wordpress.com/")
                self.site_url.pack(pady=5)
                
                # Username
                tk.Label(self, text="WordPress Username:").pack(pady=5)
                self.username = tk.Entry(self, width=50)
                self.username.insert(0, "your_username")
                self.username.pack(pady=5)
                
                # Password
                tk.Label(self, text="Application Password:").pack(pady=5)
                self.password = tk.Entry(self, width=50, show="*")
                self.password.insert(0, "q45w peed nrcd abrf")
                self.password.pack(pady=5)
                
                # Buttons
                button_frame = tk.Frame(self)
                button_frame.pack(pady=10)
                
                tk.Button(button_frame, text="Submit", command=self.ok).pack(side=tk.LEFT, padx=5)
                tk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
                
                # Result
                self.result = None
                
            def ok(self):
                self.result = (
                    self.site_url.get().strip(),
                    self.username.get().strip(),
                    self.password.get().strip()
                )
                self.destroy()
                
            def cancel(self):
                self.destroy()

        # Create and show the dialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        dialog = WordPressCredentialsDialog(root)
        root.wait_window(dialog)
        
        return dialog.result

    def validate_credentials(self, site_url, username, password):
        """
        Validates the provided WordPress credentials.
        Returns True if valid, False otherwise.
        """
        if not site_url or site_url == "https://theundeadmachinetranslator.wordpress.com/":
            self.log_message("[ERROR] Please enter a valid WordPress site URL.")
            return False
            
        if not username or username == "your_username":
            self.log_message("[ERROR] Please enter your WordPress username.")
            return False
            
        if not password or password == "q45w peed nrcd abrf":
            self.log_message("[ERROR] Please enter your WordPress application password.")
            return False
            
        return True

    def post_all_files(self):
        """
        Main method to handle WordPress posting.
        Prompts for WordPress credentials and posts all translated files.
        """
        # Get credentials from user
        credentials = self.get_credentials()
        if not credentials:
            self.log_message("[ERROR] WordPress posting cancelled.")
            return
            
        site_url, username, password = credentials
        
        # Validate credentials
        if not self.validate_credentials(site_url, username, password):
            return

        # Get output directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(script_dir, "output")

        # Post to WordPress
        self.post_to_wordpress(
            site_url=site_url,
            username=username,
            password=password,
            output_dir=output_dir
        )

def main(log_message):
    """
    Command-line entry point for WordPress posting.
    """
    poster = WordPressPoster(log_message)
    poster.post_all_files() 