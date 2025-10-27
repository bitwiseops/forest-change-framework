# Forest Change Framework GUI

A professional PyQt6 desktop application for forest loss analysis.

## 🚀 Features (Phase 1 - Foundation)

### ✅ Completed
- **Professional Application Shell**
  - Modern PyQt6 interface
  - Light/Dark theme support with stylesheet system
  - Window state persistence (size, position, maximized)
  - Menu bar with File, View, Tools, Help menus

- **Component Manager**
  - Browse all registered components organized by category
  - Search/filter components in real-time
  - Display component details (name, version, description)
  - Select components for execution

- **Configuration Management**
  - GUI-specific config persistence (~/.forest_change_framework/gui_config.json)
  - Theme preference saving
  - Window state restoration
  - Recent files tracking

- **Toolbar**
  - Quick actions: New, Open, Save, Run, Stop
  - Professional icon-based interface

## 📦 Installation

### Prerequisites
```bash
Python 3.8+
```

### Install Dependencies
```bash
pip install PyQt6 PyQt6-WebEngine folium matplotlib plotly
```

Or install with the framework:
```bash
pip install -e ".[gui]"  # Once setup.py is updated
```

## 🚀 Running the GUI

### From Command Line
```bash
# Method 1: Using the entry point script
python gui.py

# Method 2: As a module
python -m src.forest_change_framework.gui.app

# Method 3: With options
python gui.py --theme dark --debug
```

### Programmatically
```python
from src.forest_change_framework.gui.app import ForestChangeApp
import sys

app = ForestChangeApp()
exit_code = app.run()
sys.exit(exit_code)
```

## 🏗️ Architecture

### Directory Structure
```
src/forest_change_framework/gui/
├── __init__.py              # Package initialization
├── app.py                   # Main application class
├── main_window.py           # Main window
├── theme.py                 # Theme management
├── utils.py                 # Utility functions
├── panels/                  # UI Panels
│   ├── __init__.py
│   └── component_panel.py   # Component browser
├── widgets/                 # Reusable widgets (TBD)
├── dialogs/                 # Dialog windows (TBD)
├── models/                  # Data models (TBD)
├── executors/               # Execution logic (TBD)
├── handlers/                # Event handlers (TBD)
├── config/                  # Configuration
│   ├── __init__.py
│   └── gui_config.py        # GUI config manager
└── resources/               # Static assets
    ├── icons/               # Icon files (TBD)
    ├── styles/              # CSS stylesheets (TBD)
    └── templates/           # HTML templates (TBD)
```

### Key Components

#### 1. **ForestChangeApp** (app.py)
- Main application class
- Handles initialization, configuration, theme management
- Creates and shows main window
- Manages application lifecycle

#### 2. **MainWindow** (main_window.py)
- Central application window
- Contains menu bar, toolbar, panels, status bar
- Manages window state persistence
- Coordinates between panels

#### 3. **ComponentPanel** (panels/component_panel.py)
- Displays all available components
- Organized by category (data_ingestion, preprocessing, etc.)
- Search/filter functionality
- Shows component details
- Triggers configuration and execution

#### 4. **ThemeManager** (theme.py)
- Manages light/dark themes
- Applies consistent styling across all widgets
- Supports theme toggling
- Customizable color schemes

#### 5. **GUIConfig** (config/gui_config.py)
- Persists user preferences
- Dot-notation config access (e.g., "window.width")
- Deep merge for config updates
- Auto-loads on startup, saves on shutdown

## 🎯 Phase 1 - What's Done

### Core Foundation
- ✅ Application shell and main window
- ✅ Theme system (light/dark mode)
- ✅ Component discovery and listing
- ✅ Configuration persistence
- ✅ Menu bar and toolbar
- ✅ Professional styling

### Testing
```bash
# Test GUI import
python -c "from src.forest_change_framework.gui.app import ForestChangeApp; print('OK')"

# Run GUI (headless would fail, but structure is valid)
```

## 🔄 Phase 2 - Coming Next

