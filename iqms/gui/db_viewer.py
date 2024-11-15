import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime

class DatabaseViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Screw Detection Database Viewer")
        self.root.geometry("800x600")

        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create Treeview
        self.create_treeview()
        
        # Create control buttons
        self.create_controls()
        
        # Load initial data
        self.refresh_data()

    def create_treeview(self):
        # Create Treeview widget
        columns = ('chamber_number', 'missing_screws', 'good_screws', 'timestamp')
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show='headings')

        # Define headings
        self.tree.heading('chamber_number', text='Chamber Number')
        self.tree.heading('missing_screws', text='Missing Screws')
        self.tree.heading('good_screws', text='Good Screws')
        self.tree.heading('timestamp', text='Timestamp')

        # Define columns width
        self.tree.column('chamber_number', width=120)
        self.tree.column('missing_screws', width=120)
        self.tree.column('good_screws', width=120)
        self.tree.column('timestamp', width=200)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, columnspan=4, sticky='nsew')
        scrollbar.grid(row=0, column=4, sticky='ns')

    def create_controls(self):
        # Control buttons frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.grid(row=1, column=0, columnspan=4, pady=10)

        # Buttons
        ttk.Button(control_frame, text="Refresh Data", command=self.refresh_data).grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="Export to CSV", command=self.export_to_csv).grid(row=0, column=2, padx=5)

        # Search frame
        search_frame = ttk.Frame(self.main_frame)
        search_frame.grid(row=2, column=0, columnspan=4, pady=5)

        ttk.Label(search_frame, text="Search Chamber:").grid(row=0, column=0, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, padx=5)
        ttk.Button(search_frame, text="Search", command=self.search_records).grid(row=0, column=2, padx=5)
        ttk.Button(search_frame, text="Clear Search", command=self.clear_search).grid(row=0, column=3, padx=5)

    def refresh_data(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Connect to database and fetch all records
        conn = sqlite3.connect('screw_detection.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM detections ORDER BY timestamp DESC')
        rows = cursor.fetchall()

        # Insert data into treeview
        for row in rows:
            # Convert timestamp string to datetime object and format it
            timestamp = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
            self.tree.insert('', tk.END, values=(row[0], row[1], row[2], timestamp))

        conn.close()

    def delete_selected(self):
        # Get selected item
        selected_item = self.tree.selection()
        if not selected_item:
            return

        # Get chamber number of selected item
        chamber_number = self.tree.item(selected_item)['values'][0]

        # Connect to database and delete record
        conn = sqlite3.connect('screw_detection.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM detections WHERE chamber_number = ?', (chamber_number,))
        conn.commit()
        conn.close()

        # Refresh the display
        self.refresh_data()

    def search_records(self):
        search_term = self.search_var.get()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Connect to database and fetch matching records
        conn = sqlite3.connect('screw_detection.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM detections WHERE chamber_number LIKE ? ORDER BY timestamp DESC', 
                      ('%' + search_term + '%',))
        rows = cursor.fetchall()

        # Insert matching data into treeview
        for row in rows:
            timestamp = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
            self.tree.insert('', tk.END, values=(row[0], row[1], row[2], timestamp))

        conn.close()

    def clear_search(self):
        self.search_var.set('')
        self.refresh_data()

    def export_to_csv(self):
        import csv
        from tkinter import filedialog
        
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            conn = sqlite3.connect('screw_detection.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM detections ORDER BY timestamp DESC')
            rows = cursor.fetchall()
            
            with open(file_path, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                # Write header
                csv_writer.writerow(['Chamber Number', 'Missing Screws', 'Good Screws', 'Timestamp'])
                # Write data
                for row in rows:
                    timestamp = datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
                    csv_writer.writerow([row[0], row[1], row[2], timestamp])
            
            conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseViewer(root)
    root.mainloop()