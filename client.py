import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, messagebox
from PIL import Image, ImageTk
import socket
import threading
import os
import time
import io

import protocol
from media_utils import VideoCamera, AudioRecorder, AudioPlayer

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyChat Pro - University Edition")
        self.root.geometry("900x600")
        
        # Networking
        self.client_socket = None
        self.username = ""
        self.is_connected = False
        self.target_user = "All" # "All" or specific username
        
        # Call State
        self.in_call = False
        self.call_window = None
        
        # UI Layout
        self.setup_ui()
        
        # Connect prompt
        self.connect_to_server()

    def setup_ui(self):
        # -- Left Side: Chat & Input --
        left_frame = tk.Frame(self.root, width=600)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.chat_area = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD)
        self.chat_area.config(state='disabled') # Read only
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        input_frame = tk.Frame(left_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.msg_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.msg_entry.bind("<Return>", self.send_msg)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        send_btn = tk.Button(input_frame, text="Send", command=self.send_msg, bg="#4CAF50", fg="white")
        send_btn.pack(side=tk.LEFT, padx=5)

        # Tool Bar
        tool_frame = tk.Frame(left_frame)
        tool_frame.pack(fill=tk.X)
        
        tk.Button(tool_frame, text="Attach File", command=self.send_file).pack(side=tk.LEFT)
        tk.Button(tool_frame, text="Create Room", command=self.create_room).pack(side=tk.LEFT)
        tk.Button(tool_frame, text="Start Video Call", command=self.start_call, bg="#2196F3", fg="white").pack(side=tk.RIGHT)

        # -- Right Side: User List & Rooms --
        right_frame = tk.Frame(self.root, width=200, bg="lightgray")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(right_frame, text="Online Users", bg="lightgray").pack(pady=5)
        self.user_listbox = tk.Listbox(right_frame, height=15)
        self.user_listbox.pack(padx=5, fill=tk.X)
        self.user_listbox.bind('<<ListboxSelect>>', self.select_user)

        tk.Label(right_frame, text="Available Rooms", bg="lightgray").pack(pady=15)
        self.room_listbox = tk.Listbox(right_frame, height=10)
        self.room_listbox.pack(padx=5, fill=tk.X)
        self.room_listbox.bind('<Double-1>', self.join_room)

    def connect_to_server(self):
        host = simpledialog.askstring("Server", "Enter Server IP:", initialvalue="127.0.0.1")
        if not host: host = "127.0.0.1"
        
        self.username = simpledialog.askstring("Login", "Choose Username:")
        if not self.username: self.root.quit()

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, protocol.PORT))
            
            # Send Login Packet
            protocol.send_packet(self.client_socket, protocol.CMD_LOGIN, {'username': self.username})
            
            self.is_connected = True
            
            # Start Listening Thread
            threading.Thread(target=self.listen_server, daemon=True).start()
            self.root.title(f"PyChat Pro - Logged in as {self.username}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect: {e}")
            self.root.quit()

    # --- Core Chat Logic ---
    
    def select_user(self, event):
        selection = self.user_listbox.curselection()
        if selection:
            user = self.user_listbox.get(selection[0])
            if user == self.username: return
            self.target_user = user
            self.msg_entry.config(bg="#fff8dc") # Yellow tint for private mode
            print(f"Private target set to: {user}")
        else:
            self.target_user = "All"
            self.msg_entry.config(bg="white")

    def send_msg(self, event=None):
        text = self.msg_entry.get()
        if not text: return
        
        if self.target_user == "All":
            # Public
            protocol.send_packet(self.client_socket, protocol.CMD_MSG, {"text": text, "to": "All"})
        else:
            # Private
            protocol.send_packet(self.client_socket, protocol.CMD_MSG, {"text": text, "to": self.target_user})
            
        self.msg_entry.delete(0, tk.END)

    def create_room(self):
        room_name = simpledialog.askstring("Room", "New Room Name:")
        if room_name:
            protocol.send_packet(self.client_socket, protocol.CMD_ROOM_JOIN, {"room": room_name})

    def join_room(self, event):
        selection = self.room_listbox.curselection()
        if selection:
            room = self.room_listbox.get(selection[0])
            protocol.send_packet(self.client_socket, protocol.CMD_ROOM_JOIN, {"room": room})

    def append_message(self, msg_type, sender, content):
        self.chat_area.config(state='normal')
        timestamp = time.strftime("%H:%M")
        
        if msg_type == "text":
            self.chat_area.insert(tk.END, f"[{timestamp}] {sender}: {content}\n")
        elif msg_type == "private":
            self.chat_area.insert(tk.END, f"[{timestamp}] (PVT) {sender}: {content}\n", "private")
            self.chat_area.tag_config("private", foreground="red")
        elif msg_type == "file":
             self.chat_area.insert(tk.END, f"[{timestamp}] {sender} sent a file: {content}\n", "file")
             self.chat_area.tag_config("file", foreground="blue")
             
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    # --- File Sharing ---
    
    def send_file(self):
        filepath = filedialog.askopenfilename()
        if not filepath: return
        
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        # Read file bytes
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        data = {
            "filename": filename,
            "size": file_size,
            "content": file_bytes,
            "to": self.target_user if self.target_user != "All" else None
        }
        
        protocol.send_packet(self.client_socket, protocol.CMD_FILE, data)
        self.append_message("text", "Me", f"Sent file: {filename}")

    def save_incoming_file(self, filename, content):
        # Auto save to 'Downloads' folder in project dir
        if not os.path.exists("downloads"): os.makedirs("downloads")
        save_path = os.path.join("downloads", f"received_{filename}")
        with open(save_path, "wb") as f:
            f.write(content)
        return save_path

    # --- Video/Voice Calling (Threaded) ---

    def start_call(self):
        if self.target_user == "All":
            messagebox.showwarning("Call", "Select a user from the list to call.")
            return
            
        # Open Call Window
        self.setup_call_window(target=self.target_user, incoming=False)
        
        # Launch transmission threads
        threading.Thread(target=self.send_video_stream, args=(self.target_user,), daemon=True).start()
        threading.Thread(target=self.send_audio_stream, args=(self.target_user,), daemon=True).start()

    def setup_call_window(self, target, incoming=False):
        self.in_call = True
        self.call_window = tk.Toplevel(self.root)
        title = f"Incoming Call from {target}" if incoming else f"Calling {target}..."
        self.call_window.title(title)
        self.call_window.protocol("WM_DELETE_WINDOW", self.end_call)

        self.video_label = tk.Label(self.call_window)
        self.video_label.pack()

    def end_call(self):
        self.in_call = False
        if self.call_window:
            self.call_window.destroy()
            self.call_window = None

    def send_video_stream(self, target):
        camera = VideoCamera()
        while self.in_call and self.is_connected:
            frame_bytes = camera.get_frame_bytes()
            if frame_bytes:
                # Send via server
                data = {"target": target, "frame": frame_bytes}
                protocol.send_packet(self.client_socket, protocol.CMD_VIDEO, data, is_encrypted=False)
            time.sleep(0.05) # Cap at ~20 FPS
        camera.cleanup()

    def send_audio_stream(self, target):
        mic = AudioRecorder()
        mic.start()
        while self.in_call and self.is_connected:
            chunk = mic.get_chunk()
            if chunk:
                data = {"target": target, "chunk": chunk}
                protocol.send_packet(self.client_socket, protocol.CMD_AUDIO, data, is_encrypted=False)
        mic.stop()

    def update_call_video(self, frame_bytes):
        # Called from network thread
        if not self.in_call or not self.call_window: return
        try:
            image = Image.open(io.BytesIO(frame_bytes))
            photo = ImageTk.PhotoImage(image)
            self.video_label.configure(image=photo)
            self.video_label.image = photo # keep reference
        except: pass

    # --- Network Listener ---

    def listen_server(self):
        # Audio player is persistent to reduce lag in startup
        player = AudioPlayer()
        
        while self.is_connected:
            packet = protocol.receive_packet(self.client_socket)
            if not packet:
                print("Disconnected from server")
                self.is_connected = False
                break
                
            cmd = packet['type']
            data = packet['data']

            if cmd == protocol.CMD_LIST_UPDATE:
                users = data['users']
                rooms = data['rooms']
                
                self.user_listbox.delete(0, tk.END)
                self.user_listbox.insert(tk.END, "All") # broadcast option
                for u in users:
                    self.user_listbox.insert(tk.END, u)
                    
                self.room_listbox.delete(0, tk.END)
                for r in rooms:
                    self.room_listbox.insert(tk.END, r)

            elif cmd == protocol.CMD_MSG:
                sender = data['from']
                text = data['text']
                is_pvt = data.get("is_private", False)
                
                msg_type = "private" if is_pvt else "text"
                if sender == self.username: sender = "Me" # Self echo handled locally mostly, but confirmation helpful
                
                # TKINTER Thread Safety: Not purely threadsafe, but append is usually tolerant. 
                # Ideal is root.after, direct call here used for simplicity in code size
                self.append_message(msg_type, sender, text)

            elif cmd == protocol.CMD_FILE:
                sender = data['from']
                filename = data['filename']
                path = self.save_incoming_file(filename, data['content'])
                self.append_message("file", sender, f"{filename} (Saved in downloads/)")

            elif cmd == protocol.CMD_VIDEO:
                # If we are not in call, we should probably open window or notify
                # For this demo: Open window automatically if receiving frames
                if not self.in_call:
                     sender = data.get('sender')
                     self.root.after(0, lambda: self.setup_call_window(target=sender, incoming=True))
                     self.in_call = True
                
                frame = data['frame']
                # GUI update must be scheduled on Main Thread for image
                self.root.after(0, lambda: self.update_call_video(frame))

            elif cmd == protocol.CMD_AUDIO:
                # Play directly in thread (audio is non-blocking)
                chunk = data['chunk']
                player.play(chunk)
        
        player.cleanup()
        self.client_socket.close()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()