### Map Viewer
- Interactive map display (leaflet/folium)
- GeoJSON visualization
- Layer controls
- Feature popups

### Results Dashboard
- Statistics and metrics display
- Interactive charts (matplotlib, plotly)
- Metadata table viewers
- Validation report display

### Component Configuration
- Auto-generate forms from component config schema
- Type-aware input widgets
- Config validation
- Preset management

## 🔧 Phase 3 - Extended Features

### Workflow Builder
- Drag-drop component assembly
- Visual pipeline editor
- Parameter passing between components
- Workflow templates

### Execution System
- Background component execution with threading
- Progress indicators and logs
- Cancel execution support
- Execution history

### Export & Reporting
- Export dialogs for multiple formats
- PDF report generation
- Batch operations
- Result sharing

## 🛠️ Development Guide

### Adding New Panels

1. Create panel class in `panels/`:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("My Panel"))
```

2. Import and add to MainWindow:
```python
from .panels.my_panel import MyPanel

# In MainWindow._create_central_widget()
self.my_panel = MyPanel()
splitter.addWidget(self.my_panel)
```

### Adding New Dialogs

1. Create dialog class in `dialogs/`:
```python
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("My Dialog"))
```

2. Show from menu or button:
```python
dialog = MyDialog(self)
dialog.exec()  # For blocking dialog
# OR
dialog.show()  # For non-blocking dialog
```

### Theming Custom Widgets

Themes are automatically applied via stylesheet. For custom styling:

```python
# Light mode colors
from app import ForestChangeApp
app = ForestChangeApp.instance()
primary_color = app.theme_manager.get_color("primary")
```

## 📝 Configuration File

GUI configuration is stored at:
```
~/.forest_change_framework/gui_config.json
```

Example:
```json
{
  "theme": "dark",
  "window": {
    "width": 1400,
    "height": 900,
    "x": 100,
    "y": 100,
    "maximized": false
  },
  "panels": {
    "left_panel_width": 250,
    "show_log": true
  },
  "recent_files": [],
  "auto_save_interval": 30
}
```

## 🎨 Customization

### Changing Colors

Edit `theme.py` THEMES dictionary:
```python
THEMES = {
    "dark": {
        "primary": "#1976D2",      # Change primary color
        "accent": "#FF5722",        # Change accent color
        "background": "#121212",    # Change background
        # ... more colors
    }
}
```

### Changing Icons

Place SVG files in `resources/icons/` and reference by name:
```python
from utils import create_icon

my_icon = create_icon("my_icon_name")
```

## 📦 Distribution

### Building Executable (PyInstaller)

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed gui.py

# Output in: dist/gui.exe (or gui on macOS/Linux)
```

## 🐛 Debugging

### Enable Debug Logging
```bash
python gui.py --debug
```

### Check Configuration
```python
from src.forest_change_framework.gui.config.gui_config import GUIConfig

config = GUIConfig()
config.load()
print(config.data)
```

## 📚 Resources

- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- Qt Documentation: https://doc.qt.io/qt-6/
- Folium Maps: https://folium.readthedocs.io/
- Matplotlib: https://matplotlib.org/

## 🚀 Next Steps

1. **Implement Component Config Dialog** - Generate forms from component config schemas
2. **Add Component Executor** - Run components in background threads
3. **Build Map Viewer** - Display GeoJSON on interactive maps
4. **Create Results Dashboard** - Show statistics, charts, and metadata
5. **Add Workflow Builder** - Drag-drop pipeline creation
6. **Create Executable** - Package as standalone application

## 📋 Checklist for Future Development

- [ ] Component config dialog with auto-generated forms
- [ ] Component executor with threading
- [ ] Log viewer and progress indicators
- [ ] File browser for data directory
- [ ] Map viewer with folium integration
- [ ] Results dashboard with charts
- [ ] Workflow builder/executor
- [ ] Export dialogs
- [ ] PyInstaller build automation
- [ ] Comprehensive help system
- [ ] Unit tests for GUI components
- [ ] CI/CD integration

---

**Happy coding!** 🎉 The GUI foundation is ready for expansion.
