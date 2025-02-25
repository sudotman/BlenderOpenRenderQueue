import sys
import subprocess
import threading
import time
import os
import signal
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QFileDialog, QLabel, QProgressBar, QLineEdit, QStyle
)
from PyQt6.QtCore import pyqtSignal, Qt

def find_blender_executable():
    possible_paths = [
        "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",  # Windows default
        "/Applications/Blender.app/Contents/MacOS/Blender",  # macOS default
        "/usr/bin/blender",  # Linux default
        "/usr/local/bin/blender"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

class DecimalProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFormat("%p%")  # Use built-in format string
        self.setStyleSheet("""
            QProgressBar {
                text-align: center;
                padding: 1px;
                border: 1px solid grey;
                border-radius: 3px;
                background: #262626;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background: #337AB7;
            }
        """)

    def text(self):
        # Convert progress (0-1000) to percentage (0-100) with one decimal place
        percentage = self.value() / 10.0
        return f"{percentage:.1f}%"

class RenderQueueApp(QWidget):
    progress_update = pyqtSignal(int)  # Add this near the top of the class
    
    def __init__(self):
        super().__init__()
        self.queue = []
        self.rendering = False
        self.process = None
        self.render_thread = None
        self.blender_executable = find_blender_executable()
        self.current_file_progress = 0
        self.initUI()
        self.progress_update.connect(self.fileProgressBar.setValue)  # Connect the signal

        if not self.blender_executable:
            self.statusLabel.setText("Blender executable not found! Please specify manually.")

    def initUI(self):
        self.setWindowTitle("Blender Render Queue")
        self.setGeometry(100, 100, 600, 700)
        
        # Update stylesheet to include warning states and list item styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 10pt;
            }
            QListWidget {
                background-color: #363636;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
                margin: 5px 0;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 2px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #0d6efd;
            }
            QListWidget::item:hover {
                background-color: #404040;
            }
            QPushButton {
                background-color: #0d6efd;
                border: none;
                border-radius: 4px;
                padding: 8px;
                margin: 2px 0;
                color: white;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #707070;
                border: 1px solid #4d4d4d;
            }
            QPushButton#stopButton {
                background-color: #dc3545;
            }
            QPushButton#stopButton:hover {
                background-color: #bb2d3b;
            }
            QPushButton#stopButton:disabled {
                background-color: #463235;
                color: #a0a0a0;
                border: 1px solid #563235;
            }
            QPushButton#remove {
                background-color: #6c757d;
            }
            QPushButton#remove:hover {
                background-color: #5c636a;
            }
            QPushButton#remove:disabled {
                background-color: #3d3d3d;
                color: #707070;
                border: 1px solid #4d4d4d;
            }
            QLineEdit {
                padding: 8px;
                background-color: #363636;
                border: 1px solid #404040;
                border-radius: 4px;
                margin: 2px 0;
            }
            QLineEdit#warning {
                border: 1px solid #dc3545;
                background-color: #2c1215;
            }
            QLabel {
                color: #e0e0e0;
                margin: 2px 0;
            }
            QLabel#warning {
                color: #dc3545;
            }
            QWidget#section {
                background-color: #363636;
                border-radius: 4px;
                padding: 15px;
                margin: 5px 0;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        # Blender Executable Section
        executableSection = QWidget()
        executableSection.setObjectName("section")
        executableLayout = QVBoxLayout(executableSection)
        executableLayout.setSpacing(5)
        
        execHeaderLayout = QHBoxLayout()
        execLabel = QLabel("Blender Executable:")
        execLabel.setStyleSheet("font-weight: bold; background: transparent;")
        self.execStatusLabel = QLabel()
        if not self.blender_executable:
            self.execStatusLabel.setText("⚠️ Not Found")
            self.execStatusLabel.setObjectName("warning")
        else:
            self.execStatusLabel.setText("✓ Found")
            self.execStatusLabel.setStyleSheet("color: #28a745;")
        
        execHeaderLayout.addWidget(execLabel)
        execHeaderLayout.addWidget(self.execStatusLabel)
        execHeaderLayout.addStretch()
        executableLayout.addLayout(execHeaderLayout)
        
        execPathLayout = QHBoxLayout()
        self.blenderPathInput = QLineEdit()
        self.blenderPathInput.setPlaceholderText("Enter Blender executable path (blender.exe)")
        if not self.blender_executable:
            self.blenderPathInput.setObjectName("warning")
        if self.blender_executable:
            self.blenderPathInput.setText(self.blender_executable)
        
        self.selectBlenderButton = QPushButton("Browse")
        self.selectBlenderButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.selectBlenderButton.setMaximumWidth(100)
        
        execPathLayout.addWidget(self.blenderPathInput)
        execPathLayout.addWidget(self.selectBlenderButton)
        executableLayout.addLayout(execPathLayout)
        
        layout.addWidget(executableSection)

        # Output Directory Section
        outputSection = QWidget()
        outputSection.setObjectName("section")
        outputLayout = QVBoxLayout(outputSection)
        outputLayout.setSpacing(5)
        
        outputHeaderLayout = QHBoxLayout()
        outputLabel = QLabel("Output Directory:")
        outputLabel.setStyleSheet("font-weight: bold; background: transparent;")
        self.outputStatusLabel = QLabel()
        
        outputHeaderLayout.addWidget(outputLabel)
        outputHeaderLayout.addWidget(self.outputStatusLabel)
        outputHeaderLayout.addStretch()
        outputLayout.addLayout(outputHeaderLayout)
        
        outputPathLayout = QHBoxLayout()
        self.outputPathInput = QLineEdit()
        self.outputPathInput.setPlaceholderText("Select output directory for rendered frames")
        
        self.selectOutputButton = QPushButton("Browse")
        self.selectOutputButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.selectOutputButton.setMaximumWidth(100)
        
        outputPathLayout.addWidget(self.outputPathInput)
        outputPathLayout.addWidget(self.selectOutputButton)
        outputLayout.addLayout(outputPathLayout)
        
        layout.addWidget(outputSection)

        # File List Section
        listSection = QWidget()
        listSection.setObjectName("section")
        listLayout = QVBoxLayout(listSection)
        listLayout.setSpacing(5)
        
        # Header with label and add button
        headerLayout = QHBoxLayout()
        listLabel = QLabel("Render Queue:")
        listLabel.setStyleSheet("font-weight: bold; background: transparent;")
        self.addButton = QPushButton("Add File")
        self.addButton.setMaximumWidth(100)
        
        headerLayout.addWidget(listLabel)
        headerLayout.addStretch()
        headerLayout.addWidget(self.addButton)
        listLayout.addLayout(headerLayout)
        
        # List widget and remove button
        self.listWidget = QListWidget()
        listLayout.addWidget(self.listWidget)
        
        self.removeButton = QPushButton("Remove Selected")
        self.removeButton.setObjectName("remove")
        self.removeButton.setMaximumWidth(150)
        self.removeButton.setEnabled(False)
        
        removeLayout = QHBoxLayout()
        removeLayout.addStretch()
        removeLayout.addWidget(self.removeButton)
        listLayout.addLayout(removeLayout)
        
        layout.addWidget(listSection)

        # Control Section
        controlSection = QWidget()
        controlLayout = QVBoxLayout(controlSection)
        controlLayout.setSpacing(5)

        # Render control buttons
        renderButtonLayout = QHBoxLayout()
        self.startButton = QPushButton("Start Render Queue")
        self.startButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.stopButton = QPushButton("Stop Rendering")
        self.stopButton.setObjectName("stopButton")  # For specific styling
        self.stopButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stopButton.setEnabled(False)
        
        renderButtonLayout.addWidget(self.startButton)
        renderButtonLayout.addWidget(self.stopButton)
        controlLayout.addLayout(renderButtonLayout)

        # Progress bars
        self.progressBar = DecimalProgressBar()
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(1000)
        controlLayout.addWidget(QLabel("Overall Progress:"))
        controlLayout.addWidget(self.progressBar)

        self.fileProgressBar = DecimalProgressBar()
        self.fileProgressBar.setValue(0)
        self.fileProgressBar.setMaximum(1000)
        controlLayout.addWidget(QLabel("Current File Progress:"))
        controlLayout.addWidget(self.fileProgressBar)

        self.statusLabel = QLabel("Status: Idle")
        controlLayout.addWidget(self.statusLabel)

        layout.addWidget(controlSection)

        # Connect signals
        self.addButton.clicked.connect(self.addFile)
        self.removeButton.clicked.connect(self.removeFile)
        self.startButton.clicked.connect(self.startQueue)
        self.stopButton.clicked.connect(self.stopRendering)
        self.selectBlenderButton.clicked.connect(self.selectBlenderPath)
        self.listWidget.itemSelectionChanged.connect(self.updateRemoveButton)
        self.blenderPathInput.textChanged.connect(self.updateExecutableStatus)
        self.selectOutputButton.clicked.connect(self.selectOutputPath)
        self.outputPathInput.textChanged.connect(self.updateOutputStatus)

        self.setLayout(layout)

    def addFile(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Blend File", "", "Blender Files (*.blend)")
        if file:
            self.queue.append(file)
            self.listWidget.addItem(file)

    def removeFile(self):
        selected_items = self.listWidget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.queue.remove(item.text())
            self.listWidget.takeItem(self.listWidget.row(item))

    def selectBlenderPath(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Blender Executable", "", "Executable Files (*.exe *.app *.*)")
        if file:
            self.blender_executable = file
            self.blenderPathInput.setText(file)

    def selectOutputPath(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.outputPathInput.setText(directory)

    def startQueue(self):
        if not self.queue:
            self.statusLabel.setText("Status: No files in queue!")
            return
            
        self.blender_executable = self.blenderPathInput.text().strip()
        if not self.blender_executable or not os.path.exists(self.blender_executable):
            self.statusLabel.setText("Invalid Blender executable! Cannot start rendering.")
            return

        output_dir = self.outputPathInput.text().strip()
        if not output_dir or not os.path.exists(output_dir):
            self.statusLabel.setText("Invalid output directory! Cannot start rendering.")
            return

        # Disable file management buttons
        self.addButton.setEnabled(False)
        self.removeButton.setEnabled(False)
        
        self.rendering = True
        self.stopButton.setEnabled(True)
        self.render_thread = threading.Thread(target=self.render_files, daemon=True)
        self.render_thread.start()

    def render_files(self):
        total_files = len(self.queue)
        start_time = time.time()
        for index, file in enumerate(self.queue):
            if not self.rendering:
                self.statusLabel.setText("Rendering Stopped.")
                return

            self.statusLabel.setText(f"Rendering: {file}")
            self.fileProgressBar.setValue(0)

            try:
                # Create a temporary Python script
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                    tmp.write('''
import bpy
scene = bpy.context.scene
print("FRAME_RANGE:%d,%d" % (scene.frame_start, scene.frame_end))
''')
                    tmp_path = tmp.name

                try:
                    # Run Blender with the temporary script
                    info_command = f'"{self.blender_executable}" -b "{file}" -P "{tmp_path}"'
                    info_process = subprocess.run(
                        info_command,
                        capture_output=True,
                        encoding='utf-8',
                        shell=True
                    )
                    
                    print("Debug - Frame range output:", info_process.stdout)
                    print("Debug - Frame range errors:", info_process.stderr)
                    
                    # Parse the frame range
                    total_frames = 1
                    for line in info_process.stdout.split('\n'):
                        print("Debug - Checking line:", line)
                        if "FRAME_RANGE:" in line:
                            try:
                                range_part = line.split("FRAME_RANGE:")[1].strip()
                                start, end = map(int, range_part.split(','))
                                total_frames = end - start + 1
                                print(f"Debug - Found frame range: {start} to {end}, total: {total_frames}")
                            except Exception as e:
                                print(f"Debug - Error parsing frame range: {e}")
                
                finally:
                    # Clean up the temporary file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

                if total_frames == 1:
                    print("Warning: Could not detect frame range, defaulting to 1 frame")

                # Create subfolder for this blend file
                blend_filename = os.path.splitext(os.path.basename(file))[0]
                output_subfolder = os.path.join(self.outputPathInput.text().strip(), blend_filename)
                os.makedirs(output_subfolder, exist_ok=True)

                # Now start the actual render with the subfolder
                if sys.platform == 'win32':
                    self.process = subprocess.Popen(
                        f'"{self.blender_executable}" -b "{file}" -o "{output_subfolder}/frame_" -F PNG -x 1 -a',
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                else:
                    self.process = subprocess.Popen(
                        f'"{self.blender_executable}" -b "{file}" -o "{output_subfolder}/frame_" -F PNG -x 1 -a',
                        shell=True,
                        preexec_fn=os.setsid,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                
                # Monitor the rendering progress
                while self.process.poll() is None:
                    if not self.rendering:
                        break
                    
                    output = self.process.stdout.readline()
                    if output:
                        print(f"Debug - Blender output: {output}")  # Keep debug output
                        # Look for Fra:X in the output
                        if "Fra:" in output:
                            try:
                                current_frame = int(output.split("Fra:")[1].split()[0])
                                progress = (current_frame / total_frames) * 1000  # Multiply by 1000 instead of 100
                                print(f"Debug - Progress calculated: {progress/10}% (Frame {current_frame}/{total_frames})")
                                self.progress_update.emit(int(progress))
                            except Exception as e:
                                print(f"Debug - Error parsing progress: {e}")
                                pass

                if not self.rendering:  # If stopped midway
                    return

                elapsed_time = time.time() - start_time
                avg_time_per_file = elapsed_time / (index + 1)
                remaining_time = avg_time_per_file * (total_files - (index + 1))
                
                self.progressBar.setValue(int(((index + 1) / total_files) * 1000))  # Multiply by 1000 instead of 100
                self.statusLabel.setText(f"Completed {index+1}/{total_files}. Estimated time left: {int(remaining_time)}s")
                
            except Exception as e:
                self.statusLabel.setText(f"Error during rendering: {str(e)}")
                self.rendering = False
                break

        if self.rendering:  # Only update if not stopped
            self.statusLabel.setText("Rendering Complete!")
            self.progressBar.setValue(1000)
            self.fileProgressBar.setValue(1000)
            # Re-enable file management buttons after completion
            self.addButton.setEnabled(True)
            self.updateRemoveButton()
        
        self.rendering = False
        self.stopButton.setEnabled(False)
        self.render_thread = None

    def stopRendering(self):
        self.rendering = False  # Set this first to prevent new processes from starting
        
        if self.process:
            try:
                if sys.platform == 'win32':
                    # On Windows, send Ctrl+Break to the process group
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # On Unix-like systems, kill the entire process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait briefly for the process to terminate
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If process doesn't terminate gracefully, force kill it
                    if sys.platform == 'win32':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            
            except Exception as e:
                print(f"Error while stopping process: {e}")
            finally:
                self.process = None

        self.stopButton.setEnabled(False)
        # Re-enable file management buttons
        self.addButton.setEnabled(True)
        self.updateRemoveButton()  # This will enable remove button only if files are selected
        
        self.statusLabel.setText("Rendering Stopped.")
        self.progressBar.setValue(0)
        self.fileProgressBar.setValue(0)

    def updateRemoveButton(self):
        # Enable/disable remove button based on selection
        self.removeButton.setEnabled(len(self.listWidget.selectedItems()) > 0)

    def updateExecutableStatus(self):
        path = self.blenderPathInput.text().strip()
        if os.path.exists(path):
            self.execStatusLabel.setText("✓ Found")
            self.execStatusLabel.setStyleSheet("color: #28a745;")
            self.blenderPathInput.setObjectName("")
        else:
            self.execStatusLabel.setText("⚠️ Not Found")
            self.execStatusLabel.setObjectName("warning")
            self.blenderPathInput.setObjectName("warning")
        
        # Force style update
        self.blenderPathInput.style().unpolish(self.blenderPathInput)
        self.blenderPathInput.style().polish(self.blenderPathInput)

    def updateOutputStatus(self):
        path = self.outputPathInput.text().strip()
        if os.path.exists(path) and os.path.isdir(path):
            self.outputStatusLabel.setText("✓ Valid")
            self.outputStatusLabel.setStyleSheet("color: #28a745;")
            self.outputPathInput.setObjectName("")
        else:
            self.outputStatusLabel.setText("⚠️ Invalid")
            self.outputStatusLabel.setObjectName("warning")
            self.outputPathInput.setObjectName("warning")
        
        self.outputPathInput.style().unpolish(self.outputPathInput)
        self.outputPathInput.style().polish(self.outputPathInput)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RenderQueueApp()
    window.show()
    sys.exit(app.exec())
